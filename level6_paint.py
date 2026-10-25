import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import product
from pathlib import Path

import level6 as L


class Painter:
    def __init__(self, r, pattern, f):
        self.r = r
        self.lim = r - 1
        self.pattern = pattern
        self.halo = {n for c in pattern for n in L.neighbours(c)
                     if n not in pattern and max(map(abs, n)) <= self.lim}
        self.interior = [(a, b, -a - b) for a in range(-self.lim, self.lim + 1)
                         for b in range(-self.lim, self.lim + 1) if abs(a + b) <= self.lim]
        self.offs = L.line_offsets(r)
        self.f = f
        self.g, self.h = [x for x in range(3) if x != f]
        self.val = [self.offs[k] and next(v for v, o in self.offs[k].items() if o == 0)
                    for k in range(6)]
        self.on = [False] * 6
        self.prog = []
        self.done = set()
        self.dirty_ok = False
        self.dirty = set()
        self.new_dirty, self.new_clean = set(), set()

    def family(self, k):
        return k % 3

    def effect(self, val, on):
        lines = [(self.family(k), val[k]) for k in range(6) if on[k]]
        self.new_dirty, self.new_clean = set(), set()
        if len(lines) < 2:
            return True, set()
        made = set()
        for c in self.interior:
            n = 0
            for f, v in lines:
                if c[f] == v:
                    n += 1
            if n == 2:
                if c in self.halo:
                    if not self.dirty_ok:
                        return False, None
                    self.new_dirty.add(c)
                if c in self.pattern:
                    made.add(c)
            elif n >= 3:
                if c in self.done:
                    return False, None
                if c in self.halo:
                    self.new_clean.add(c)
        return True, made

    def tick(self, ops):
        row = ["-"] * 6
        for k, op in ops.items():
            row[k] = op
            if op == "T":
                self.on[k] = not self.on[k]
            else:
                o = self.offs[k][self.val[k]] + (1 if op == "F" else -1)
                self.val[k] = next(v for v, oo in self.offs[k].items() if oo == o)
        self.prog.append(row)

    def step_op(self, k, target):
        o, t = self.offs[k][self.val[k]], self.offs[k][target]
        return None if o == t else ("F" if t > o else "B")

    def targets_for(self, v):
        f, g, h = self.f, self.g, self.h
        holes = [c for c in self.halo if c[f] == v and c not in self.dirty]
        if len(holes) > 4:
            if not self.dirty_ok:
                return []
            holes = sorted(holes, key=lambda c: abs(c[self.g] - self.val[self.g]))[:4]
        out = []
        for fams in product((g, h), repeat=len(holes)):
            if fams.count(g) > 2 or fams.count(h) > 2:
                continue
            for flip_g, flip_h in product((0, 1), repeat=2):
                val = list(self.val)
                on = [False] * 6
                val[f] = val[f + 3] = v
                on[f] = on[f + 3] = True
                slots = {g: [g, g + 3][::(-1 if flip_g else 1)], h: [h, h + 3][::(-1 if flip_h else 1)]}
                for c, fam in zip(holes, fams):
                    k = slots[fam].pop(0)
                    val[k] = c[fam]
                    on[k] = True
                dist = max(abs(self.offs[k][val[k]] - self.offs[k][self.val[k]]) for k in range(6))
                out.append((dist, val, on))
        out.sort(key=lambda t: t[0])
        return out

    def set_family(self, f):
        self.f = f
        self.g, self.h = [x for x in range(3) if x != f]

    def paint_line(self, v, f=None):
        if f is not None:
            self.set_family(f)
        for dist, val, on in self.targets_for(v):
            if dist <= 1 and all(not (val[k] != self.val[k] and on[k] != self.on[k])
                                 for k in range(6)) \
                    and all(self.on[k] or not on[k] or val[k] == self.val[k] for k in range(6)):
                ok, made = self.effect(val, on)
                if ok and made is not None:
                    ops = {}
                    for k in range(6):
                        if val[k] != self.val[k]:
                            ops[k] = self.step_op(k, val[k])
                        elif on[k] != self.on[k]:
                            ops[k] = "T"
                    self.tick(ops)
                    self.done |= made
                    self.dirty = (self.dirty | self.new_dirty) - self.new_clean
                    return True
        for dist, val, on in self.targets_for(v):
            ok, made = self.effect(val, on)
            if not ok:
                continue
            if any(self.on):
                self.tick({k: "T" for k in range(6) if self.on[k]})
            while any(self.val[k] != val[k] for k in range(6)):
                self.tick({k: self.step_op(k, val[k]) for k in range(6) if self.val[k] != val[k]})
            self.tick({k: "T" for k in range(6) if on[k]})
            self.done |= made
            self.dirty = (self.dirty | self.new_dirty) - self.new_clean
            return True
        return False

    def run(self, count, limit):
        rows = sorted({c[self.f] for c in self.pattern})
        for copy in range(count):
            self.done = set()
            order = rows if copy % 2 == 0 else rows[::-1]
            for v in order:
                if not self.paint_line(v):
                    return None
                if len(self.prog) >= limit:
                    return None
                if self.done >= self.pattern:
                    break
        return self.prog


def erase(painter, limit):
    p = painter
    trio = [0, 1, 2]
    while p.dirty:
        cur = tuple(p.val[k] for k in trio)
        lit = all(p.on[k] for k in trio) and not any(p.on[k] for k in (3, 4, 5))
        c = min(p.dirty, key=lambda d: max(abs(d[f] - cur[f]) for f in range(3)))
        val = list(p.val)
        for k in trio:
            val[k] = c[k]
        if lit and max(abs(p.offs[k][val[k]] - p.offs[k][p.val[k]]) for k in trio) <= 1:
            p.tick({k: p.step_op(k, val[k]) for k in trio if val[k] != p.val[k]})
        else:
            if any(p.on):
                p.tick({k: "T" for k in range(6) if p.on[k]})
            while any(p.val[k] != val[k] for k in trio):
                p.tick({k: p.step_op(k, val[k]) for k in trio if p.val[k] != val[k]})
            p.tick({k: "T" for k in trio})
        p.dirty.discard(c)
        if len(p.prog) >= limit:
            return False
    return True


def run_paint_erase(painter, f, count, limit):
    painter.dirty_ok = True
    painter.set_family(f)
    rows = sorted({c[f] for c in painter.pattern})
    for copy in range(count):
        painter.done = set()
        painter.dirty = set()
        for v in (rows if copy % 2 == 0 else rows[::-1]):
            if not painter.paint_line(v, f):
                return None
            if len(painter.prog) >= limit:
                return None
        if not painter.done >= painter.pattern:
            return None
        if not erase(painter, limit):
            return None
    return painter.prog


def run_mixed(painter, count, limit):
    pattern = painter.pattern
    paintable = []
    for f in range(3):
        for v in sorted({c[f] for c in pattern}):
            holes = [c for c in painter.halo if c[f] == v]
            others = [x for x in range(3) if x != f]
            if len(holes) <= 4:
                paintable.append((f, v, {c for c in pattern if c[f] == v}))
    uncovered = set(pattern)
    chosen = []
    while uncovered:
        f, v, cells = max(paintable, key=lambda t: len(t[2] & uncovered))
        if not cells & uncovered:
            return None
        chosen.append((f, v))
        uncovered -= cells
    by_family = {}
    for f, v in chosen:
        by_family.setdefault(f, []).append(v)
    families = sorted(by_family, key=lambda f: -len(by_family[f]))
    order = [(f, v) for f in families for v in sorted(by_family[f])]
    for copy in range(count):
        painter.done = set()
        seq = order if copy % 2 == 0 else order[::-1]
        for f, v in seq:
            if not painter.paint_line(v, f):
                return None
            if len(painter.prog) >= limit:
                return None
            if painter.done >= pattern:
                break
        if not painter.done >= pattern:
            return None
    return painter.prog


def improve(job):
    (r, rows, count), current = job
    grid_cells = {(y, x) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == "M"}
    pattern = {L.to_cube(r, y, x) for y, x in grid_cells}
    best = current
    for f in range(3):
        prog = Painter(r, pattern, f).run(count, len(best))
        if prog is not None and len(prog) < len(best) and L.simulate(r, grid_cells, prog) == count:
            best = prog
    prog = run_mixed(Painter(r, pattern, 0), count, len(best))
    if prog is not None and len(prog) < len(best) and L.simulate(r, grid_cells, prog) == count:
        best = prog
    for f in range(3):
        prog = run_paint_erase(Painter(r, pattern, f), f, count, len(best))
        if prog is not None and len(prog) < len(best) and L.simulate(r, grid_cells, prog) == count:
            best = prog
    return best


def main():
    folder = Path(__file__).parent
    tags = sys.argv[1:] or ["1-small", "2-medium", "3-large", "4-enormous"]
    with ProcessPoolExecutor() as pool:
        for tag in tags:
            inp = folder / f"in_level-6_{tag}.txt"
            out = folder / f"out_level-6_{tag}.txt"
            cases = L.parse(inp.read_text())
            blocks = [b for b in out.read_text().split("\n\n") if b.strip()]
            current = [[ln.split() for ln in b.splitlines()] for b in blocks]
            assert len(current) == len(cases)
            progs = list(pool.map(improve, zip(cases, current), chunksize=1))
            changed = sum(len(p) != len(c) for p, c in zip(progs, current))
            out.write_text("".join("\n".join(" ".join(l) for l in p) + "\n\n" for p in progs),
                           newline="\n")
            print(f"{out.name}: {sum(map(len, current))} -> {sum(map(len, progs))} lines "
                  f"({changed} programs replaced)", flush=True)


if __name__ == "__main__":
    main()
