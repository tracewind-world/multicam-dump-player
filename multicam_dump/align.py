"""Putting the cameras of one dump on a common time line.

Why not use the container timestamps?  In the sample every camera has its own clock: the first pts of the 16 cameras
are up to ~11 s apart, yet the cameras were recording at the same time (the picture clocks and the order of the records in
the file both say so). Laying the cells out by pts leaves most of the grid dark for the first seconds.

What the file *does* tell us is the order in which records were written. Cameras are written in bursts (a dozen
frames of one camera, then the next camera ...). The camera with the most records is used as the reference clock:
its k-th record, at file position p_k, happened at k / fps. Every burst of another camera is placed at the reference time
interpolated at the start of that burst, and inside the burst frames follow the camera's own frame counter.
Each camera gets one constant offset (the median over its bursts), so its frames stay evenly spaced.
"""
import statistics


def split_bursts(recs):
    """Runs of consecutive file positions for one camera: [(first_order, first_local_index, count)]."""
    out, start = [], 0
    for i in range(1, len(recs) + 1):
        if i == len(recs) or recs[i].order != recs[i - 1].order + 1:
            out.append((recs[start].order, start, i - start))
            start = i
    return out


def interp(xs, ys, x):
    """Piecewise-linear, clamped, xs ascending."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    f = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + f * (ys[hi] - ys[lo])


def channel_offsets(chans, fps):
    """chans = [(number, stream_id, [records])]. Returns {number: offset_seconds}; time of local frame j = offset + j / fps."""
    ref = max(chans, key=lambda c: len(c[2]))
    xs = [r.order for r in ref[2]]
    ys = [k / fps for k in range(len(xs))]
    offsets = {}
    for num, _sid, recs in chans:
        if num == ref[0]:
            offsets[num] = 0.0
            continue
        obs = [interp(xs, ys, first_order) - local / fps for first_order, local, _n in split_bursts(recs)]
        offsets[num] = statistics.median(obs)
    return offsets, ref[0]
