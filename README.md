# Libro

KDP niche detection and automated book creation system. Discovers profitable niches on Amazon, generates low-content book variants (journals, planners, trackers), and semi-automates publishing to KDP.

## Quick Start

```bash
# Install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# Initialize database
libro db init

# Copy and edit config
cp config.example.yaml config.yaml
```

## Workflow

The typical workflow follows these stages:

### 1. Discover niches

```bash
# Scrape Amazon for a keyword
libro intel discover "anxiety journal"

# Enrich with Keepa data (BSR trends, pricing history)
libro intel enrich --niche-id 1

# Score niches by opportunity
libro intel score

# Review results
libro intel list
libro intel show 1
```

### 2. Generate book variants

```bash
# Create variant records from competitor analysis
libro generate variants --niche-id 1 --count 3

# Generate interior PDFs
libro generate interior --variant-id 1 --template lined
libro generate interior --variant-id 2 --template gratitude

# Available templates: lined, dotted, grid, gratitude, planner
libro generate templates
```

### 3. Branding and covers

```bash
# Create a brand with color palette
libro brand create "Calm Press" --palette sage

# Assign brand to variant
libro brand assign --variant-id 1 --brand-id 1

# Generate KDP-compliant cover (PDF, 300 DPI)
libro brand cover --variant-id 1
```

### 4. Publish

```bash
# Run compliance checklist
libro publish checklist --variant-id 1

# Bundle files for KDP upload
libro publish prepare --variant-id 1

# List prepared publications
libro publish list
```

### 5. Upload to KDP

```bash
# Upload a single variant (semi-automated, browser opens)
libro kdp upload --variant-id 1

# Batch upload all ready variants
libro kdp batch --limit 5

# Check pipeline status
libro kdp status
```

The uploader opens a Chromium browser, logs you in (session persists between runs), fills all KDP forms automatically, and pauses before publishing for your review.

### 6. Track performance

```bash
# Capture BSR/review snapshots for published books
libro track snapshot

# Evaluate a publication (scale / iterate / kill)
libro track evaluate --publication-id 1

# Record decision
libro track decide --publication-id 1 --decision scale

# Performance report
libro track report
```

### 7. Scale

```bash
# Flood pipeline: produce books at scale (3-5/day)
libro strategy flood --daily-target 3

# Generate a series from a winning book
libro strategy series --publication-id 1

# A/B test covers
libro strategy cover-ab --variant-id 1

# Clone to other marketplaces (DE, JP)
libro strategy clone --variant-id 1 --marketplace de

# Dashboard with metrics
libro strategy status
```

## Web Dashboard

```bash
libro web --port 8000
```

Opens at `http://localhost:8000` with:
- Catalog metrics and publishing velocity
- Variant management with visual preview
- Human review gate for pending books
- Deploy monitoring (real-time KDP upload logs)

## Configuration

Edit `config.yaml` to adjust:

| Setting | Default | Description |
|---------|---------|-------------|
| `daily_target` | 3 | Books per flood run |
| `evergreen_ratio` | 0.7 | Fraction of evergreen vs seasonal/trending |
| `compliance_velocity_7d_max` | 10 | Max books in 7 days (KDP 5.4.8) |
| `compliance_velocity_30d_max` | 30 | Max books in 30 days |
| `compliance_similarity_threshold` | 0.85 | Title similarity threshold |
| `evaluation_period_days` | 21 | Days before first performance evaluation |
| `require_human_review` | true | Require manual approval before upload |

## Project Structure

```
libro/
  intelligence/   # Amazon scraping, Keepa, niche scoring
  generation/     # Interior PDFs, variant engine, title engine
  branding/       # Cover design, brand management, niche styles
  publication/    # Metadata, compliance checklist, packaging
  tracking/       # Performance monitoring, evaluation, decisions
  strategy/       # Flood pipeline, optimizer, scaler, feedback loop
  kdp/            # Semi-automated KDP uploader (Playwright)
  web/            # FastAPI dashboard
  models/         # SQLAlchemy ORM (Niche, Product, Brand, Variant, Publication)
  common/         # PDF utils, validation, similarity, rate limiting
```

## Testing

```bash
pytest tests/ -v
```

## KDP 5.4.8 Compliance

Built-in safeguards against account suspension:
- **Velocity limits**: Max 10/week, 30/month (configurable)
- **Similarity detection**: Blocks near-duplicate titles (threshold 0.85)
- **Trademark scanning**: Blocks titles containing trademarked brand names
- **PDF validation**: Verifies structure, dimensions, and page count before upload
- **Human review gate**: Every book requires manual approval before publishing
