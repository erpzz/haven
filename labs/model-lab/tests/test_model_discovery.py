"""Discovery boundary tests; fixtures are metadata, never downloaded weights."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import model_discovery as d

class DiscoveryTests(unittest.TestCase):
    def test_unknown_fields_urls_and_paths_rejected_before_network(self):
        with patch.object(d,'fetch') as fetch:
            for body in ({'repo':'https://evil.example/x'}, {'repo':'owner/../private'}, {'repo':'owner/model','token':'private'}):
                with self.assertRaises(ValueError): d.detail(body)
            for body in ({'query':'test','url':'https://evil.example'}, {'query':'test','format':'pickle'}, {'query':'test','author':'../secret'}):
                with self.assertRaises(ValueError):d.search(body)
            fetch.assert_not_called()

    def test_search_bounds_and_explicit_metadata_only_stages(self):
        with patch.object(d,'fetch',return_value=[{'id':'public/model','sha':'a'*40,'cardData':{'license':'apache-2.0'}}]*20) as fetch:
            result=d.search({'query':'Granite','format':'gguf','author':'public','task':'text-generation'})
            self.assertEqual(len(result['models']),12)
            self.assertEqual(result['models'][0]['stage'],'DISCOVERABLE')
            self.assertEqual(result['models'][0]['compatibility'],'UNVERIFIED')
            self.assertEqual(fetch.call_args.args[1]['limit'],12)

    def test_checksums_and_revision_are_metadata_not_verified_artifacts(self):
        raw={'id':'public/model','sha':'a'*40,'siblings':[
            {'rfilename':'model-Q4_K_M.gguf','size':123,'lfs':{'sha256':'b'*64}},
            {'rfilename':'unknown.gguf','size':20}, {'rfilename':'../escape.gguf','size':10},
            {'rfilename':'code.py','size':10}]}
        with patch.object(d,'fetch',return_value=raw):
            result=d.detail({'repo':'public/model'})
        self.assertEqual(len(result['files']),2)
        self.assertEqual(result['files'][0]['integrity'],'PINNED_LFS_METADATA')
        self.assertEqual(result['files'][1]['integrity'],'UNVERIFIED')
        self.assertEqual(result['installation'],'REVIEW_REQUIRED')
        self.assertNotIn('download_url',str(result))

    def test_redirect_is_denied_before_following_location(self):
        with self.assertRaises(ValueError):d.NoRedirect().redirect_request(None,None,None,None,None,None)

if __name__=='__main__':unittest.main()
