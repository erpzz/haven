"""Invoke the pinned upstream MTP tool without its automatic main fallback."""
from pathlib import Path
import importlib.util
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent


def strict_revision(module):
    module.REVISION = module.PINNED_REVISION
    module.REPO = module.PINNED
    def resolve():
        request = urllib.request.Request(module.PINNED + 'model.safetensors.index.json', method='HEAD')
        with urllib.request.urlopen(request, timeout=60):
            pass
        module.REPO = module.PINNED
    module.resolve_repo = resolve


def main():
    path = ROOT / '.local' / 'Strata' / 'tools' / 'mtp_fetch.py'
    spec = importlib.util.spec_from_file_location('haven_upstream_mtp', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strict_revision(module)
    return module.main()


if __name__ == '__main__':
    main()
