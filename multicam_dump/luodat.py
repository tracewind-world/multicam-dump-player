"""Reader for the "luo" multi-channel recorder dump (``*.dat``).

Layout (little-endian), as also implemented by FFmpeg's ``luodat`` demuxer:

    0x0000  b"luo "                      file magic
    0x1ffc  b" oulliu "                  magic, 8 bytes
    0x207c  b" uil"                      magic, 4 bytes
    0x2000  records, back to back

    record  = 128-byte header + payload
      +0x00  b"liu "                     record magic
      +0x04  u32  stream id              random-looking 32-bit id, one per camera
      +0x08  u32  width
      +0x0c  u32  height
      +0x10  u32  fps                    nominal frame rate
      +0x14  16 bytes                    unknown
      +0x24  u32  key                    1 = key frame
      +0x28  4 bytes                     unknown
      +0x2c  u32  frame index            per stream
      +0x30  4 bytes                     unknown
      +0x34  u64  pts                    unit = 1/fps, per-camera clock
      +0x3c  u32  payload size
      +0x40  64 bytes                    unknown
    payload = one H.264 access unit, Annex B

Every camera is a separate H.264 stream; records of different cameras are interleaved in bursts.
"""
import struct
from dataclasses import dataclass

MAGIC_FILE = b"luo "
RECORD_MAGIC = b"liu "
DATA_START = 0x2000
HEADER_SIZE = 128


class NotLuoDat(ValueError):
    pass


@dataclass(frozen=True)
class Record:
    order: int          # position among all records in the file
    offset: int         # file offset of the payload
    stream_id: int
    width: int
    height: int
    fps: int
    key: bool
    index: int          # per-stream frame counter written by the recorder
    pts: int
    size: int


def check_magic(buf):
    if len(buf) < 0x2080 or buf[:4] != MAGIC_FILE or buf[0x1FFC:0x2004] != b" oulliu " or buf[0x207C:0x2080] != b" uil":
        raise NotLuoDat("not a luo .dat recorder dump")


def read_records(data):
    """Parse every complete record of a dump held in memory. Returns (records, notes).

    Parsing never skips silently: bytes that do not start a valid record are reported in ``notes``
    (and the scan resumes at the next record magic).
    """
    check_magic(data)
    records, notes = [], []
    pos, n = DATA_START, len(data)
    while pos + HEADER_SIZE <= n:
        if data[pos:pos + 4] != RECORD_MAGIC:
            nxt = data.find(RECORD_MAGIC, pos + 1)
            notes.append("%d bytes at 0x%x are not a record" % ((nxt if nxt >= 0 else n) - pos, pos))
            if nxt < 0:
                break
            pos = nxt
            continue
        sid, w, h, fps = struct.unpack_from("<4I", data, pos + 4)
        key, = struct.unpack_from("<I", data, pos + 0x24)
        idx, = struct.unpack_from("<I", data, pos + 0x2C)
        pts, = struct.unpack_from("<Q", data, pos + 0x34)
        size, = struct.unpack_from("<I", data, pos + 0x3C)
        if size == 0:
            notes.append("zero-length record at 0x%x: end of the data (a dump cut out of a longer recording ends like this)" % pos)
            break
        end = pos + HEADER_SIZE + size
        if end > n:
            notes.append("record at 0x%x is cut off by the end of the file (%d of %d payload bytes)" % (pos, n - pos - HEADER_SIZE, size))
            break
        records.append(Record(len(records), pos + HEADER_SIZE, sid, w, h, fps, key == 1, idx, pts, size))
        pos = end
    return records, notes


def channels(records):
    """Group records by camera, cameras numbered CH1.. by first appearance in the file."""
    order, groups = [], {}
    for r in records:
        if r.stream_id not in groups:
            groups[r.stream_id] = []
            order.append(r.stream_id)
        groups[r.stream_id].append(r)
    return [(i + 1, sid, groups[sid]) for i, sid in enumerate(order)]
