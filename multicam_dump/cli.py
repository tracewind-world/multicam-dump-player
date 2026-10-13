import argparse
import os
import sys
import time

from . import __version__
from .grid import Dump, export_grid
from .luodat import NotLuoDat


def cmd_info(a):
    d = Dump(a.file)
    lo, hi = d.timeline()
    print("%s: %d cameras, %d records, %dx%d @ %d fps, grid %dx%d" % (os.path.basename(a.file), len(d.chans), len(d.records), d.width, d.height, d.fps, d.cols, d.rows))
    print("common timeline %.2f s .. %.2f s  (%.1f s); reference camera CH%02d" % (lo, hi, hi - lo, d.ref))
    for num, sid, recs in d.chans:
        keys = sum(1 for r in recs if r.key)
        print("  CH%02d  id %-10d  %4d frames  %3d key  container pts %d..%d  offset %+6.2f s" % (num, sid, len(recs), keys, recs[0].pts, recs[-1].pts, d.offsets[num]))
    for n in d.notes:
        print("note:", n)


def cmd_export(a):
    d = Dump(a.file)
    t0 = time.time()
    n = export_grid(d, a.output, a.start, a.end, not a.no_labels)
    print("wrote %s: %d frames in %.1f s" % (a.output, n, time.time() - t0))
    bad = {k: v for k, v in getattr(d, "decode_errors", {}).items() if v}
    if bad:
        print("undecodable packets (usually before a camera's first key frame):", bad)


def cmd_split(a):
    d = Dump(a.file)
    os.makedirs(a.dir, exist_ok=True)
    for num, sid, recs in d.chans:
        p = os.path.join(a.dir, "ch%02d.h264" % num)
        with open(p, "wb") as f:
            for r in recs:
                f.write(d.data[r.offset:r.offset + r.size])
        print("wrote", p, "(%d frames)" % len(recs))
    print("each file is a raw H.264 stream at %d fps; e.g.  ffmpeg -f h264 -framerate %d -i ch01.h264 -c copy ch01.mp4" % (d.fps, d.fps))


def cmd_play(a):
    import cv2
    d = Dump(a.file)
    period = 1.0 / d.fps
    paused = False
    for t, img in d.grid_frames(a.start, a.end):
        cv2.imshow("multicam-dump-player", img)
        t_next = time.time() + period
        while True:
            key = cv2.waitKey(1 if not paused else 50) & 0xFF
            if key in (ord("q"), 27):
                cv2.destroyAllWindows()
                return
            if key == ord(" "):
                paused = not paused
            if not paused and time.time() >= t_next:
                break
            if paused and key == ord("n"):
                break
    cv2.destroyAllWindows()


def main(argv=None):
    p = argparse.ArgumentParser(prog="mcdump", description="Open recorder dumps that interleave many cameras in one file.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info", help="list the cameras in a dump"); s.add_argument("file"); s.set_defaults(fn=cmd_info)
    s = sub.add_parser("export", help="write the grid as an MP4")
    s.add_argument("file"); s.add_argument("-o", "--output", default="grid.mp4")
    s.add_argument("--start", type=float); s.add_argument("--end", type=float); s.add_argument("--no-labels", action="store_true")
    s.set_defaults(fn=cmd_export)
    s = sub.add_parser("split", help="write each camera as a raw .h264 file")
    s.add_argument("file"); s.add_argument("-d", "--dir", default="channels"); s.set_defaults(fn=cmd_split)
    s = sub.add_parser("play", help="play the grid (needs opencv-python with GUI; space pauses, n steps, q quits)")
    s.add_argument("file"); s.add_argument("--start", type=float); s.add_argument("--end", type=float); s.set_defaults(fn=cmd_play)
    a = p.parse_args(argv)
    try:
        a.fn(a)
    except NotLuoDat as e:
        sys.exit("error: %s: %s" % (a.file, e))


if __name__ == "__main__":
    main()
