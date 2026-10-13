import os
import unittest

from multicam_dump.align import channel_offsets, interp, split_bursts
from multicam_dump.grid import Dump
from multicam_dump.luodat import NotLuoDat, check_magic, read_records, channels

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "file0000.dat")


class Parse(unittest.TestCase):
    def setUp(self):
        self.data = open(SAMPLE, "rb").read()

    def test_sixteen_cameras(self):
        recs, notes = read_records(self.data)
        ch = channels(recs)
        self.assertEqual(len(ch), 16)
        self.assertEqual(len(recs), 2107)
        self.assertTrue(all(r.width == 352 and r.height == 288 and r.fps == 16 for r in recs))
        self.assertEqual(len(notes), 1)        # the zero-length tail

    def test_not_a_dump(self):
        with self.assertRaises(NotLuoDat):
            check_magic(b"\x00" * 0x3000)

    def test_container_clocks_disagree_but_alignment_agrees(self):
        recs, _ = read_records(self.data)
        ch = channels(recs)
        starts = [c[2][0].pts for c in ch]
        self.assertGreater(max(starts) - min(starts), 100)      # ~11 s apart at 16 ticks/s: the pts cannot be used
        offsets, ref = channel_offsets(ch, 16)
        self.assertLess(max(offsets.values()) - min(offsets.values()), 1.0)   # the cameras were recording together


class Align(unittest.TestCase):
    def test_interp(self):
        self.assertEqual(interp([0, 10], [0, 1], 5), 0.5)
        self.assertEqual(interp([0, 10], [0, 1], -3), 0)
        self.assertEqual(interp([0, 10], [0, 1], 99), 1)


class Grid(unittest.TestCase):
    def test_first_grid_frame_has_cells(self):
        d = Dump(SAMPLE)
        self.assertEqual((d.cols, d.rows), (4, 4))
        t, img = next(d.grid_frames(start=4.0, end=4.2))
        self.assertEqual(img.shape, (4 * 288, 4 * 352, 3))
        lit = 0
        for r in range(4):
            for c in range(4):
                cell = img[r * 288 + 30:(r + 1) * 288, c * 352:(c + 1) * 352]     # below the CH label
                lit += int(cell.mean() > 5)
        self.assertEqual(lit, 16)


if __name__ == "__main__":
    unittest.main()
