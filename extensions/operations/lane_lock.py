"""Small OS-backed nonblocking maintenance lock; no third-party dependency."""
import os


class Timeout(Exception):
    pass


class FileLock:
    def __init__(self, path):
        self.path = path
        self.handle = None

    def acquire(self, timeout=0):
        if timeout != 0:
            raise ValueError('Only nonblocking maintenance locks are supported')
        handle = open(self.path, 'a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if os.fstat(handle.fileno()).st_size == 0:
                    handle.write(b'0'); handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise Timeout() from exc
        self.handle = handle
        return self

    def release(self):
        if self.handle:
            if os.name == 'nt':
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()
            self.handle = None
