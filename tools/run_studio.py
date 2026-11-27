#!/usr/bin/env python3
"""Launch the optional Conquer Studio desktop application."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conquer_studio.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
