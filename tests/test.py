import unittest

from unittest.mock import create_autospec

import acbs.parser
import acbs.find

from acbs.utils import make_build_dir
from acbs.const import TMP_DIR


def fake_pm(package):
    return package


def find_package_generic(name: str):
    acbs.parser.arch = 'none'
    acbs.parser.filter_dependencies = fake_pm
    make_build_dir_mock = unittest.mock.Mock(
        spec=make_build_dir, return_value='/tmp/')
    acbs.find.make_build_dir = make_build_dir_mock
    return acbs.find.find_package(name, './tests/'), make_build_dir_mock


class TestParser(unittest.TestCase):
    def test_parse_no_arch(self):
        acbs.parser.arch = 'none'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package(
            './tests/fixtures/test-1/autobuild')
        self.assertEqual(package.deps, ['test-2', 'test-3', 'test-4'])
        self.assertEqual(package.source_uri.version, '1')
        self.assertEqual(package.source_uri.type, 'none')

    def test_parse_arch(self):
        acbs.parser.arch = 'arch'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package(
            './tests/fixtures/test-1/autobuild')
        self.assertEqual(package.deps, ['test-2', 'test-3', 'test-17'])
        self.assertEqual(package.source_uri.version, '1')
        self.assertEqual(package.source_uri.type, 'none')


class TestSearching(unittest.TestCase):
    def test_basic_find(self):
        result, _ = find_package_generic('test-1')
        self.assertEqual(len(result), 1)

    def test_basic_prefixed_find(self):
        result, _ = find_package_generic('fixtures/test-1')
        self.assertEqual(len(result), 1)

    def test_subpackage_find(self):
        result, make_build_dir_mock = find_package_generic('sub-1')
        make_build_dir_mock.assert_called_once_with(TMP_DIR)
        self.assertEqual(len(result), 2)

    def test_group_expand(self):
        result, make_build_dir_mock = find_package_generic('test-2')
        make_build_dir_mock.assert_called_once_with(TMP_DIR)
        self.assertEqual(len(result), 2)

    def test_group_prefixed_expand(self):
        result, make_build_dir_mock = find_package_generic('fixtures/test-2')
        make_build_dir_mock.assert_called_once_with(TMP_DIR)
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
