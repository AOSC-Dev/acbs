# coding: utf-8

"""
Fake magic bindings
"""
import subprocess

# Flag constants for open and setflags
MAGIC_NONE = NONE = 0
MAGIC_DEBUG = DEBUG = 1
MAGIC_SYMLINK = SYMLINK = 2
MAGIC_COMPRESS = COMPRESS = 4
MAGIC_DEVICES = DEVICES = 8
MAGIC_MIME_TYPE = MIME_TYPE = 16
MAGIC_CONTINUE = CONTINUE = 32
MAGIC_CHECK = CHECK = 64
MAGIC_PRESERVE_ATIME = PRESERVE_ATIME = 128
MAGIC_RAW = RAW = 256
MAGIC_ERROR = ERROR = 512
MAGIC_MIME_ENCODING = MIME_ENCODING = 1024
MAGIC_MIME = MIME = 1040  # MIME_TYPE + MIME_ENCODING
MAGIC_APPLE = APPLE = 2048

MAGIC_NO_CHECK_COMPRESS = NO_CHECK_COMPRESS = 4096
MAGIC_NO_CHECK_TAR = NO_CHECK_TAR = 8192
MAGIC_NO_CHECK_SOFT = NO_CHECK_SOFT = 16384
MAGIC_NO_CHECK_APPTYPE = NO_CHECK_APPTYPE = 32768
MAGIC_NO_CHECK_ELF = NO_CHECK_ELF = 65536
MAGIC_NO_CHECK_TEXT = NO_CHECK_TEXT = 131072
MAGIC_NO_CHECK_CDF = NO_CHECK_CDF = 262144
MAGIC_NO_CHECK_TOKENS = NO_CHECK_TOKENS = 1048576
MAGIC_NO_CHECK_ENCODING = NO_CHECK_ENCODING = 2097152

MAGIC_NO_CHECK_BUILTIN = NO_CHECK_BUILTIN = 4173824


class fakeMagic(object):

    def __init__(self):
        self.flags = []
        self.cmd_args = ['file', '-b']
        return

    def magic_open(self, flags=[]) -> None:
        self.flags = flags
        return

    def add_cmds(self) -> None:
        if (self.flags & MAGIC_MIME):
            self.cmd_args.append('-i')
        elif (self.flags & MAGIC_MIME_TYPE):
            self.cmd_args.append('--mime-type')
        elif (self.flags & MAGIC_SYMLINK):
            self.cmd_args.append('-L')
        elif (self.flags & MAGIC_COMPRESS):
            self.cmd_args.append('-z')

    def load(self) -> None:
        pass

    def file(self, *args) -> bytes:
        self.add_cmds()
        self.cmd_args.append(*args)
        return subprocess.check_output(self.cmd_args)


mgc = fakeMagic()


def open(flags: int):
    mgc.magic_open(flags)
    return mgc
