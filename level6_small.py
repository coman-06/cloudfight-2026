import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import level6 as L

SMALL = 24
TIME_CAP = 25.0
TOP = [(8, 1.0, 16, True), (6, 0.8, 12, False), (8, 0.8, 16, True), (4, 1.0, 16, True)]


def heavy_candidates():
    for la in (60, 150):
        for st in TOP:
            for fw in (None, 0, 1, 2):
                yield (fw,) + st + (None, True, la)
    for seed in range(12):
        for st in TOP[:2]:
            for fw in (None, 0, 1, 2):
                yield (fw,) + st + (seed, True, 60)


def improve(job):
    (r, rows, count), current = job
    cells = {(y, x) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == "M"}
    if len(cells) > SMALL:
        return current
    cube = {L.to_cube(r, y, x) for y, x in cells}
    best = current
    start = time.time()
    for args in heavy_candidates():
        if time.time() - start > TIME_CAP:
            break
        prog = L.build_cross(r, cube, count, *args)
        if len(prog) < len(best) and L.simulate(r, cells, prog) == count:
            best = prog
    return best


def main():
    folder = Path(__file__).parent
    tags = sys.argv[1:] or ["1-small", "2-medium", "3-large"]
    with ProcessPoolExecutor() as pool:
        for tag in tags:
            inp = folder / f"in_level-6_{tag}.txt"
            out = folder / f"out_level-6_{tag}.txt"
            cases = L.parse(inp.read_text())
            blocks = [b for b in out.read_text().split("\n\n") if b.strip()]
            current = [[ln.split() for ln in b.splitlines()] for b in blocks]
            assert len(current) == len(cases)
            progs = list(pool.map(improve, zip(cases, current), chunksize=1))
            before = sum(map(len, current))
            after = sum(map(len, progs))
            out.write_text("".join("\n".join(" ".join(l) for l in p) + "\n\n" for p in progs),
                           newline="\n")
            print(f"{out.name}: {before} -> {after} lines", flush=True)


if __name__ == "__main__":
    main()
