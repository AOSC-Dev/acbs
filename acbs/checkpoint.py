from typing import List, Tuple
from acbs.base import ACBSPackageInfo
from acbs.main import BuildCore
from acbs.find import find_package
from acbs.utils import print_package_names, print_build_timings
from acbs import __version__

import pickle
import time
import logging
import os
import hashlib


class ACBSShrinkWrap(object):
    def __init__(self, cursor: int, timings: List[Tuple[str, float]], packages: List[ACBSPackageInfo], no_deps: bool):
        self.cursor = cursor
        self.timings = timings
        self.packages = packages
        # spec states
        self.sps: List[str] = []
        self.no_deps = no_deps
        self.version = __version__


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


def do_load_checkpoint(name: str) -> ACBSShrinkWrap:
    with open(name, 'rb') as f:
        return pickle.load(f)


def do_resume_checkpoint(filename: str):
    def resume_build():
        logging.debug('Queue: {}'.format(resumed_packages))
        logging.info('Packages to be resumed: {}'.format(
            print_package_names(resumed_packages, 5)))
        build_timings = state.timings.copy()
        builder.build_sequential(build_timings, resumed_packages)
        print_build_timings(build_timings)

    state = do_load_checkpoint(filename)
    builder = BuildCore({})
    logging.info('Resuming from {}'.format(filename))
    if state.version != __version__:
        logging.warning(
            'The state was check-pointed with a different version of acbs!')
        logging.warning('Undefined behavior might occur!')
    if state.no_deps:
        leftover = state.packages[state.cursor-1:]
        logging.warning('Resuming without dependency resolution.')
        logging.info('Resumed. {} packages to go.'.format(len(leftover)))
        builder.build_sequential(state.timings, leftover)
        return
    logging.info('Validating status...')
    if len(state.packages) != len(state.sps):
        raise ValueError(
            'Inconsistencies detected in the saved state! The file might be corrupted.')
    resumed_packages = []
    new_cursor = state.cursor - 1
    index = 0
    for p, v in zip(state.packages, state.sps):
        if checkpoint_spec(p) == v:
            resumed_packages.append(p)
            index += 1
            continue
        # the spec files changed
        if index < new_cursor:
            new_cursor = index
        resumed_packages.extend(find_package(p.name, builder.tree_dir))
        # index doesn't matter now, since changes have been detected
    if new_cursor != (state.cursor - 1):
        logging.warning(
            'Senario mismatch detected! Dependency resolution will be re-attempted.')
        resolved = builder.resolve_deps(resumed_packages)
        logging.info(
            'Dependencies resolved, {} packages in the queue'.format(len(resolved)))
        resume_build()
        return
    resume_build()
    return
