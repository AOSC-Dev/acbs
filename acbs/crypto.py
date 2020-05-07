import hashlib
from typing import Tuple, Optional


def check_hash_hashlib(chksum_tuple: Tuple[str, str], target_file: str) -> None:
    hash_type, hash_value = chksum_tuple
    hash_type = hash_type.lower()
    hash_value = hash_value.lower()
    if hash_type not in hashlib.algorithms_available:
        raise NotImplementedError(
            'Unsupported hash type %s! Currently supported: %s' % (
                hash_type, ' '.join(sorted(hashlib.algorithms_available))))
    hash_obj = hashlib.new(hash_type)
    with open(target_file, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    target_hash = hash_obj.hexdigest()
    if hash_value != target_hash:
        raise RuntimeError('Checksums mismatch of type %s at file %s:\nExpected: %s\nActual:   %s' % (
            hash_type, target_file, hash_value, target_hash))
