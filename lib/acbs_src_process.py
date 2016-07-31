import os
# import sys
import subprocess
import re
import tempfile
import shutil
from lib.acbs_utils import test_progs, group_match


def src_proc_dispatcher(pkg_name, src_tbl_name, src_loc):
    tobj = tempfile.mkdtemp(dir='/var/cache/acbs/build/', prefix='acbs.')
    src_tbl_loc = os.path.join(src_loc, src_tbl_name)
    shadow_ark_loc = os.path.join(tobj, src_tbl_name)
    if os.path.isdir(src_tbl_loc):
        print('[I] Making a copy of the source directory...', end='')
        try:
            shutil.copytree(src=src_tbl_loc, dst=shadow_ark_loc)
        except:
            print('Failed!')
            return False
        print('Done!')
        return True, tobj
    else:
        os.symlink(src_tbl_loc, shadow_ark_loc)
        # print('[D] Source location: {}, Shadow link: {}'.format(src_tbl_loc, shadow_ark_loc))
        return decomp_file(shadow_ark_loc, tobj), tobj


def file_type(file_loc):
    try:
        import magic
    except:
        print('[W] ACBS cannot find libmagic bindings, will use bundled one instead.')
        import lib.magic as magic
    mco = magic.open(magic.MIME_TYPE | magic.MAGIC_SYMLINK)
    mco.load()
    try:
        tp = mco.file(file_loc)
        tp_list = tp.decode('utf-8').split('/')
    except:
        print('[W] Unable to determine the file type!')
        return ['unknown', 'unknown']
    return tp_list


def file_type_full(file_loc):
    try:
        import magic
    except:
        print('[W] ACBS cannot find libmagic bindings, will use bundled one instead.')
        import lib.magic as magic
    mco = magic.open(magic.NONE | magic.MAGIC_SYMLINK)
    mco.load()
    try:
        tp = mco.file(file_loc)
    except:
        print('[W] Unable to determine the file type!')
        return 'data'
    return tp.decode('utf-8')


def decomp_file(file_loc, dest):
    file_type_name = file_type(file_loc)
    ext_list = ['x-tar*', 'zip*', 'x-zip*',
                'x-cpio*', 'x-gzip*', 'x-bzip*', 'x-xz*']
    if (len(file_type_name[0].split('application')) > 1) and group_match(ext_list, file_type_name[1], 1):
        # x-tar*|zip*|x-*zip*|x-cpio*|x-gzip*|x-bzip*|x-xz*
        pass
    else:
        print('[W] ACBS don\'t know how to decompress {} file, will leave it as is!'.format(
            file_type_full(file_loc)))
        return True
    return decomp_lib(file_loc, dest)


def decomp_ext(file_loc, dest):
    if not test_progs(['bsdtar', '-h']):
        print('[E] Unable to use bsdtar. Can\'t decompress files... :-(')
        return False
    try:
        subprocess.check_call(['bsdtar', '-xf', file_loc, '-C', dest])
    except:
        print('[E] Unable to decompress file! File corrupted?! Permission?!')
        return False
    return True


def decomp_lib(file_loc, dest):
    try:
        import libarchive
        import os
    except:
        print('[W] Failed to load libarchive library! Fall back to bsdtar!')
        return decomp_ext(file_loc, dest)
    # Begin
    os.chdir(dest)
    try:
        libarchive.extract.extract_file(file_loc)
    except:
        print('[E] Extraction failure!')
        return False
    return True
