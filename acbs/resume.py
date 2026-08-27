import logging
import pickle

from acbs import __version__
from acbs.base import ACBSPackageInfo, ACBSShrinkWrap
from acbs.checkpoint import checkpoint_dpkg, checkpoint_spec, checkpoint_to_group
from acbs.const import TMP_DIR
from acbs.find import find_package
from acbs.main import BuildCore
from acbs.pm import check_if_installed
from acbs.utils import make_build_dir, print_build_timings, print_package_names

logger = logging.getLogger(__name__)

def reassign_build_dir(packages: list[ACBSPackageInfo]):
    groups: dict[str, str] = {}
    for package in packages:
        if package.base_slug:
            directory = groups.get(package.base_slug)
            if not directory:
                directory = make_build_dir(TMP_DIR)
                groups[package.base_slug] = directory
            package.build_location = directory
            continue
        package.build_location = ''


def check_dpkg_state(state: ACBSShrinkWrap, packages: list[ACBSPackageInfo]) -> bool:
    if checkpoint_dpkg() == state.dpkg_state:
        return True
    logger.warning('DPKG state change detected. Re-checking dependencies...')
    for package in packages:
        if not check_if_installed(package.name):
            return False
    return True


def do_load_checkpoint(name: str) -> ACBSShrinkWrap:
    with open(name, 'rb') as f:
        return pickle.load(f)


def do_resume_checkpoint(filename: str, args):
    def resume_build():
        logger.debug(f'Queue: {resumed_packages}')
        logger.info(f'Packages to be resumed: {print_package_names(resumed_packages, 5)}')
        build_timings = state.timings.copy()
        try:
            builder.build_sequential(build_timings, resumed_packages)
        except Exception:
            # failed again?
            logger.exception("Failed to resume build")
            builder.save_checkpoint(build_timings, resumed_packages)
        print_build_timings(build_timings, [])

    state = do_load_checkpoint(filename)
    builder = BuildCore(args)
    stage2 = builder.stage2
    logger.info(f'Resuming from {filename}')
    if state.version != __version__:
        logger.warning(
            'The state was check-pointed with a different version of acbs!')
        logger.warning('Undefined behavior might occur!')
    if state.no_deps:
        leftover = state.packages[state.cursor-1:]
        logger.warning('Resuming without dependency resolution.')
        logger.info(f'Resumed. {len(leftover)} packages to go.')
        builder.build_sequential(state.timings, leftover)
        return
    logger.info('Validating status...')
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
        new_cursor = min(new_cursor, index)
        resumed_packages.extend(find_package(p.name, builder.tree_dir, '+stage2' if stage2 else ''))
        # index doesn't matter now, since changes have been detected
    if not check_dpkg_state(state, resumed_packages[:new_cursor]):
        name = checkpoint_to_group(
            resumed_packages[new_cursor:], builder.tree_dir)
        raise RuntimeError(
            f'DPKG state mismatch. Unable to resume.\nACBS has created a new temporary group {name} for you to continue.')
    resumed_packages = resumed_packages[new_cursor:]
    # clear the build directory of the first package
    reassign_build_dir(resumed_packages)
    if new_cursor != (state.cursor - 1):
        logger.warning(
            'Scenario mismatch detected! Dependency resolution will be re-attempted.')
        resolved = builder.resolve_deps(resumed_packages, stage2)
        logger.info(
            f'Dependencies resolved, {len(resolved)} packages in the queue')
        resume_build()
        return
    resume_build()
    return
