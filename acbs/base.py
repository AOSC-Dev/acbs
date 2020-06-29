from typing import List, Optional, Tuple

from acbs import __version__


class ACBSSourceInfo(object):
    def __init__(self, type: str, url: str, revision=None, branch=None, depth=None) -> None:
        self.type = type
        self.url = url
        self.revision: Optional[str] = revision
        self.branch: Optional[str] = branch
        self.depth: Optional[int] = depth
        self.chksum: Tuple[str, str] = ('', '')
        # where the source file/folder is located (on local filesystem)
        self.source_location: Optional[str] = None

    def __repr__(self) -> str:
        return '<ACBSSourceInfo {type}: {url}:{branch}@{revision} integrity: {checksum}>'.format(type=self.type, url=self.url, branch=self.branch, revision=self.revision, checksum=self.chksum)


class ACBSPackageInfo(object):
    def __init__(self, name: str, deps: List[str], location: str, source_uri: List[ACBSSourceInfo]) -> None:
        self.name = name
        self.rel = '0'
        self.deps = deps
        self.installables: List[str] = []  # installable dependencies
        self.build_location = ''
        self.base_slug = ''  # group slug (like extra-devel/llvm), if any
        self.group_seq = 0  # group sequence number
        self.source_uri = source_uri
        self.version = ''
        self.subdir: Optional[str] = None
        # script location (autobuild directory)
        self.script_location = location

    def __repr__(self) -> str:
        return '<ACBSPackageInfo {name}: - deps: {deps} - uri: {uri}>'.format(name=self.name, deps=self.deps, uri=self.source_uri)


class ACBSShrinkWrap(object):
    def __init__(self, cursor: int, timings: List[Tuple[str, float]], packages: List[ACBSPackageInfo], no_deps: bool):
        self.cursor = cursor
        self.timings = timings
        self.packages = packages
        # spec states
        self.sps: List[str] = []
        self.dpkg_state: str = ''
        self.no_deps = no_deps
        self.version = __version__
