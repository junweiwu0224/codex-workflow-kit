#!/usr/bin/env python3
"""CLI entry point for the V4.2 Skill lifecycle state machine."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.lifecycle import _cli


if __name__ == "__main__":
    raise SystemExit(_cli())
