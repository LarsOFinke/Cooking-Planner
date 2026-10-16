import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))

from cooking_planner.launcher import prepare_data_directory


class DataDirectoryTest(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'POSIX permissions only')
    def test_default_directory_is_private_even_when_it_already_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / '.cooking-planner'
            directory.mkdir(mode=0o775)
            directory.chmod(0o775)
            prepare_data_directory(directory, default_location=True)
            self.assertEqual(0o700, stat.S_IMODE(directory.stat().st_mode))

    @unittest.skipUnless(os.name == 'posix', 'POSIX permissions only')
    def test_new_configured_directory_starts_private(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'configured'
            prepare_data_directory(directory, default_location=False)
            self.assertEqual(0o700, stat.S_IMODE(directory.stat().st_mode))


if __name__ == '__main__':
    unittest.main()
