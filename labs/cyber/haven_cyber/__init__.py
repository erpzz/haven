"""Haven cyber intelligence: knowledge retrieval, read-only security tools, a common evidence model and evaluation.

The core is standard-library only (Python >= 3.11) so it runs on Slink, the Mac and in CI without installs.
The MCP server (`haven_cyber.mcp_server`) is the one module that needs the `mcp` SDK.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # labs/cyber
CORPUS = ROOT / "corpus"
FIXTURES = ROOT / "fixtures"
EVAL = ROOT / "eval"
RUNS = ROOT / "runs"

__version__ = "0.1.0"
