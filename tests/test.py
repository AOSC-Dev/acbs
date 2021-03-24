import unittest
import unittest.mock

import acbs.parser
import acbs.find
import acbs.pm

from acbs.utils import make_build_dir, guess_extension_name, fail_arch_regex
from acbs.const import TMP_DIR
from acbs.deps import tarjan_search
from acbs.parser import get_deps_graph, parse_url_schema


def fake_pm(package):
    return package


def check_scc(resolved):
    error = False
    for dep in resolved:
        if len(dep) > 1 or dep[0].name in dep[0].deps:
            # this is a SCC, aka a loop
            error = True
        elif not error:
            continue
    return error


def find_package_generic(name: str):
    acbs.parser.arch = 'none'
    acbs.parser.filter_dependencies = fake_pm
    make_build_dir_mock = unittest.mock.Mock(spec=make_build_dir, return_value='/tmp/')
    acbs.find.make_build_dir = make_build_dir_mock
    return acbs.find.find_package(name, './tests/'), make_build_dir_mock


class TestParser(unittest.TestCase):
    def test_parse_no_arch(self):
        acbs.parser.arch = 'none'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package('./tests/fixtures/test-1/autobuild')
        self.assertEqual(package.deps, ['test-2', 'test-3', 'test-4'])
        self.assertEqual(package.version, '1')
        self.assertEqual(package.source_uri[0].type, 'none')

    def test_parse_arch(self):
        acbs.parser.arch = 'arch'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package('./tests/fixtures/test-1/autobuild')
        self.assertEqual(package.deps, ['test-2', 'test-3', 'test-17'])
        self.assertEqual(package.version, '1')
        self.assertEqual(package.source_uri[0].type, 'none')

    def test_deps_loop(self):
        acbs.parser.arch = 'arch'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package('./tests/fixtures/test-3/autobuild')
        packages = tarjan_search(get_deps_graph([package]), './tests')
        error = check_scc(packages)
        self.assertEqual(error, True)

    def test_fail_arch(self):
        import re

        self.assertEqual(re.compile("^(?!amd64)"), fail_arch_regex("!amd64"))
        self.assertEqual(re.compile("^amd64"), fail_arch_regex("amd64"))
        self.assertEqual(re.compile("^(amd64|arm64)"), fail_arch_regex("(amd64|arm64)"))
        self.assertEqual(
            re.compile("^(?!amd64|arm64)"), fail_arch_regex("!(amd64|arm64)")
        )

    def test_parse_url(self):
        info = parse_url_schema('tbl::https://example.com', 'sha256::123')
        self.assertEqual(info.type, 'tarball')
        self.assertEqual(info.url, 'https://example.com')
        self.assertEqual(info.chksum, ('sha256', '123'))
        info = parse_url_schema('https://example.com/test.tar.gz', 'sha256::123')
        self.assertEqual(info.type, 'tarball')
        self.assertEqual(info.url, 'https://example.com/test.tar.gz')
        self.assertEqual(info.chksum, ('sha256', '123'))
        info = parse_url_schema('git://github.com/AOSC-Dev/acbs', 'SKIP')
        self.assertEqual(info.type, 'git')
        self.assertEqual(info.url, 'git://github.com/AOSC-Dev/acbs')
        self.assertEqual(info.chksum, ('none', ''))
        info = parse_url_schema(
            'git::commit=abcdef::git://github.com/AOSC-Dev/acbs', 'SKIP'
        )
        self.assertEqual(info.type, 'git')
        self.assertEqual(info.url, 'git://github.com/AOSC-Dev/acbs')
        self.assertEqual(info.revision, 'abcdef')
        self.assertEqual(info.chksum, ('none', ''))
        info = parse_url_schema(
            'git::commit=a2e5eff::https://github.com/AOSC-Dev/acbs#title', 'SKIP'
        )
        self.assertEqual(info.type, 'git')
        self.assertEqual(info.url, 'https://github.com/AOSC-Dev/acbs#title')
        self.assertEqual(info.revision, 'a2e5eff')
        self.assertEqual(info.chksum, ('none', ''))

    def test_parse_new_spec(self):
        acbs.parser.arch = 'none'
        acbs.parser.filter_dependencies = fake_pm
        package = acbs.parser.parse_package('./tests/fixtures/test-4/autobuild')
        self.assertEqual(package.deps, ['test-4'])
        self.assertEqual(package.version, '1')
        self.assertEqual(package.source_uri[0].type, 'git')
        self.assertEqual(package.source_uri[1].type, 'git')


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


class TestMisc(unittest.TestCase):
    def test_apt_name_escaping(self):
        self.assertEqual(acbs.pm.escape_package_name('test++'), 'test\\+\\+')
        self.assertEqual(acbs.pm.escape_package_name('test+-'), 'test\\+-')

    def test_apt_install_escaping(self):
        self.assertEqual(acbs.pm.escape_package_name_install('test++'), 'test\\+\\++')
        self.assertEqual(acbs.pm.escape_package_name_install('test+-'), 'test\\+-+')

    def test_guess_extension_name(self):
        self.assertEqual(guess_extension_name('test-1.2.3.tar.gz'), '.tar.gz')
        self.assertEqual(guess_extension_name('test-1.2.3.bin'), '.bin')
        self.assertEqual(guess_extension_name('test'), '')


if __name__ == '__main__':
    unittest.main()
