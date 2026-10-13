# Putting 16 cameras on one clock

## What does not work: container timestamps

Every camera carries its own `pts`. In the sample the first values are 1310180 … 1310359 (units of 1/16 s), i.e. the cameras seem to start up to 11 s apart.
Placing frames by `pts` gives a grid in which, for the first seconds, only a few cells have a picture, and the picture clocks of different cells disagree.
The on-screen clocks and the interleaving of the records both show that the cameras were recording together; the `pts` are per-camera counters, not a shared time.

## What works: the order of the records

The recorder writes the cameras in bursts. Take the camera with the most records as the reference clock: its k-th record is at file position `p_k` and happened at `k / fps`.

1. Map any file position to reference time by linear interpolation over `(p_k, k / fps)`.
2. For another camera, split its records into bursts (runs of consecutive file positions).
3. For each burst, offset = reference time at the burst's first record − (index of that record in the camera) / fps.
4. The camera's constant offset is the median of its burst offsets; frame `j` is at `offset + j / fps`.

Because the offset is one constant per camera, frames stay evenly spaced, and the median ignores bursts that were flushed late.
On the sample the 16 offsets lie within 0.17 s of each other and the on-screen clocks of all 16 cells agree.

The estimate is only as fine as the write bursts (a fraction of a second). It is not a timecode; if the recorder wrote one, use it.
