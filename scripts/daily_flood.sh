#!/bin/bash
# Daily KDP flood pipeline — generates 15 book packages
# Runs via cron at 6:00 AM daily

set -e

cd /home/fabian/workSpace/Libro
source .venv/bin/activate

echo "=== Libro Daily Flood — $(date) ==="

# Run flood pipeline
libro strategy flood --target 15

# Run tracking snapshots for active publications
libro track cron-tick

echo "=== Done — $(date) ==="
