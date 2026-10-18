from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

_password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

# Dummy hash cố định để chống timing attack: verify tốn thời gian như thật dù user không tồn tại.
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Trả (verified, new_hash). new_hash khác None nếu cần re-hash (vd nâng cấp từ bcrypt lên argon2)."""
    return _password_hash.verify_and_update(plain_password, hashed_password)
