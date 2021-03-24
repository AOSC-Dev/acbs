import hashlib
from typing import Tuple, Optional

CHUNKSIZE = 1 * 1024 * 1024


def calculate_hash(chksum_type: str, target_file: str) -> Optional[str]:
    hash_type = chksum_type.lower()
    if hash_type == 'none':
        return None
    if hash_type not in hashlib.algorithms_available:
        raise NotImplementedError(
            'Unsupported hash type %s! Currently supported: %s' % (
                hash_type, ' '.join(sorted(hashlib.algorithms_available))))
    hash_obj = hashlib.new(hash_type)
    with open(target_file, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNKSIZE), b''):
            hash_obj.update(chunk)
    target_hash = hash_obj.hexdigest()
    return target_hash


def hash_url(url: str) -> str:
    hash_obj = hashlib.new('sha256')
    hash_obj.update(url.encode('utf-8'))
    return hash_obj.hexdigest()


def check_hash(chksum_tuple: Tuple[str, str], target_file: str) -> None:
    hash_type, hash_value = chksum_tuple
    hash_type = hash_type.lower()
    hash_value = hash_value.lower()
    target_hash = calculate_hash(hash_type, target_file)
    if hash_value != target_hash:
        raise RuntimeError('Checksums mismatch of type %s at file %s:\nExpected: %s\nActual:   %s' % (
            hash_type, target_file, hash_value, target_hash))
