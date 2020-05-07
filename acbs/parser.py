from typing import List, Optional, Dict, Tuple, Deque
from collections import OrderedDict, defaultdict, deque
from acbs import bashvar
from acbs.utils import get_arch_name
from acbs.base import ACBSPackageInfo, ACBSSourceInfo
import os
import configparser


def parse_package_url(var: Dict[str, str]) -> ACBSSourceInfo:
    acbs_source_info = ACBSSourceInfo('none', '', '')
    if var.get('DUMMYSRC') in ['y', 'yes', '1']:
        return acbs_source_info
    version = var.get('VER')
    if version:
        acbs_source_info.version = version
    subdir = var.get('SUBDIR')
    if subdir:
        acbs_source_info.subdir = subdir
    url = var.get('SRCTBL')
    if url:
        acbs_source_info.type = 'tarball'
        acbs_source_info.url = url
        chksum = var.get('CHKSUM')
        if not chksum:
            return acbs_source_info
        chksum_ = chksum.split('::', 1)
        if len(chksum_) != 2:  # malformed checksum line
            return acbs_source_info
        acbs_source_info.chksum = (chksum_[0], chksum_[1])
        return acbs_source_info
    # VCS related
    for type_ in ('GIT', 'BZR', 'SVN', 'HG', 'BK'):
        url = var.get('{type_}SRC'.format(type_=type_))
        if url:
            acbs_source_info.type = type_
            acbs_source_info.url = url
            acbs_source_info.revision = var.get(
                '{type_}CO'.format(type_=type_))
            acbs_source_info.branch = var.get(
                '{type_}BRANCH'.format(type_=type_))
    # No sources specified?
    if acbs_source_info.type == 'none':
        raise ValueError('No sources specified, if this is intended, please set `DUMMYSRC=1`')
    return acbs_source_info


def parse_package(location: str) -> ACBSPackageInfo:
    defines_location = os.path.join(location, "defines")
    spec_location = os.path.join(location, '..', 'spec')
    with open(defines_location, 'rt') as f:
        var = bashvar.eval_bashvar(f.read(), filename=defines_location)
    with open(spec_location, 'rt') as f:
        spec_var = bashvar.eval_bashvar(f.read(), filename=spec_location)
    deps: str = var.get('PKGDEP__{arch}'.format(
        arch=arch.upper())) or var.get('PKGDEP') or ''
    builddeps: str = var.get('BUILDDEP__{arch}'.format(
        arch=arch.upper())) or var.get('BUILDDEP')
    deps += ' ' + (builddeps or '')  # add builddep
    # architecture specific dependencies
    acbs_source_info = parse_package_url(spec_var)
    if not deps:
        return ACBSPackageInfo(name=var['PKGNAME'], deps=[], location=location, source_uri=acbs_source_info)
    result = ACBSPackageInfo(
        name=var['PKGNAME'], deps=deps.split(), location=location, source_uri=acbs_source_info)

    return result


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


arch = os.environ.get('CROSS') or os.environ.get(
    'ARCH') or get_arch_name() or ''
