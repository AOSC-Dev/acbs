import configparser
import logging
import os
import re
from collections import OrderedDict
from typing import Dict, List, Optional
from urllib.parse import urlparse

from acbs import bashvar
from acbs.base import ACBSPackageInfo, ACBSSourceInfo
from acbs.pm import filter_dependencies
from acbs.utils import fail_arch_regex, get_arch_name, tarball_pattern

generate_mode = False


def get_defines_file_path(location: str, stage2: bool) -> str:
    '''
    Return ${location}/defines or ${location}/defines.stage2 depending on the value of stage2 and whether the .stage2 file exists.
    '''
    if stage2 and os.path.exists(os.path.join(location, 'defines.stage2')):
        return os.path.join(location, 'defines.stage2')
    else:
        return os.path.join(location, 'defines')


def parse_url_schema(url: str, checksum: str) -> ACBSSourceInfo:
    acbs_source_info = ACBSSourceInfo('none', '', '')
    url_split = url.split('::', 2)
    schema = ''
    url_plain = ''
    if len(url_split) < 2:
        url_plain = url
        if re.search(tarball_pattern, url_plain):
            schema = 'tarball'
        elif url_plain.endswith('.git') or url_plain.startswith('git://'):
            schema = 'git'
        else:
            raise ValueError(
                'Unable to deduce source type for {}.'.format(url_plain))
    elif len(url_split) < 3:
        schema = url_split[0].lower()
        url_plain = url_split[1]
    else:
        schema, options, url_plain = url_split
        schema = schema.lower()
        acbs_source_info = parse_fetch_options(options, acbs_source_info)
    acbs_source_info.type = 'tarball' if schema == 'tbl' else schema
    chksum_ = checksum.split('::', 1)
    if len(chksum_) != 2 and checksum != 'SKIP':
        raise ValueError('Malformed checksum: {}'.format(checksum))
    acbs_source_info.chksum = (
        chksum_[0], chksum_[1]) if checksum != 'SKIP' else ('none', '')
    acbs_source_info.url = url_plain
    if acbs_source_info.use_url_name and acbs_source_info.source_name:
        raise ValueError("Option 'use-url-name' can NOT be used with the 'rename' option.")
    if acbs_source_info.use_url_name:
        parsed = urlparse(url_plain)
        acbs_source_info.source_name = os.path.basename(parsed.path)
    return acbs_source_info


def parse_fetch_options(options: str, acbs_source_info: ACBSSourceInfo):
    options_split = options.split(';')
    for option in options_split:
        k, v = option.split('=')
        if k == 'branch':
            acbs_source_info.branch = v.strip()
        elif k == 'rename':
            acbs_source_info.source_name = v.strip()
        elif k == 'use-url-name':
            acbs_source_info.use_url_name = v.strip() == 'true'
        elif k == 'commit':
            acbs_source_info.revision = v.strip()
        elif k == 'copy-repo':
            acbs_source_info.copy_repo = v.strip() == 'true'
        elif k == 'submodule':
            translated = {
                'false': 0,
                'true': 1,
                'recursive': 2,
            }.get(v.strip())
            if translated is None:
                raise ValueError(f'Invalid submodule directive: {v}')
            acbs_source_info.submodule = translated
    return acbs_source_info


def parse_package_url(var: Dict[str, str], ignore_empty_srcs: bool) -> List[ACBSSourceInfo]:
    acbs_source_info: List[ACBSSourceInfo] = []
    sources = var.get('SRCS__{arch}'.format(
        arch=arch.upper())) or var.get('SRCS')
    checksums = var.get('CHKSUMS__{arch}'.format(
        arch=arch.upper())) or var.get('CHKSUMS')
    if var.get('DUMMYSRC') in ['y', 'yes', '1']:
        acbs_source_info.append(ACBSSourceInfo('none', '', ''))
        return acbs_source_info
    if sources is None:
        if not ignore_empty_srcs:
            raise ValueError(
                'Source definition is missing. If that is intended, '
                'perhaps you want to set DUMMYSRC=1.')
        else:
            return []
    if checksums is None and not generate_mode:
        raise ValueError(
            'Missing checksums. You can use `SKIP` for VCS sources.')
    sources_list = sources.strip().split()
    checksums_list = checksums.strip().split() if checksums else [
        '::'] * len(sources_list)
    if len(sources_list) != len(checksums_list):
        raise ValueError(
            f'Sources array and checksums array must have the same length (Sources: {len(sources_list)}, Checksums: {len(checksums_list)}).'
        )
    for s, c in zip(sources_list, checksums_list):
        acbs_source_info.append(parse_url_schema(s, c))
    return acbs_source_info


def parse_package(location: str, modifiers: str) -> ACBSPackageInfo:
    # Ignore (seemingly) empty srcs on unbuildable archs, if the package
    # uses different sources for each (supported) architectures.
    ignore_empty_srcs: bool = False
    logging.debug('Parsing {}...'.format(location))
    stage2 = ACBSPackageInfo.is_in_stage2(modifiers)
    # Call a helper function to check if there's a stage2 defines automatically
    defines_location = get_defines_file_path(location, stage2)
    spec_location = os.path.join(location, '..', 'spec')
    with open(defines_location, 'rt') as f:
        var = bashvar.eval_bashvar(f.read(), filename=defines_location)
    with open(spec_location, 'rt') as f:
        spec_var = bashvar.eval_bashvar(f.read(), filename=spec_location)
    fail_arch = var.get('FAIL_ARCH')
    fail_arch_re: Optional[re.Pattern] = None
    if fail_arch:
        fail_arch_re = fail_arch_regex(fail_arch)
        if fail_arch_re.match(arch):
            logging.debug(f'Package {var["PKGNAME"]} is not buildable on current arch: {arch}')
            # Continue parsing but ignore any source error, since we still
            # need the complete tree.
            # There are some packages that use different sources for each
            # (supported) architectures, but for unbuildable packages the
            # source info parser will fail, as there is no SRCS for current
            # arch.
            ignore_empty_srcs = True
    deps_arch: Optional[str] = var.get('PKGDEP__{arch}'.format(
        arch=arch.upper()))
    # determine whether this is an undefined value or an empty string
    deps: str = (var.get('PKGDEP') or '') if deps_arch is None else deps_arch
    builddeps_arch: Optional[str] = var.get('BUILDDEP__{arch}'.format(
        arch=arch.upper()))
    builddeps: str = var.get(
        'BUILDDEP') if builddeps_arch is None else builddeps_arch
    deps += ' ' + (builddeps or '')  # add builddep
    # architecture specific dependencies
    acbs_source_info = parse_package_url(spec_var, ignore_empty_srcs)
    if not deps:
        result = ACBSPackageInfo(
            name=var['PKGNAME'], deps=[], location=location, source_uri=acbs_source_info)
    else:
        result = ACBSPackageInfo(
            name=var['PKGNAME'], deps=deps.split(), location=location, source_uri=acbs_source_info)
    result.bin_arch = var.get('ABHOST') or arch
    release = spec_var.get('REL') or '0'
    result.rel = release
    version = spec_var.get('VER')
    if fail_arch:
        result.fail_arch = fail_arch_re
    if version:
        result.version = version
    subdir = spec_var.get('SUBDIR')
    if subdir:
        result.subdir = subdir
    epoch = spec_var.get('EPOCH')
    if epoch:
        result.epoch = epoch
    result.modifiers = modifiers
    # collect exported variables (prefixed with `__`)
    for k, v in spec_var.items():
        if k.startswith('__'):
            result.exported[k] = v

    return filter_dependencies(result)


def get_deps_graph(packages: List[ACBSPackageInfo]) -> 'OrderedDict[str, ACBSPackageInfo]':
    'convert flattened list to adjacency list'
    result = {}
    for i in packages:
        result[i.name] = i
    return OrderedDict(result)


def get_tree_by_name(filename: str, tree_name) -> str:
    acbs_config = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation())
    with open(filename, 'rt') as conf_file:
        try:
            acbs_config.read_file(conf_file)
        except Exception as ex:
            raise Exception('Failed to read configuration file!') from ex
    try:
        tree_loc_dict = acbs_config[tree_name]
    except KeyError as ex:
        err_message = 'Tree not found: {}, defined trees: {}'.format(tree_name,
                                                                     ' '.join(acbs_config.sections()))
        raise ValueError(err_message) from ex
    try:
        tree_loc = tree_loc_dict['location']
    except KeyError as ex:
        raise KeyError(
            'Malformed configuration file: missing `location` keyword') from ex
    return tree_loc


def check_buildability(package: ACBSPackageInfo, required_by: Optional[str]=None) -> bool:
    if package.fail_arch and package.fail_arch.match(arch):
        if required_by:
            raise RuntimeError(f'{package.name} is required by `{required_by}` but is not buildable on `{arch}` (FAIL_ARCH).')
        else:
            return False
    return True


arch = os.environ.get('CROSS') or os.environ.get(
    'ARCH') or get_arch_name() or ''
if not arch:
    raise ValueError('Unable to determine architecture name')
