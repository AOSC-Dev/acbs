import pickle
import logging

from acbs import __version__
from acbs.base import ACBSShrinkWrap, ACBSPackageInfo
from acbs.main import BuildCore
from acbs.find import find_package
from acbs.utils import print_package_names, print_build_timings, make_build_dir
from acbs.checkpoint import checkpoint_spec, checkpoint_dpkg, checkpoint_to_group
from acbs.const import TMP_DIR
from acbs.pm import check_if_installed
from typing import List, Dict


def reassign_build_dir(packages: List[ACBSPackageInfo]):
    groups: Dict[str, str] = {}
    for package in packages:
        if package.base_slug:
            directory = groups.get(package.base_slug)
            if not directory:
                directory = make_build_dir(TMP_DIR)
                groups[package.base_slug] = directory
            package.build_location = directory
            continue
        package.build_location = ''
    return


def check_dpkg_state(state: ACBSShrinkWrap, packages: List[ACBSPackageInfo]) -> bool:
    if checkpoint_dpkg() == state.dpkg_state:
        return True
    logging.warning('DPKG state change detected. Re-checking dependencies...')
    for package in packages:
        if not check_if_installed(package.name):
            return False
    return True


def do_load_checkpoint(name: str) -> ACBSShrinkWrap:
    with open(name, 'rb') as f:
        return pickle.load(f)


def do_resume_checkpoint(filename: str, args):
    """
    Resume from checkpoint. This is an entry point.

    :param args: cmdline args from acbs-build.
    """
    def resume_build():
        logging.debug('Queue: {}'.format(resumed_packages))
        logging.info(
            'Packages to be resumed: {}'.format(
                print_package_names(resumed_packages, 5)
            )
        )
        build_timings = state.timings.copy()
        try:
            builder.build_sequential(build_timings, resumed_packages)
        except Exception as ex:
            # failed again?
            logging.exception(ex)
            builder.save_checkpoint(build_timings, resumed_packages)
        print_build_timings(build_timings)

    state = do_load_checkpoint(filename)
    builder = BuildCore(args)
    logging.info('Resuming from {}'.format(filename))
    if state.version != __version__:
        logging.warning('The state was check-pointed with a different version of acbs!')
        logging.warning('Undefined behavior might occur!')
    if state.no_deps:
        leftover = state.packages[state.cursor - 1 :]
        logging.warning('Resuming without dependency resolution.')
        logging.info('Resumed. {} packages to go.'.format(len(leftover)))
        builder.build_sequential(state.timings, leftover)
        return
    logging.info('Validating status...')
    if len(state.packages) != len(state.sps):
        raise ValueError(
            'Inconsistencies detected in the saved state! The file might be corrupted.'
        )
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
    if not check_dpkg_state(state, resumed_packages[:new_cursor]):
        name = checkpoint_to_group(resumed_packages[new_cursor:], builder.tree_dir)
        raise RuntimeError(
            'DPKG state mismatch. Unable to resume.\nACBS has created a new temporary group {} for you to continue.'.format(
                name
            )
        )
    resumed_packages = resumed_packages[new_cursor:]
    # clear the build directory of the first package
    reassign_build_dir(resumed_packages)
    if new_cursor != (state.cursor - 1):
        logging.warning(
            'Senario mismatch detected! Dependency resolution will be re-attempted.'
        )
        resolved = builder.resolve_deps(resumed_packages)
        logging.info(
            'Dependencies resolved, {} packages in the queue'.format(len(resolved))
        )
        resume_build()
        return
    resume_build()
    return
