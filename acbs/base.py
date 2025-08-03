import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from acbs import __version__


@dataclass
class ACBSSourceInfo:
    type: str
    url: str
    revision: Optional[str] = None
    branch: Optional[str] = None
    depth: Optional[int] = None
    chksum: Tuple[str, str] = ('', '')
    source_name: Optional[str] = ''
    use_url_name: bool = False
    # where the source file/folder is located (on local filesystem)
    source_location: Optional[str] = None
    enabled: bool = True
    # copy the repository to the build directory
    copy_repo: bool = False
    # this is a tristate: 0 - off; 1 - on (non-recursive); 2 - recursive
    submodule: int = 2


@dataclass
class ACBSPackageInfo:
    name: str
    deps: List[str]
    location: str
    source_uri: List[ACBSSourceInfo]
    rel: str = '0'
    installables: List[str] = field(default_factory=list)
    build_location: str = ''
    base_slug: str = ''  # group slug (like extra-devel/llvm), if any
    group_seq: int = 0  # group sequence number
    version: str = ''
    epoch: str = ''
    subdir: Optional[str] = None
    fail_arch: Optional[re.Pattern] = None  # fail_arch regex
    bin_arch: str = ''
    script_location: str = field(init=False)  # script location (autobuild directory)
    exported: Dict[str, str] = field(default_factory=dict)  # extra exported variables from spec
    modifiers: str = ''  # modifiers to be applied to the source file/folder (only available in autobuild4)

    def __post_init__(self):
        self.script_location = self.location

    @staticmethod
    def is_in_stage2(modifiers: str) -> bool:
        return '+stage2' in modifiers.lower()


@dataclass
class ACBSShrinkWrap:
    cursor: int
    timings: List[Tuple[str, float]]
    packages: List[ACBSPackageInfo]
    no_deps: bool
    # spec states
    sps: List[str] = field(default_factory=list)
    dpkg_state: str = ''
    version: str = __version__
