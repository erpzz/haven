"""Haven operator surface for Hermes: one MCP tool per Haven operation, over the existing controllers.

labs/engineer stays the only fleet controller and the Model Lab stays the only GPU owner; this package is a
thin, audited facade over them (engineer Python APIs on the controller host, labctl on Slink over ssh).
Standard library only (Python >= 3.9), so it runs with the system python3 on the Mac and on Slink.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # labs/hermes
LABS = ROOT.parent
ENGINEER = Path(os.environ.get("HAVEN_ENGINEER_DIR", LABS / "engineer"))

# Engineer modules import each other as top-level modules (they insert their own directory the same way).
if str(ENGINEER) not in sys.path:
    sys.path.insert(0, str(ENGINEER))

__version__ = "0.1.0"
