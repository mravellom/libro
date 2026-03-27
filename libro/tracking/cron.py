"""Cron job entry point for automated tracking.

Setup:
    # Run every 12 hours
    0 */12 * * * cd /path/to/Libro && .venv/bin/libro track cron-tick >> data/cron.log 2>&1
"""

import logging
from datetime import UTC, datetime

from libro.database import get_session_factory
from libro.tracking.monitor import capture_all_active

log = logging.getLogger(__name__)


def cron_tick() -> int:
    """Execute a tracking tick — snapshot all active publications.

    Returns:
        Number of snapshots captured.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    log.info(f"Cron tick started at {datetime.now(UTC).isoformat()}")

    factory = get_session_factory()
    session = factory()

    try:
        snapshots = capture_all_active(session, headless=True)
        session.commit()
        log.info(f"Cron tick complete: {len(snapshots)} snapshots captured")
        return len(snapshots)
    except Exception as e:
        session.rollback()
        log.error(f"Cron tick failed: {e}")
        raise
    finally:
        session.close()
