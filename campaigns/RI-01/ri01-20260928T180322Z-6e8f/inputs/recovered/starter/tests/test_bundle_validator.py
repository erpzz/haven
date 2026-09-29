"""Unit tests of the offline starter validator, not product acceptance tests."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('bundle_validator',ROOT/'scripts/validate_bundle.py')
v=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)

class OfflineValidatorTests(unittest.TestCase):
    def fixture(self,name):
        return v.load(ROOT/f'fixtures/contracts/{name}.json')
    def schema(self,name):
        return v.load(ROOT/f'contracts/{name}.schema.json')
    def test_all_positive_fixtures(self):
        for row in v.load(ROOT/'contracts/registry.json'):
            with self.subTest(row['name']):
                v.check_record(ROOT,row['schema'],row['example'])
    def test_all_negative_fixtures(self):
        for row in v.load(ROOT/'fixtures/negative/registry.json'):
            with self.subTest(row['name']):
                with self.assertRaises(v.ValidationError):
                    v.check_record(ROOT,row['schema'],row['path'])
    def test_bool_is_not_integer(self):
        with self.assertRaises(v.ValidationError):v.check_shape(True,{'type':'integer'})
    def test_nonfinite_number_rejected(self):
        for number in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(number=number):
                with self.assertRaises(v.ValidationError):v.check_shape(number, {'type':'number'})
    def test_coordinate_dimension_rejected(self):
        data=self.fixture('spatial_estimate');data['geometry']=[[0,0,0,0]]
        with self.assertRaises(v.ValidationError):v.check_shape(data,self.schema('spatial_estimate'))
    def test_schema_unknown_keyword_rejected(self):
        with self.assertRaises(v.ValidationError):v.check_shape({}, {'made_up':'unsafe'})
    def test_unknown_raw_action_rejected(self):
        data=self.fixture('physical_action_proposal'); data['address']='TEST_ONLY'
        with self.assertRaises(v.ValidationError):v.check_shape(data,self.schema('physical_action_proposal'))
    def test_missing_required_field_rejected(self):
        data=self.fixture('agent_job'); del data['sponsor_id']
        with self.assertRaises(v.ValidationError):v.check_shape(data,self.schema('agent_job'))
    def test_unavailable_health_is_not_zero(self):
        data=self.fixture('health_observation'); data['value']=0
        with self.assertRaises(v.ValidationError):v.check_semantics('health_observation',data)
    def test_available_health_requires_capture_time(self):
        data=self.fixture('health_observation');data.update(availability='AVAILABLE',value=72)
        with self.assertRaises(v.ValidationError):v.check_semantics('health_observation',data)
    def test_unknown_spatial_uncertainty_rejected(self):
        data=self.fixture('spatial_estimate');data['uncertainty_parameters']=[0]
        with self.assertRaises(v.ValidationError):v.check_semantics('spatial_estimate',data)
    def test_unknown_capture_not_current(self):
        data=self.fixture('evidence');data.update(captured_at=None,freshness='CURRENT')
        with self.assertRaises(v.ValidationError):v.check_semantics('evidence',data)
    def test_path_traversal_rejected(self):
        for path in ('../secret','/absolute','C:/Users','x\\y'):
            with self.subTest(path):
                with self.assertRaises(v.ValidationError):v.safe_path(ROOT,path)
    def test_manifest_detects_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'a.txt').write_text('original')
            digest=hashlib.sha256((root/'a.txt').read_bytes()).hexdigest()
            (root/'MANIFEST.sha256').write_text(f'{digest}  a.txt\n')
            self.assertEqual(v.verify_manifest(root),1)
            (root/'a.txt').write_text('changed')
            with self.assertRaises(v.ValidationError):v.verify_manifest(root)
    def test_manifest_detects_unlisted_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'MANIFEST.sha256').write_text('');(root/'unexpected').write_text('x')
            with self.assertRaises(v.ValidationError):v.verify_manifest(root)
    def test_reference_coverage(self):
        result=v.validate(ROOT,integrity=False)
        self.assertEqual(result['requirements'],102)
        self.assertEqual(result['future_acceptance_tests_not_executed'],102)
        self.assertEqual(result['network_or_device_actions'],0)

if __name__=='__main__':unittest.main()
