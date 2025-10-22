# -*- coding: utf-8 -*-
import typing
from   typing import *

###
# Standard imports, starting with os and sys
###
min_py = (3, 9)
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###
import errno
import fcntl
import mmap
import struct
import tempfile

###
# Credits
###
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2024, University of Richmond'
__credits__ = None
__version__ = 0.1
__maintainer__ = 'George Flanagin'
__email__ = 'gflanagin@richmond.edu'
__status__ = 'in progress'
__license__ = 'MIT'


def get_logical_block_size(dir:str=None) -> int:
    """
    Given that any program may be using several different file
    systems on various mounts, it is wise to look. The program
    opens a nameless, temporary file r/w, and then gets the
    block size. If that fails (why would it? I don't know),
    try getting the answer from statvfs, and if that fails,
    use the value in sysconf. The temporary file will always
    be deleted.

    dir -- a directory (any directory) on the file system of interest.

    returns -- the block size, expressed in bytes.
    """
    BLKSSZGET = 0x1268

    path = dir if dir else os.getcwd()

    try:
        f=tempfile.TemporaryFile(dir=path)
        buf = fcntl.ioctl(f.fileno(), BLKSSZGET, b"    ")
        return struct.unpack("I", buf)[0]

    except Exception:
        try:
            st = os.statvfs(path)
            return st.f_bsize or os.sysconf("SC_PAGESIZE")

        except Exception:
            return os.sysconf("SC_PAGESIZE")

    finally:
        f.close()


def fdirect_open(path:str) -> int:
    """
    Low-level open on a filename.
    """
    try:
        flags = os.O_RDONLY
        flags |= os.O_DIRECT if direct and hasattr(os, "O_DIRECT") else 0
        return os.open(path, flags)

    except:
        return -1


def fdirect_read(fd:int, offset:int, size:int,
    direct:bool=True, bs:int=os.sysconf("SC_PAGESIZE")) -> bytes:
    """
    Use low-level OS primitives to read a file by blocks. Attempts
    to bypass the usual file system buffering.

    fd -- a file handle created with fdirect_open.
    offset -- where to read. positive numbers are construed to be
        offsets from the beginning, and negative numbers are
        construed to be from the end.
    size -- how much to read.
    direct -- whether to attempt to use a direct read. The failover
        is the usual buffered read. If you happen to "know" that
        you are reading on a file system that cannot be directly
        read (NFS, for example), pass in direct=False

    Returns bytes of length 'size'.
    """

    page = mmap.PAGESIZE  # typically 4096; helps ensure mmap alignment

    # Align the read window to block size
    align_off  = (offset // bs) * bs
    align_diff = offset - align_off
    read_size  = ((align_diff + size + bs - 1) // bs) * bs  # ceil to multiple of bs

    try:
        # If we're in O_DIRECT, the buffer and size must be aligned to both block and page.
        # mmap gives a page-aligned buffer; we also ensure length is a multiple of bs.
        # Use preadv to fill our buffer in-place.
        def _direct_preadv():
            # Ensure length also multiple of page (usually already true if bs == page).
            aligned_len = ((read_size + page - 1) // page) * page
            buf = mmap.mmap(-1, aligned_len, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
            mv = memoryview(buf)[:read_size]  # only the needed bytes
            n = os.preadv(fd, [mv], align_off)
            if n < read_size:
                # Short read (e.g., near EOF) is fine; trim to what we got but keep slice later
                mv = mv[:n]
            # Return requested slice
            out = bytes(mv[align_diff:align_diff + size])
            buf.close()
            return out

        def _buffered_pread():
            data = os.pread(fd, read_size, align_off)  # kernel page cache path
            return data[align_diff:align_diff + size]

        if flags & getattr(os, "O_DIRECT", 0):
            try:
                return _direct_preadv()
            except OSError as e:
                # Typical O_DIRECT failures: EINVAL (misaligned), EOPNOTSUPP, etc.
                # Fall back to buffered read transparently.
                if e.errno not in (errno.EINVAL, errno.EOPNOTSUPP, errno.ENOTTY, errno.EBADF):
                    raise
                return _buffered_pread()

        else:
            return _buffered_pread()

    finally:
        os.close(fd)

# --- Example usage ---
if __name__ == "__main__":
    path = "/dev/sda"          # or a large regular file
    off  = 4096 * 1234         # try a misaligned value to see alignment logic work
    n    = 128 * 1024          # 128 KiB
    data = aligned_read(path, off, n, direct=True)
    print(f"Read {len(data)} bytes (requested {n})")


