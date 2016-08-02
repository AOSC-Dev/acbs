import os
# import sys
import subprocess
# import re
import tempfile
import logging
import shutil
from lib.acbs_utils import acbs_utils


def src_proc_dispatcher(pkg_name, src_tbl_name, src_loc):
    tobj = tempfile.mkdtemp(dir='/var/cache/acbs/build/', prefix='acbs.')
    if src_tbl_name is not None:
        src_tbl_loc = os.path.join(src_loc, src_tbl_name)
        shadow_ark_loc = os.path.join(tobj, src_tbl_name)
    else:
        return True, tobj
    if os.path.isdir(src_tbl_loc):
        logging.info('Making a copy of the source directory...')
        try:
            shutil.copytree(src=src_tbl_loc, dst=shadow_ark_loc)
        except:
            print('Failed!')
            return False
        logging.info('Done on making a copy!')
        return True, tobj
    else:
        os.symlink(src_tbl_loc, shadow_ark_loc)
        # print('[D] Source location: {}, Shadow link: {}'.format(src_tbl_loc, shadow_ark_loc))
        return decomp_file(shadow_ark_loc, tobj), tobj


def file_type(file_loc, res_type=1):
    try:
        import magic
    except:
        logging.warning(
            'ACBS cannot find libmagic bindings, will use bundled one instead.')
        import lib.magic as magic
    if res_type == 1:
        mco = magic.open(magic.MIME_TYPE | magic.MAGIC_SYMLINK)
    elif res_type == 2:
        mco = magic.open(magic.NONE | magic.MAGIC_SYMLINK)
    else:
        mco = magic.open(magic.NONE)
    mco.load()
    try:
        tp = mco.file(file_loc)
        if isinstance(tp, str):
            if res_type == 1:
                tp_res = tp.split('/')
            else:
                tp_res = tp
        else:
            # Workaround a bug in certain version of libmagic
            if res_type == 1:
                tp_res = tp.decode('utf-8').strip('b\'\'').split('/')
            else:
                tp_res = tp.decode('utf-8').strip('b\'\'')
    except:
        logging.error('Unable to determine the file type!')
        if res_type == 1:
            return ['unknown', 'unknown']
        else:
            return 'data'
    return tp_res


def decomp_file(file_loc, dest):
    file_type_name = file_type(file_loc)
    ext_list = ['x-tar*', 'zip*', 'x-zip*',
                'x-cpio*', 'x-gzip*', 'x-bzip*', 'x-xz*']
    if (len(file_type_name[0].split('application')) > 1) and acbs_utils.group_match(ext_list, file_type_name[1], 1):
        # x-tar*|zip*|x-*zip*|x-cpio*|x-gzip*|x-bzip*|x-xz*
        pass
    else:
        logging.warning('ACBS don\'t know how to decompress {} file, will leave it as is!'.format(
            file_type(file_loc, 2)))
        return True
    return decomp_lib(file_loc, dest)


def decomp_ext(file_loc, dest):
    if not acbs_utils.test_progs(['bsdtar', '-h']):
        logging.critical('Unable to use bsdtar. Can\'t decompress files... :-(')
        return False
    try:
        subprocess.check_call(['bsdtar', '-xf', file_loc, '-C', dest])
    except:
        logging.error(
            'Unable to decompress file! File corrupted?! Or Permission denied?!')
        return False
    return True


def decomp_lib(file_loc, dest):
    try:
        import libarchive
        import os
    except:
        logging.warning(
            'Failed to load libarchive library! Fall back to bsdtar!')
        return decomp_ext(file_loc, dest)
    # Begin
    os.chdir(dest)
    try:
        libarchive.extract.extract_file(file_loc)
    except:
        logging.error('Extraction failure!')
        return False
    return True
