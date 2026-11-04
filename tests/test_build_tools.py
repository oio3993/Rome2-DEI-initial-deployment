"""Negative input/pack checks using synthetic data; no game files or DLL execution."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import build_pack
from project import BUILD, BOOTSTRAP, check_dll, decode_payload, sha, write_report
from pack_io import make_pack, read_pack
from verify_release import verify_pack


class BuildTools(unittest.TestCase):
    def test_roundtrip(self):
        values={'campaigns\\fixture\\scripting.lua':b'-- fixture\n','lua_scripts\\x.lua':b'return true\n'}
        self.assertEqual(read_pack(make_pack(values)),values)

    def test_truncated_header(self):
        with self.assertRaises(ValueError):read_pack(b'PFH4')

    def test_truncated_payload(self):
        with self.assertRaises(ValueError):read_pack(make_pack({'x.lua':b'abc'})[:-1])

    def test_trailing_bytes(self):
        with self.assertRaises(ValueError):read_pack(make_pack({'x.lua':b'abc'})+b'bad')

    def test_bad_index_bounds(self):
        value=bytearray(make_pack({'x.lua':b'abc'}));struct.pack_into('<I',value,20,0xffffffff)
        with self.assertRaises(ValueError):read_pack(bytes(value))

    def test_unsafe_paths(self):
        for name in ('..\\x.lua','/x.lua','D:\\x.lua','x\\..\\y.lua','x\\\\y.lua'):
            with self.subTest(name=name),self.assertRaises(ValueError):make_pack({name:b'a'})

    def test_case_duplicate(self):
        with self.assertRaises(ValueError):make_pack({'x.lua':b'a','X.lua':b'b'})

    def test_missing_campaigns(self):
        BUILD.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD) as temp:
            with self.assertRaisesRegex(ValueError,'Missing campaign'):build_pack.load_campaigns(Path(temp))

    def test_changed_campaign_rejected(self):
        BUILD.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD) as temp:
            root=Path(temp);(root/'fixture').mkdir();(root/'fixture/scripting.lua').write_bytes(b'changed')
            with patch.dict(build_pack.CAMPAIGN_SHA,{'fixture':sha(b'known')},clear=True):
                with self.assertRaisesRegex(ValueError,'Unverified DEI'):build_pack.load_campaigns(root)

    def test_duplicate_bootstrap_rejected(self):
        BUILD.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD) as temp:
            root=Path(temp);(root/'fixture').mkdir();data=b'-- fixture\n'+BOOTSTRAP
            (root/'fixture/scripting.lua').write_bytes(data)
            with patch.dict(build_pack.CAMPAIGN_SHA,{'fixture':sha(data)},clear=True):
                with self.assertRaisesRegex(ValueError,'already exists'):build_pack.load_campaigns(root)

    def test_wrong_native_rejected(self):
        with self.assertRaises(ValueError):check_dll(b'MZwrong')

    def test_linked_checks_are_not_silently_skipped(self):
        import verify_native
        BUILD.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD) as temp:
            with patch.object(verify_native,'root',Path(temp)):
                with self.assertRaisesRegex(ValueError,'Linked checks require'):verify_native.verify()

    def test_payload_range_rejected(self):
        with self.assertRaises(ValueError):decode_payload(b'return "\\999"')

    def test_tampered_real_pack_rejected(self):
        from project import DLL,DIST,PACK_NAME
        raw=bytearray((DIST/PACK_NAME).read_bytes());raw[-1]^=1
        with self.assertRaises(ValueError):verify_pack(bytes(raw),DLL.read_bytes())


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(BuildTools)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    write_report('build_tools_tests.json',dict(passed=result.wasSuccessful(),test_count=result.testsRun,
                 synthetic_and_tamper_tests=True,game_executed=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
