"""Configuration and constants.

The case study fixes the report date at 2026-06-25 — treat it as "today" for any
upcoming / current figure. Everything else is derived from the CSVs in ``data/``.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# Report date — "today" for upcoming/current figures (per the case study).
REPORT_DATE = date(2026, 6, 25)

# Paths. config.py lives at <repo>/backend/app/config.py.
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = Path(os.environ.get("EQUITIE_DATA_DIR", str(REPO_ROOT / "data")))

# LLM model id (used from Phase 2). Kept behind one env var so narration can be
# swapped (Haiku 4.5 -> Sonnet 4.6 / Opus 4.8) without touching code.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
