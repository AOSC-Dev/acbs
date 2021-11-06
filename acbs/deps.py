from collections import OrderedDict, defaultdict, deque
from typing import List, Dict, Deque

from acbs.find import find_package
from acbs.parser import ACBSPackageInfo, check_buildability

# package information cache
pool: Dict[str, ACBSPackageInfo] = {}


def tarjan_search(packages: 'OrderedDict[str, ACBSPackageInfo]', search_path: str) -> List[List[ACBSPackageInfo]]:
    """This function describes a Tarjan's strongly connected components algorithm.
    The resulting list of ACBSPackageInfo are sorted topologically as a byproduct of the algorithm
    """
    # Initialize state trackers
    lowlink: Dict[str, int] = defaultdict(lambda: -1)
    index: Dict[str, int] = defaultdict(lambda: -1)
    stackstate: Dict[str, bool] = defaultdict(bool)
    stack: Deque[str] = deque()
    results: List[List[ACBSPackageInfo]] = []
    packages_list: List[str] = [i for i in packages]
    pool.update(packages)
    for i in packages_list:
        if index[i] == -1:  # recurse on each package that is not yet visited
            strongly_connected(search_path, packages_list, results, packages,
                               i, lowlink, index, stackstate, stack)
    return results


def prepare_for_reorder(package: ACBSPackageInfo, packages_list: List[str]) -> ACBSPackageInfo:
    """This function prepares the package for reordering.
    The idea is to move the installable dependencies which are in the build list to the "uninstallable" list.
    """
    new_installables = []
    for d in package.installables:
        # skip self-dependency
        if d == package.name:
            new_installables.append(d)
            continue
        try:
            packages_list.index(d)
            package.deps.append(d)
        except ValueError:
            new_installables.append(d)
    package.installables = new_installables
    return package


def strongly_connected(search_path: str, packages_list: List[str], results: list, packages: 'OrderedDict[str, ACBSPackageInfo]', vert: str, lowlink: Dict[str, int], index: Dict[str, int], stackstate: Dict[str, bool], stack: Deque[str], depth=0):
    # update depth indices
    index[vert] = depth
    lowlink[vert] = depth
    depth += 1
    stackstate[vert] = True
    stack.append(vert)

    # search package begin
    print(f'[{len(results) + 1}/{len(pool)}] {vert}\t\t\r', end='', flush=True)
    current_package = packages.get(vert)
    if current_package is None:
        package = pool.get(vert) or find_package(vert, search_path)
        if not package:
            raise ValueError(
                f'Package {vert} not found')
        if isinstance(package, list):
            for s in package:
                if vert == s.name:
                    current_package = s
                    pool[s.name] = s
                    continue
                pool[s.name] = s
                packages_list.append(s.name)
        else:
            current_package = package
            pool[vert] = current_package
    assert current_package is not None
    # first check if this dependency is buildable
    # when `required_by` argument is present, it will raise an exception when the dependency is unbuildable.
    check_buildability(current_package, stack[-1] if len(stack) > 0 else '<unknown>')
    # search package end
    # Look for adjacent packages (dependencies)
    for p in current_package.deps:
        if index[p] == -1:
            # recurse on unvisited packages
            strongly_connected(search_path, packages_list, results, packages,
                               p, lowlink, index, stackstate, stack, depth)
            lowlink[vert] = min(lowlink[p], lowlink[vert])
        # adjacent package is in the stack which means it is part of a loop
        elif stackstate[p] is True:
            lowlink[vert] = min(lowlink[p], index[vert])

    w = ''
    result = []
    # if this is a root vertex
    if lowlink[vert] == index[vert]:
        # the current stack contains the vertices that belong to the same loop
        # if the stack only contains one vertex, then there is no loop there
        while w != vert:
            w = stack.pop()
            result.append(pool[w])
            stackstate[w] = False
        results.append(result)
