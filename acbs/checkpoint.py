import hashlib
import io
import logging
import os
import pickle
import tarfile
import time
from typing import IO, List, Tuple, cast

from acbs.base import ACBSPackageInfo, ACBSShrinkWrap
from acbs.const import DPKG_DIR


class Hasher(io.IOBase):
    def __init__(self):
        self.hash_obj = hashlib.new("sha256")

    def write(self, data):
        self.hash_obj.update(data)

    def hexdigest(self):
        return self.hash_obj.hexdigest()


def checkpoint_spec(package: ACBSPackageInfo) -> str:
    f = cast(IO[bytes], Hasher())
    with tarfile.open(mode='w|', fileobj=f) as tar:
        tar.add(os.path.join(package.script_location, '..'))
    return f.hexdigest()  # type: ignore


def checkpoint_dpkg() -> str:
    hasher = hashlib.new("sha256")
    with open(os.path.join(DPKG_DIR, 'status'), 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def checkpoint_text(packages: List[ACBSPackageInfo]) -> str:
    return '\n'.join([package.name for package in packages])


def checkpoint_to_group(packages: List[ACBSPackageInfo], path: str) -> str:
    groups = os.path.join(path, 'groups')
    if not os.path.isdir(groups):
        os.makedirs(groups)
    filename = 'acbs-{}'.format(int(time.time()))
    with open(os.path.join(groups, filename), 'wt') as f:
        f.write(checkpoint_text(packages))
    return filename


def do_shrink_wrap(data: ACBSShrinkWrap, path: str) -> str:
    # stamp the spec files
    for package in data.packages:
        data.sps.append(checkpoint_spec(package))
    data.dpkg_state = checkpoint_dpkg()
    filename = os.path.join(path, '{}.acbs-ckpt'.format(int(time.time())))
    with open(filename, 'wb') as f:
        pickle.dump(data, f)
    return filename
