"""H.264 decoding of the cameras of a dump (PyAV)."""
import av
import cv2


def to_bgr(frame):
    """YUV 4:2:0 -> BGR with OpenCV (about 25x faster than asking PyAV for bgr24 on every frame)."""
    return cv2.cvtColor(frame.to_ndarray(format="yuv420p"), cv2.COLOR_YUV2BGR_I420)


class ChannelDecoder:
    """Streams decoded frames of one camera. Frames before the first key frame cannot be decoded; they are counted
    in ``errors`` and reported, never hidden."""

    def __init__(self, data, recs):
        self.data, self.recs = data, recs
        self.errors = 0

    def frames(self):
        ctx = av.CodecContext.create("h264", "r")
        for local, r in enumerate(self.recs):
            payload = self.data[r.offset:r.offset + r.size]
            try:
                out = ctx.decode(av.Packet(payload))
            except av.error.InvalidDataError:
                self.errors += 1
                continue
            for f in out:
                yield local, to_bgr(f)
        try:
            for f in ctx.decode(None):
                yield len(self.recs) - 1, to_bgr(f)
        except av.error.InvalidDataError:
            self.errors += 1
