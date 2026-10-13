# The "luo" multi-camera `.dat` layout

Everything is little-endian unless noted. Documented from the sample in this repository; FFmpeg's `libavformat/luodatdec.c` implements the same layout.

| Where | Size | Meaning |
|---|---|---|
| `0x0000` | 4 | `"luo "` |
| `0x1ffc` | 8 | `" oulliu "` |
| `0x207c` | 4 | `" uil"` |
| `0x2000` | … | records |

A record is a 128-byte header followed by the payload.

| Offset | Size | Meaning |
|---|---|---|
| `+0x00` | 4 | `"liu "` |
| `+0x04` | 4 | stream id — one per camera, random-looking 32-bit numbers |
| `+0x08` | 4 | width |
| `+0x0c` | 4 | height |
| `+0x10` | 4 | fps (nominal) |
| `+0x14` | 16 | unknown |
| `+0x24` | 4 | key flag, 1 = key frame |
| `+0x28` | 4 | unknown |
| `+0x2c` | 4 | frame index of this stream |
| `+0x30` | 4 | unknown |
| `+0x34` | 8 | pts, units of 1/fps, a per-camera clock |
| `+0x3c` | 4 | payload size |
| `+0x40` | 64 | unknown |
| `+0x80` | size | payload: one H.264 access unit, Annex B |

Observations on the sample (16 cameras, 352×288, 16 fps, 2107 records):

- Records of one camera come in bursts of about a dozen frames, then the next camera, and so on round the 16 cameras.
- Stream ids are not ordered; this project numbers cameras `CH01…` by first appearance in the file.
- The first `pts` of the 16 cameras span 179 ticks = 11.2 s, while the on-screen clocks of all cameras show the same second.
- Key frames come about every 32 frames (2 s); a camera whose first record is not a key frame cannot be decoded until its first key frame.
