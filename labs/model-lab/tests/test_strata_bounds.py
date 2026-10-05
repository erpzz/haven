"""Installation-bound regressions without downloads or upstream execution."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strata_install import checked_cleanup, configure_install_environment
from strata_mtp import strict_revision


class StrataBoundaryTests(unittest.TestCase):
    def test_inherited_dependency_destinations_and_config_are_disabled(self):
        inherited = {'PIP_TARGET': '/foreign', 'PIP_PREFIX': '/foreign',
                     'PIP_INDEX_URL': 'https://foreign.invalid', 'PIP_CONFIG_FILE': '/foreign/pip.ini',
                     'HF_HUB_CACHE': '/foreign', 'HF_TOKEN': 'fixture-token'}
        with patch.dict(os.environ, inherited, clear=True):
            configure_install_environment()
            for key in ('PIP_TARGET', 'PIP_PREFIX', 'PIP_INDEX_URL', 'HF_TOKEN'):
                self.assertNotIn(key, os.environ)
            self.assertEqual(os.environ['PIP_CONFIG_FILE'], os.devnull)
            self.assertTrue(Path(os.environ['PIP_CACHE_DIR']).is_relative_to(Path(os.environ['HF_HOME']).parent))
            self.assertTrue(Path(os.environ['HF_HUB_CACHE']).is_relative_to(Path(os.environ['HF_HOME'])))

    def test_cleanup_rejects_scope_alias_and_outside(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'Strata'; scope.mkdir()
            child = scope / 'child'; child.mkdir()
            with self.assertRaises(ValueError): checked_cleanup(child / '..', scope)
            with self.assertRaises(ValueError): checked_cleanup(scope.parent, scope)
            checked_cleanup(child, scope)
            self.assertTrue(child.exists())  # Validation itself deletes nothing.

    def test_cleanup_rejects_links(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory); target = scope / 'target'; target.mkdir()
            link = scope / 'link'
            try: link.symlink_to(target, target_is_directory=True)
            except OSError: self.skipTest('Host does not grant symlink creation')
            with self.assertRaises(ValueError): checked_cleanup(link, scope)

    def test_mtp_missing_pinned_revision_never_falls_back(self):
        module = SimpleNamespace(PINNED_REVISION='a'*40, PINNED='https://huggingface.co/x/y/resolve/'+'a'*40+'/',
                                 REVISION='main', REPO='https://huggingface.co/x/y/resolve/main/')
        strict_revision(module)
        with patch('strata_mtp.urllib.request.urlopen', side_effect=urllib.error.HTTPError(module.PINNED,404,'missing',{},None)):
            with self.assertRaises(urllib.error.HTTPError): module.resolve_repo()
        self.assertEqual(module.REPO, module.PINNED)
        self.assertEqual(module.REVISION, module.PINNED_REVISION)


if __name__ == '__main__': unittest.main()
