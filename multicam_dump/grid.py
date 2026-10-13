"""Compose the cameras into one grid and write or show it."""
import math

import av
import cv2
import numpy as np

from .align import channel_offsets
from .decode import ChannelDecoder
from .luodat import channels as group_channels, read_records


class Dump:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        self.records, self.notes = read_records(self.data)
        self.chans = group_channels(self.records)
        if not self.chans:
            raise ValueError("no camera records found")
        first = self.records[0]
        self.fps = first.fps or 16
        self.width, self.height = first.width, first.height
        self.offsets, self.ref = channel_offsets(self.chans, self.fps)

    @property
    def cols(self):
        return math.ceil(math.sqrt(len(self.chans)))

    @property
    def rows(self):
        return math.ceil(len(self.chans) / self.cols)

    def timeline(self):
        """(t_start, t_end) over all cameras, seconds on the common clock."""
        lo = min(self.offsets[n] for n, _s, _r in self.chans)
        hi = max(self.offsets[n] + len(r) / self.fps for n, _s, r in self.chans)
        return lo, hi

    def grid_frames(self, start=None, end=None, labels=True):
        """Yield (t, grid image BGR) at the nominal fps. A cell shows the newest frame of its camera at or before t;
        black until that camera has produced a decodable frame."""
        t0, t1 = self.timeline()
        t0 = t0 if start is None else start
        t1 = t1 if end is None else end
        W, H = self.width, self.height
        decs = []
        for num, sid, recs in self.chans:
            d = ChannelDecoder(self.data, recs)
            decs.append({"num": num, "dec": d, "it": d.frames(), "cur": None, "next": None, "off": self.offsets[num], "done": False})

        def advance(c, t):
            while not c["done"]:
                if c["next"] is None:
                    try:
                        local, img = next(c["it"])
                    except StopIteration:
                        c["done"] = True
                        break
                    c["next"] = (c["off"] + local / self.fps, img)
                if c["next"][0] <= t + 1e-9:
                    c["cur"], c["next"] = c["next"][1], None
                else:
                    break

        n = int(round((t1 - t0) * self.fps))
        for k in range(n):
            t = t0 + k / self.fps
            canvas = np.zeros((self.rows * H, self.cols * W, 3), np.uint8)
            for i, c in enumerate(decs):
                advance(c, t)
                if c["cur"] is not None:
                    r, col = divmod(i, self.cols)
                    canvas[r * H:(r + 1) * H, col * W:(col + 1) * W] = c["cur"][:H, :W]
                if labels:
                    r, col = divmod(i, self.cols)
                    cv2.putText(canvas, "CH%02d" % c["num"], (col * W + 6, r * H + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
            yield t, canvas
        self.decode_errors = {c["num"]: c["dec"].errors for c in decs}


def export_grid(dump, out_path, start=None, end=None, labels=True):
    first, count = True, 0
    container = av.open(out_path, "w")
    stream = None
    for _t, img in dump.grid_frames(start, end, labels):
        if first:
            stream = container.add_stream("libx264", rate=dump.fps)
            stream.width, stream.height, stream.pix_fmt = img.shape[1], img.shape[0], "yuv420p"
            stream.options = {"crf": "20", "preset": "veryfast"}
            stream.codec_context.thread_type = "FRAME"   # ~4x faster than the slice-threading default
            first = False
        frame = av.VideoFrame.from_ndarray(img, format="bgr24")
        for pkt in stream.encode(frame):
            container.mux(pkt)
        count += 1
    if stream is not None:
        for pkt in stream.encode():
            container.mux(pkt)
    container.close()
    return count
