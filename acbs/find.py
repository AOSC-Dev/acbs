import os
from typing import List, Dict, Optional

from acbs.const import TMP_DIR
from acbs.parser import parse_package, ACBSPackageInfo, ACBSSourceInfo
from acbs.utils import make_build_dir


def check_package_group(name: str, search_path: str, entry_path: str, stage2: bool) -> Optional[List[ACBSPackageInfo]]:
    # is this a package group?
    if os.path.basename(entry_path) == os.path.basename(name) and os.path.isfile(os.path.join(search_path, entry_path, 'spec')):
        stub = ACBSPackageInfo(name, [], '', [ACBSSourceInfo('none', '', '')])
        stub.base_slug = entry_path
        return expand_package_group(stub, search_path, stage2)
    with os.scandir(os.path.join(search_path, entry_path)) as group:
        # scan potential package groups
        for entry_group in group:
            full_search_path = os.path.join(
                search_path, entry_path, entry_group.name)
            # condition: `defines` inside a folder but not named `autobuild`
            if os.path.basename(full_search_path) == 'autobuild' or not os.path.isfile(
                    os.path.join(full_search_path, 'defines')):
                continue
            # because the package inside the group will have a different name than the folder name
            # we will parse the defines file to decide
            result = parse_package(full_search_path, stage2)
            if result and result.name == name:
                # name of the package inside the group
                package_alias = os.path.basename(
                    full_search_path)
                try:
                    group_seq = int(
                        package_alias.split('-')[0])
                except (ValueError, IndexError) as ex:
                    raise ValueError('Invalid package alias: {alias}'.format(
                        alias=package_alias)) from ex
                group_root = os.path.realpath(
                    os.path.join(full_search_path, '..'))
                group_category = os.path.realpath(
                    os.path.join(group_root, '..'))
                result.base_slug = '{cat}/{root}'.format(cat=os.path.basename(
                    group_category), root=os.path.basename(group_root))
                result.group_seq = group_seq
                group_result = expand_package_group(
                    result, search_path, stage2)
                return group_result
    return None


def find_package(name: str, search_path: str, stage2: bool) -> List[ACBSPackageInfo]:
    if os.path.isfile(os.path.join(search_path, name)):
        with open(os.path.join(search_path, name), 'rt') as f:
            content = f.read()
        packages = content.splitlines()
        results = []
        print()
        for n, p in enumerate(packages):
            print(f'[{n + 1}/{len(packages)}] {name} > {p:15}\r', end='', flush=True)
            p = p.strip()
            if not p or p.startswith('#'):
                continue
            found = find_package_inner(p, search_path, stage2=stage2)
            if not found:
                raise RuntimeError(
                    f'Package {p} requested in {name} was not found.')
            results.extend(found)
        print()
        return results
    return find_package_inner(name, search_path, stage2=stage2)


def find_package_inner(name: str, search_path: str, group=False, stage2: bool=False) -> List[ACBSPackageInfo]:
    if os.path.isdir(os.path.join(search_path, name)):
        flat_path = os.path.join(search_path, name, 'autobuild')
        if os.path.isdir(flat_path):
            return [parse_package(os.path.join(search_path, name, 'autobuild'), stage2)]
        # is this a package group?
        group_result = check_package_group(name, search_path, name, stage2)
        if group_result:
            return group_result
    with os.scandir(search_path) as it:
        # scan categories
        for entry in it:
            if not entry.is_dir():
                continue
            with os.scandir(os.path.join(search_path, entry.name)) as inner:
                # scan package directories
                for entry_inner in inner:
                    if not entry_inner.is_dir():
                        continue
                    full_search_path = os.path.join(
                        search_path, entry.name, entry_inner.name, 'autobuild')
                    if entry_inner.name == name and os.path.isdir(full_search_path):
                        return [parse_package(full_search_path, stage2)]
                    if not group:
                        continue
                    # is this a package group?
                    group_result = check_package_group(
                        name, search_path, os.path.join(entry.name, entry_inner.name), stage2)
                    if group_result:
                        return group_result
    if group:
        return []
    else:
        # if cannot find a package without considering it as part of a group
        # then re-search with group enabled
        return find_package_inner(name, search_path, True)


def check_package_groups(packages: List[ACBSPackageInfo]):
    """In AOSC OS build rules, the package group need to be built sequentially together.
    This function will check if the package inside the group will be built sequentially
    """
    groups_seen: Dict[str, int] = {}
    for pkg in packages:
        base_slug = pkg.base_slug
        if not base_slug:
            continue
        if base_slug in groups_seen:
            if groups_seen[base_slug] > pkg.group_seq:
                raise ValueError('Package {} (in {}) has a different sequential order (#{}) after dependency resolution (should be #{})'.format(
                    pkg.name, base_slug, pkg.group_seq, groups_seen[base_slug] + 1))
        else:
            groups_seen[base_slug] = pkg.group_seq


def expand_package_group(package: ACBSPackageInfo, search_path: str, stage2: bool) -> List[ACBSPackageInfo]:
    group_root = os.path.join(search_path, package.base_slug)
    original_base = package.base_slug
    actionables: List[ACBSPackageInfo] = []
    for entry in os.scandir(group_root):
        if not entry.is_dir():
            continue
        name = entry.name
        splitted = name.split('-', 1)
        if len(splitted) != 2:
            raise ValueError(
                'Malformed sub-package name: {name}'.format(name=entry.name))
        try:
            sequence = int(splitted[0])
            package = parse_package(entry.path, stage2)
            if package:
                package.base_slug = original_base
                package.group_seq = sequence
                actionables.append(package)
        except ValueError as ex:
            raise ValueError(
                'Malformed sub-package name: {name}'.format(name=entry.name)) from ex
    # because the directory order is arbitrary, we need to sort them
    actionables = sorted(actionables, key=lambda a: a.group_seq)
    # pre-assign build location for sub-packages
    location = make_build_dir(TMP_DIR)
    for a in actionables:
        a.build_location = location
    return actionables
