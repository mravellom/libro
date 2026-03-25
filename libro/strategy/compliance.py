"""KDP 5.4.8 Risk Assessment — portfolio-level compliance and financial exposure tracking."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from libro.common.similarity import title_similarity
from libro.config import get_settings
from libro.models.publication import Publication
from libro.models.variant import Variant
from libro.publication.checklist import run_compliance_checklist

log = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Portfolio-level KDP 5.4.8 risk assessment."""

    # Financial exposure (estimated from BSR data)
    total_estimated_unpaid: float = 0.0
    total_at_risk: float = 0.0
    exposure_ratio: float = 0.0  # at_risk / unpaid (0.0 = safe, 1.0 = all at risk)

    # Compliance summary
    total_publications: int = 0
    compliant_count: int = 0
    flagged_count: int = 0
    blocked_count: int = 0
    unchecked_count: int = 0

    # Pattern detection — velocity
    velocity_7d: int = 0
    velocity_30d: int = 0
    velocity_alert: bool = False

    # Pattern detection — similarity
    max_catalog_similarity: float = 0.0
    similar_clusters: int = 0
    similarity_alert: bool = False

    # Content risk
    trademark_violations: int = 0
    attribution_warnings: int = 0

    # Overall
    risk_level: str = "low"  # low | medium | high | critical
    risk_factors: list[str] = field(default_factory=list)

    # Drill-down data
    flagged_publications: list[dict] = field(default_factory=list)


def assess_portfolio_risk(session: Session) -> RiskAssessment:
    """Run full portfolio risk assessment for KDP 5.4.8 compliance.

    This is the heavy operation — updates compliance_status on publications,
    calculates financial exposure, and detects risky patterns.
    """
    settings = get_settings()
    r = RiskAssessment()
    now = datetime.utcnow()

    # --- Load all active publications ---
    pubs = (
        session.query(Publication)
        .filter(Publication.published_at.isnot(None))
        .all()
    )
    r.total_publications = len(pubs)

    if not pubs:
        r.risk_level = "low"
        return r

    # --- Financial exposure ---
    for pub in pubs:
        if pub.decision == "kill":
            continue

        # Calculate estimated unpaid from latest snapshot
        if pub.snapshots:
            latest = max(pub.snapshots, key=lambda s: s.captured_at)
            monthly_rev = latest.estimated_monthly_revenue or 0.0

            # Estimate total unpaid: monthly revenue × months since published
            if pub.published_at:
                months_active = max(
                    (now - pub.published_at).days / 30.0, 1.0
                )
                estimated_total = monthly_rev * months_active
            else:
                estimated_total = monthly_rev

            pub.estimated_total_royalties = round(estimated_total, 2)
            r.total_estimated_unpaid += estimated_total

    # --- Compliance checks on unchecked/stale publications ---
    recheck_cutoff = now - timedelta(days=settings.compliance_recheck_days)

    for pub in pubs:
        if pub.decision == "kill":
            continue

        needs_check = (
            pub.compliance_status is None
            or pub.compliance_checked_at is None
            or pub.compliance_checked_at < recheck_cutoff
        )

        if needs_check and pub.variant_id:
            checklist = run_compliance_checklist(session, pub.variant_id)
            errors = checklist.errors
            warnings = checklist.warnings

            issues = []
            for c in errors:
                issues.append({"severity": "error", "name": c.name, "message": c.message})
            for c in warnings:
                issues.append({"severity": "warning", "name": c.name, "message": c.message})

            if errors:
                pub.compliance_status = "blocked"
            elif warnings:
                pub.compliance_status = "flagged"
            else:
                pub.compliance_status = "clear"

            pub.compliance_checked_at = now
            pub.compliance_notes = json.dumps(issues) if issues else None

            # Count specific risk types
            for c in errors + warnings:
                if "trademark" in c.name.lower():
                    r.trademark_violations += 1
                if "quote" in c.name.lower() and not c.passed:
                    r.attribution_warnings += 1

    # --- Aggregate compliance counts ---
    for pub in pubs:
        if pub.decision == "kill":
            continue
        status = pub.compliance_status
        if status == "clear":
            r.compliant_count += 1
        elif status == "flagged":
            r.flagged_count += 1
            r.total_at_risk += pub.estimated_total_royalties or 0.0
            r.flagged_publications.append({
                "pub_id": pub.id,
                "title": pub.variant.title if pub.variant else f"Variant #{pub.variant_id}",
                "asin": pub.asin,
                "status": "flagged",
                "revenue_at_risk": pub.estimated_total_royalties or 0.0,
                "issues": json.loads(pub.compliance_notes) if pub.compliance_notes else [],
            })
        elif status == "blocked":
            r.blocked_count += 1
            r.total_at_risk += pub.estimated_total_royalties or 0.0
            r.flagged_publications.append({
                "pub_id": pub.id,
                "title": pub.variant.title if pub.variant else f"Variant #{pub.variant_id}",
                "asin": pub.asin,
                "status": "blocked",
                "revenue_at_risk": pub.estimated_total_royalties or 0.0,
                "issues": json.loads(pub.compliance_notes) if pub.compliance_notes else [],
            })
        else:
            r.unchecked_count += 1

    # Exposure ratio
    if r.total_estimated_unpaid > 0:
        r.exposure_ratio = round(r.total_at_risk / r.total_estimated_unpaid, 3)

    r.total_estimated_unpaid = round(r.total_estimated_unpaid, 2)
    r.total_at_risk = round(r.total_at_risk, 2)

    # --- Velocity detection ---
    r.velocity_7d = (
        session.query(Publication)
        .filter(Publication.published_at >= now - timedelta(days=7))
        .count()
    )
    r.velocity_30d = (
        session.query(Publication)
        .filter(Publication.published_at >= now - timedelta(days=30))
        .count()
    )
    r.velocity_alert = (
        r.velocity_7d > settings.compliance_velocity_7d_max
        or r.velocity_30d > settings.compliance_velocity_30d_max
    )

    # --- Catalog-wide similarity analysis ---
    active_variants = (
        session.query(Variant)
        .filter(Variant.status.in_(["ready", "selected", "published", "pending_review"]))
        .order_by(Variant.created_at.desc())
        .limit(200)
        .all()
    )

    max_sim = 0.0
    cluster_count = 0

    # Pairwise similarity (capped at 200 titles)
    for i in range(len(active_variants)):
        similar_to_i = 0
        for j in range(i + 1, len(active_variants)):
            sim = title_similarity(active_variants[i].title, active_variants[j].title)
            if sim > max_sim:
                max_sim = sim
            if sim >= settings.compliance_similarity_threshold:
                similar_to_i += 1
        if similar_to_i >= 3:
            cluster_count += 1

    r.max_catalog_similarity = round(max_sim, 3)
    r.similar_clusters = cluster_count
    r.similarity_alert = (
        cluster_count > 0 or max_sim >= settings.compliance_similarity_threshold
    )

    # --- Risk level calculation ---
    risk_factors = []

    if r.trademark_violations > 0:
        risk_factors.append(
            f"{r.trademark_violations} trademark violation(s) — immediate account risk"
        )

    if r.velocity_alert:
        risk_factors.append(
            f"High publishing velocity ({r.velocity_7d}/7d, {r.velocity_30d}/30d) — spam pattern"
        )

    if r.similarity_alert:
        risk_factors.append(
            f"Catalog similarity concern (max {r.max_catalog_similarity:.0%}, "
            f"{r.similar_clusters} cluster(s)) — duplicate content pattern"
        )

    if r.blocked_count > 0:
        risk_factors.append(
            f"{r.blocked_count} publication(s) with blocking compliance errors"
        )

    if r.flagged_count > 3:
        risk_factors.append(
            f"{r.flagged_count} flagged publications — review recommended"
        )

    if r.exposure_ratio > 0.5:
        risk_factors.append(
            f"{r.exposure_ratio:.0%} of estimated revenue at risk "
            f"(${r.total_at_risk:,.0f} / ${r.total_estimated_unpaid:,.0f})"
        )

    r.risk_factors = risk_factors

    # Determine level
    if r.trademark_violations > 0:
        r.risk_level = "critical"
    elif r.exposure_ratio > 0.5 or r.velocity_alert or r.blocked_count > 0:
        r.risk_level = "high"
    elif r.flagged_count > 3 or r.similarity_alert:
        r.risk_level = "medium"
    else:
        r.risk_level = "low"

    log.info(
        f"Risk assessment complete: level={r.risk_level}, "
        f"unpaid=${r.total_estimated_unpaid:,.0f}, at_risk=${r.total_at_risk:,.0f}, "
        f"flagged={r.flagged_count}, blocked={r.blocked_count}"
    )

    return r


def update_financial_exposure(session: Session) -> dict:
    """Lightweight update of estimated royalties on each publication.

    Callable from cron or evaluate pipeline without running full compliance checks.
    """
    now = datetime.utcnow()
    pubs = (
        session.query(Publication)
        .filter(
            Publication.published_at.isnot(None),
            Publication.decision != "kill",
        )
        .all()
    )

    updated = 0
    total = 0.0

    for pub in pubs:
        if not pub.snapshots:
            continue

        latest = max(pub.snapshots, key=lambda s: s.captured_at)
        monthly_rev = latest.estimated_monthly_revenue or 0.0

        if pub.published_at:
            months_active = max((now - pub.published_at).days / 30.0, 1.0)
            estimated_total = round(monthly_rev * months_active, 2)
        else:
            estimated_total = round(monthly_rev, 2)

        pub.estimated_total_royalties = estimated_total
        total += estimated_total
        updated += 1

    return {"updated": updated, "total_estimated": round(total, 2)}
