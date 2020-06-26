import pickle
import logging

from acbs import __version__
from acbs.base import ACBSShrinkWrap, ACBSPackageInfo
from acbs.main import BuildCore
from acbs.find import find_package
from acbs.utils import print_package_names, print_build_timings
from acbs.checkpoint import checkpoint_spec


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
