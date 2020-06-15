from typing import List, Optional, Dict, Tuple, Deque


class ACBSSourceInfo(object):
    def __init__(self, type: str, url: str, version: str, revision=None, branch=None, depth=None) -> None:
        self.type = type
        self.url = url
        self.subdir: Optional[str] = None
        self.version = version
        self.revision: Optional[str] = revision
        self.branch: Optional[str] = branch
        self.depth: Optional[int] = depth
        self.chksum: Tuple[str, str] = ('', '')
        # where the source file/folder is located (on local filesystem)
        self.source_location: Optional[str] = None

    def __repr__(self) -> str:
        return '<ACBSSourceInfo {type}: {url}:{branch}@{revision} integrity: {checksum}>'.format(type=self.type, url=self.url, branch=self.branch, revision=self.revision, checksum=self.chksum)


class ACBSPackageInfo(object):
    def __init__(self, name: str, deps: List[str], location: str, source_uri: ACBSSourceInfo) -> None:
        self.name = name
        self.rel = '0'
        self.deps = deps
        self.installables: List[str] = []  # installable dependencies
        self.build_location = ''
        self.base_slug = ''  # group slug (like extra-devel/llvm), if any
        self.group_seq = 0  # group sequence number
        self.source_uri = source_uri
        # script location (autobuild directory)
        self.script_location = location

    def __repr__(self) -> str:
        return '<ACBSPackageInfo {name}: - deps: {deps} - uri: {uri}>'.format(name=self.name, deps=self.deps, uri=self.source_uri)
