from contextlib import contextmanager
import os
from pathlib import Path
import uuid

from . import contracts as c


def publish(path, raw):
    path = c.checked_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    before = c.identity(path.parent)
    temp = path.parent / ('.partial-' + uuid.uuid4().hex)
    with temp.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    c.require(temp.read_bytes() == raw and c.identity(path.parent) == before, 'publish_preflight')
    c.checked_path(path)
    try:
        os.link(temp, path)
    except FileExistsError as exc:
        raise c.ContractError('publish_no_overwrite') from exc
    c.require(c.identity(path.parent) == before, 'publish_parent_changed')
    temp.unlink()


@contextmanager
def writer_lock(root):
    root = c.checked_path(root, directory=True)
    root_identity = c.identity(root)
    path = c.checked_path(root / '.writer.lock')
    with path.open('a+b') as handle:
        c.require(os.fstat(handle.fileno()).st_nlink == 1 and
                  [os.fstat(handle.fileno()).st_dev, os.fstat(handle.fileno()).st_ino] == c.identity(path),
                  'writer_lock_identity')
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise c.ContractError('writer_busy') from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise c.ContractError('writer_busy') from exc
        try:
            c.require(c.identity(root) == root_identity, 'writer_root_changed')
            yield
            c.require(c.identity(root) == root_identity, 'writer_root_changed')
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Store:
    def __init__(self, root):
        self.root = c.checked_path(root, directory=True)
        self.root_identity = c.identity(self.root)

    def check(self):
        c.require(c.identity(self.root) == self.root_identity, 'store_identity_changed')

    def put(self, raw):
        self.check()
        c.require(type(raw) is bytes and len(raw) <= c.PROFILE['limits']['max_object_bytes'], 'object_bounds')
        sha = c.digest(raw)
        path = self.root / 'objects' / (sha + '.bin')
        if path.exists():
            c.require(self.get(sha) == raw, 'object_collision')
        else:
            publish(path, raw)
        return sha

    def get(self, sha):
        self.check()
        c.require(type(sha) is str and len(sha) == 64 and all(ch in '0123456789abcdef' for ch in sha), 'object_id')
        raw = c.read_regular(self.root / 'objects' / (sha + '.bin'), c.PROFILE['limits']['max_object_bytes'])
        c.require(c.digest(raw) == sha, 'object_hash')
        return raw

    def json(self, sha):
        return c.loads(self.get(sha))
