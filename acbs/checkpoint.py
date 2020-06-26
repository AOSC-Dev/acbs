from typing import List, Tuple
from acbs.base import ACBSPackageInfo, ACBSShrinkWrap
from acbs import __version__

import pickle
import time
import logging
import os
import hashlib


def checkpoint_spec(package: ACBSPackageInfo) -> str:
    hash_obj = hashlib.new("sha256")
    with open(os.path.join(package.script_location, '..', 'spec'), 'rb') as f:
        hash_obj.update(f.read())
    with open(os.path.join(package.script_location, 'defines'), 'rb') as f:
        hash_obj.update(f.read())
    return hash_obj.hexdigest()


def do_shrink_wrap(data: ACBSShrinkWrap) -> str:
    # stamp the spec files
    for package in data.packages:
        data.sps.append(checkpoint_spec(package))
    filename = '{}.acbs-ckpt'.format(int(time.time()))
    with open(filename, 'wb') as f:
        pickle.dump(data, f)
    return filename
