import unittest

from unittest.mock import create_autospec

import acbs.parser

def fake_pm(package):
    return package

class TestParser(unittest.TestCase):
    def test_parse_no_arch(self):
        acbs.parser.arch = 'none'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package('./tests/fixtures/test-1/autobuild')
        self.assertEqual(package.deps, ['test-2', 'test-3', 'test-4'])
        self.assertEqual(package.source_uri.version, '1')
        self.assertEqual(package.source_uri.type, 'none')

    def test_parse_arch(self):
        acbs.parser.arch = 'arch'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package('./tests/fixtures/test-1/autobuild')
        self.assertEqual(package.deps, ['test-2', 'test-3', 'test-17'])
        self.assertEqual(package.source_uri.version, '1')
        self.assertEqual(package.source_uri.type, 'none')


if __name__ == '__main__':
    unittest.main()
