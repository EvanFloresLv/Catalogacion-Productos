# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID


def uuid_to_bytes(u: UUID) -> bytes:
    return u.bytes


def bytes_to_uuid(b: bytes) -> UUID:
    return UUID(bytes=b)