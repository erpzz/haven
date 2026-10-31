"""Local, dependency-free entry point for the Operation Forge lab."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / ".hermes/plugins/haven-forge"))
from forge_runtime.cli import main

if __name__ == "__main__":
    main()
