from dataclasses import dataclass, field

from acbs import __version__


@dataclass
class ACBSSourceInfo:
    type: str
    url: str
    revision: str | None = None
    branch: str | None = None
    depth: int | None = None
    chksum: tuple[str, str] = ('', '')
    source_name: str | None = ''
    use_url_name: bool = False
    # where the source file/folder is located (on local filesystem)
    source_location: str | None = None
    enabled: bool = True
    # copy the repository to the build directory
    copy_repo: bool = False
    # this is a tristate: 0 - off; 1 - on (non-recursive); 2 - recursive
    submodule: int = 2


@dataclass
class ACBSPackageInfo:
    name: str
    deps: list[str]
    location: str
    source_uri: list[ACBSSourceInfo]
    rel: str = '0'
    installables: list[str] = field(default_factory=list)
    build_location: str = ''
    base_slug: str = ''  # group slug (like extra-devel/llvm), if any
    group_seq: int = 0  # group sequence number
    version: str = ''
    epoch: str = ''
    subdir: str | None = None
    fail_arch: str | None = None  # fail_arch expression
    bin_arch: str = ''
    script_location: str = field(init=False)  # script location (autobuild directory)
    exported: dict[str, str] = field(default_factory=dict)  # extra exported variables from spec
    modifiers: str = ''  # modifiers to be applied to the source file/folder (only available in autobuild4)

    def __post_init__(self):
        self.script_location = self.location

    @staticmethod
    def is_in_stage2(modifiers: str) -> bool:
        return '+stage2' in modifiers.lower()


@dataclass
class ACBSShrinkWrap:
    cursor: int
    timings: list[tuple[str, float]]
    packages: list[ACBSPackageInfo]
    no_deps: bool
    # spec states
    sps: list[str] = field(default_factory=list)
    dpkg_state: str = ''
    version: str = __version__
