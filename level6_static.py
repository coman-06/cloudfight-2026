import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations, product
from pathlib import Path

import level6 as L

MAX_CELLS = 12


def static_program(case, current_len):
    r, rows, count = case
    grid_cells = {(y, x) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == "M"}
    pattern = {L.to_cube(r, y, x) for y, x in grid_cells}
    if len(pattern) > MAX_CELLS:
        return None
    lim = r - 1
    halo = {n for c in pattern for n in L.neighbours(c)
            if n not in pattern and max(map(abs, n)) <= lim}
    offs = L.line_offsets(r)
    vals = [sorted({c[f] for c in pattern}) for f in range(3)]
    choices = []
    for f in range(3):
        opts = [()] + [(v,) for v in vals[f]] + list(combinations(vals[f], 2))
        choices.append(opts)

    best = None
    for A, B, C in product(*choices):
        sets = (set(A), set(B), set(C))
        if any(sum(c[f] in sets[f] for f in range(3)) < 2 for c in pattern):
            continue
        lines = [(0, v) for v in A] + [(1, v) for v in B] + [(2, v) for v in C]
        n = len(lines)
        assign = {}
        travel = 0
        for f, group in ((0, A), (1, B), (2, C)):
            if not group:
                continue
            if len(group) == 1:
                e = min((f, f + 3), key=lambda k: abs(offs[k][group[0]]))
                assign[(f, group[0])] = e
                travel = max(travel, abs(offs[e][group[0]]))
            else:
                o1 = max(abs(offs[f][group[0]]), abs(offs[f + 3][group[1]]))
                o2 = max(abs(offs[f][group[1]]), abs(offs[f + 3][group[0]]))
                if o1 <= o2:
                    assign[(f, group[0])], assign[(f, group[1])] = f, f + 3
                else:
                    assign[(f, group[1])], assign[(f, group[0])] = f, f + 3
                travel = max(travel, min(o1, o2))
        if best is not None and travel + count >= best[0]:
            continue
        if travel + count >= current_len:
            continue
        effects = []
        for mask in range(1, 1 << n):
            on = [lines[i] for i in range(n) if mask >> i & 1]
            made, killed, ok = set(), set(), True
            seen = set()
            for (f1, v1), (f2, v2) in combinations(on, 2):
                if f1 == f2:
                    continue
                c = [0, 0, 0]
                c[f1], c[f2] = v1, v2
                c[3 - f1 - f2] = -v1 - v2
                c = tuple(c)
                if c in seen or max(map(abs, c)) > lim:
                    continue
                seen.add(c)
                k = sum(1 for f, v in on if c[f] == v)
                if k == 2:
                    if c in halo:
                        ok = False
                        break
                    if c in pattern:
                        made.add(c)
                elif c in pattern:
                    killed.add(c)
            if ok and made:
                effects.append((mask, frozenset(made), frozenset(killed)))
        seq = None
        for e in effects:
            if e[1] >= pattern:
                seq = [e]
                break
        if seq is None:
            useful = sorted(effects, key=lambda e: -len(e[1]))[:40]
            for e1, e2 in product(useful, repeat=2):
                if (e1[1] | e2[1]) >= pattern and not (e2[2] & (e1[1] - e2[1])):
                    seq = [e1, e2]
                    break
        if seq is None:
            useful = sorted(effects, key=lambda e: -len(e[1]))[:20]
            for e1, e2, e3 in product(useful, repeat=3):
                if (e1[1] | e2[1] | e3[1]) >= pattern \
                        and not (e2[2] & (e1[1] - e2[1])) \
                        and not (e3[2] & ((e1[1] | e2[1]) - e3[1])):
                    seq = [e1, e2, e3]
                    break
        if seq is None:
            continue
        cost = travel + count * len(seq)
        if cost >= current_len or (best is not None and cost >= best[0]):
            continue
        pos = [0] * 6
        target = {assign[ln]: offs[assign[ln]][ln[1]] for ln in lines}
        prog = []
        for _ in range(travel):
            row = ["-"] * 6
            for e, o in target.items():
                if pos[e] < o:
                    row[e] = "F"
                    pos[e] += 1
                elif pos[e] > o:
                    row[e] = "B"
                    pos[e] -= 1
            prog.append(row)
        state = [False] * 6
        for _ in range(count):
            for mask, _, _ in seq:
                want = [False] * 6
                for i in range(n):
                    if mask >> i & 1:
                        want[assign[lines[i]]] = True
                prog.append(["T" if want[e] != state[e] else "-" for e in range(6)])
                state = want
        if L.simulate(r, grid_cells, prog) == count:
            best = (len(prog), prog)
    return best[1] if best else None


def improve(job):
    case, current = job
    prog = static_program(case, len(current))
    return prog if prog is not None and len(prog) < len(current) else current


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
            out.write_text("".join("\n".join(" ".join(l) for l in p) + "\n\n" for p in progs),
                           newline="\n")
            changed = sum(p is not c for p, c in zip(progs, current))
            print(f"{out.name}: {sum(map(len, current))} -> {sum(map(len, progs))} lines "
                  f"({changed} programs replaced)", flush=True)


if __name__ == "__main__":
    main()
