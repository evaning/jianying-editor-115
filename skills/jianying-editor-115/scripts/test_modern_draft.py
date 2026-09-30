import base64
import copy
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
import os
import sys
from unittest.mock import patch
from draft_codec import DraftError, decode, detect, encode
from modern_draft import apply_patch_plan, choose_content, clone_edit, digest, hash_files, inspect, reject_native_for_legacy

if os.environ.get('JY_LEGACY_TEST_RUNTIME'):
    sys.path.append(str(Path(os.environ['JY_LEGACY_TEST_RUNTIME']) / 'scripts'))

LEGACY_AVAILABLE = importlib.util.find_spec('jy_wrapper') is not None


class DraftCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.timeline = self.source / 'Timelines' / 'main'
        self.timeline.mkdir(parents=True)
        self.data = {'id': 'main', 'duration': 3000000, 'fps': 30,
                     'canvas_config': {'width': 1920, 'height': 1080},
                     'config': {}, 'unknown_115': {'retain': [1, 2]},
                     'materials': {'videos': [{'path': str(self.source / 'media.bin')}], 'future_kind': [{'x': 1}]},
                     'tracks': [{'id': 'v', 'type': 'video', 'segments': [{'id': 's', 'volume': 1.0, 'target_timerange': {'start': 0, 'duration': 3000000}}]}]}
        self.write(self.timeline / 'draft_content.json', self.data)
        self.write(self.source / 'draft_content.json', self.data)
        stale = copy.deepcopy(self.data)
        stale['duration'] = 1000000
        self.write(self.source / 'draft_info.json', stale)
        self.write(self.source / 'Timelines' / 'project.json', {'id': 'old-project', 'main_timeline_id': 'main', 'timelines': [{'id': 'main', 'is_marked_delete': False}]})
        self.write(self.source / 'draft_meta_info.json', {'draft_id': 'old', 'draft_name': 'source', 'draft_fold_path': str(self.source)})
        (self.source / 'media.bin').write_bytes(b'original media')
        self.plan = {'source_sha256': digest((self.timeline / 'draft_content.json').read_bytes()), 'operations': [{'op': 'replace', 'path': '/tracks/0/segments/0/volume', 'expected': 1.0, 'value': 0.4}]}

    def write(self, path, data):
        path.write_bytes(encode(data))

    def test_current_timeline_over_stale_info(self):
        result = inspect(self.source)
        self.assertEqual(result['duration_us'], 3000000)
        self.assertEqual(choose_content(self.source), (self.timeline / 'draft_content.json').resolve())
        self.assertTrue(any(not x['same_content'] for x in result['other_files']))

    def test_plain_bom_and_base64_json(self):
        for raw in [b'\xef\xbb\xbf' + encode(self.data), base64.b64encode(encode(self.data))]:
            self.assertEqual(decode(raw), self.data)

    def test_corrupt_plaintext_is_not_encryption(self):
        for raw in [b'{bad}', b'', b'[]']:
            with self.assertRaises(DraftError):
                detect(raw)

    def test_encryption_candidate_does_not_pass_without_native(self):
        raw = base64.b64encode(b'opaque-ciphertext')
        self.assertEqual(detect(raw), 'encrypted-candidate')
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(DraftError):
            decode(raw)

    def test_wrong_source_hash_rejected(self):
        with self.assertRaises(DraftError):
            apply_patch_plan(self.data, 'changed', self.plan)

    def test_expected_value_rejected(self):
        self.plan['operations'][0]['expected'] = 0.6
        with self.assertRaises(DraftError):
            apply_patch_plan(self.data, self.plan['source_sha256'], self.plan)

    def test_negative_index_rejected(self):
        self.plan['operations'][0]['path'] = '/tracks/-1/segments/0/volume'
        with self.assertRaises(DraftError):
            apply_patch_plan(self.data, self.plan['source_sha256'], self.plan)

    def test_negative_duration_rejected(self):
        self.plan['operations'] = [{'op': 'replace', 'path': '/tracks/0/segments/0/target_timerange/duration', 'expected': 3000000, 'value': -1}]
        with self.assertRaises(DraftError):
            apply_patch_plan(self.data, self.plan['source_sha256'], self.plan)

    def test_native_omitted_zero_start_preserved(self):
        data = copy.deepcopy(self.data)
        del data['tracks'][0]['segments'][0]['target_timerange']['start']
        changed = apply_patch_plan(data, self.plan['source_sha256'], self.plan)
        self.assertNotIn('start', changed['tracks'][0]['segments'][0]['target_timerange'])

    def test_copy_preserves_source_unknown_fields_and_mirrors(self):
        before = hash_files(self.source)
        destination = self.root / 'review'
        result = clone_edit(self.source, destination, self.plan)
        self.assertTrue(result['source_unchanged'])
        self.assertEqual(hash_files(self.source), before)
        actual = json.loads((destination / 'draft_content.json').read_bytes())
        self.assertEqual(actual['unknown_115'], self.data['unknown_115'])
        self.assertEqual(actual['tracks'][0]['segments'][0]['volume'], 0.4)
        self.assertEqual(actual, json.loads((destination / 'draft_info.json').read_bytes()))
        self.assertEqual(actual, json.loads((destination / 'Timelines' / 'main' / 'draft_content.json').read_bytes()))
        self.assertEqual(actual['materials']['videos'][0]['path'], (destination / 'media.bin').resolve().as_posix())
        self.assertNotEqual(json.loads((destination / 'draft_meta_info.json').read_bytes())['draft_id'], 'old')

    def test_existing_and_nested_destinations_rejected(self):
        for destination in (self.source, self.source / 'child', self.root):
            with self.assertRaises(DraftError):
                clone_edit(self.source, destination, self.plan)

    def test_multiple_timelines_not_published(self):
        manifest = self.source / 'Timelines' / 'project.json'
        data = json.loads(manifest.read_bytes())
        data['timelines'].append({'id': 'second'})
        self.write(manifest, data)
        with self.assertRaises(DraftError):
            clone_edit(self.source, self.root / 'review', self.plan)
        self.assertFalse((self.root / 'review').exists())

    @unittest.skipUnless(LEGACY_AVAILABLE, 'Optional: prepare full runtime and set JY_LEGACY_TEST_RUNTIME')
    def test_legacy_rejects_native_even_with_plain_stale_mirror(self):
        with self.assertRaises(DraftError):
            reject_native_for_legacy(self.source)
        from jy_wrapper import JyProject
        before = hash_files(self.source)
        for overwrite in (True, False):
            with self.assertRaises(DraftError):
                JyProject('source', drafts_root=str(self.root), overwrite=overwrite)
        self.assertEqual(hash_files(self.source), before)

    @unittest.skipUnless(LEGACY_AVAILABLE, 'Optional: prepare full runtime and set JY_LEGACY_TEST_RUNTIME')
    def test_legacy_parse_failure_never_recreates(self):
        legacy = self.root / 'legacy'
        legacy.mkdir()
        (legacy / 'draft_info.json').write_text('{invalid')
        (legacy / 'draft_meta_info.json').write_text('{}')
        from jy_wrapper import JyProject
        before = hash_files(legacy)
        with self.assertRaises(DraftError):
            JyProject('legacy', drafts_root=str(self.root), overwrite=False)
        self.assertEqual(hash_files(legacy), before)


if __name__ == '__main__':
    unittest.main()
