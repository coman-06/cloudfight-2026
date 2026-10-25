import random
import sys
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

DIRS = [
    (0, 2),
    (1, 1),
    (1, -1),
    (0, -2),
    (-1, -1),
    (-1, 1),
]

FAMILY = [0, 1, 2, 0, 1, 2]


def empty_board(r):
    rows = []
    for i in range(2 * r + 1):
        d = abs(r - i)
        k = 2 * r + 1 - d
        if i == 0 or i == 2 * r:
            cells = ["*"] * k
        else:
            cells = ["*"] + ["O"] * (k - 2) + ["*"]
        rows.append(list("-" * d + "-".join(cells) + "-" * d))
    return rows


def border_ring(r):
    w = 4 * r + 1
    ring = []
    for i in range(r):
        ring.append((r - i, i))
    for c in range(r, w - 1 - r, 2):
        ring.append((0, c))
    for i in range(r):
        ring.append((i, w - 1 - r + i))
    for i in range(r):
        ring.append((r + i, w - 1 - i))
    for c in range(w - 1 - r, r, -2):
        ring.append((2 * r, c))
    for i in range(r):
        ring.append((2 * r - i, r - i))
    return ring


def to_cube(r, y, x):
    return (y - r, (x - y - r) // 2, (3 * r - x - y) // 2)


def simulate(r, pattern, program):
    grid = empty_board(r)
    ring = border_ring(r)
    pos = [k * r for k in range(6)]
    active = [False] * 6
    submitted = 0
    for line in program:
        for k, op in enumerate(line):
            if op == "F":
                pos[k] = (pos[k] + 1) % len(ring)
            elif op == "B":
                pos[k] = (pos[k] - 1) % len(ring)
            elif op == "T":
                active[k] = not active[k]
        hits = Counter()
        for k in range(6):
            if not active[k]:
                continue
            dr, dc = DIRS[k]
            y, x = ring[pos[k]]
            y, x = y + dr, x + dc
            while 0 <= y < len(grid) and 0 <= x < len(grid[y]):
                if grid[y][x] in "OM":
                    hits[y, x] += 1
                y, x = y + dr, x + dc
        for (y, x), n in hits.items():
            if n == 2:
                grid[y][x] = "M"
            elif n >= 3:
                grid[y][x] = "O"
        ok = all(grid[y][x] == "M" for y, x in pattern)
        if ok:
            for y, x in pattern:
                for dy, dx in DIRS:
                    ny, nx = y + dy, x + dx
                    if (ny, nx) not in pattern and 0 <= ny < len(grid) \
                            and 0 <= nx < len(grid[ny]) and grid[ny][nx] == "M":
                        ok = False
        if ok:
            for y, x in pattern:
                grid[y][x] = "O"
            submitted += 1
    return submitted


def line_offsets(r):
    ring = border_ring(r)
    n = len(ring)
    table = []
    for k in range(6):
        dr, dc = DIRS[k]
        m = {}
        for off in range(-(r - 1), r):
            y, x = ring[(k * r + off) % n]
            ny, nx = y + dr, x + dc
            assert 0 <= ny <= 2 * r and abs(r - ny) <= nx <= 4 * r - abs(r - ny)
            m[to_cube(r, ny, nx)[FAMILY[k]]] = off
        assert len(m) == 2 * r - 1
        table.append(m)
    return table


class Plan:
    def __init__(self, r, ea, eb):
        self.lines = []
        self.ea, self.eb = ea, eb
        self.offs = line_offsets(r)
        self.off = [0] * 6
        self.on = [False] * 6

    def tick(self, ops):
        line = ["-"] * 6
        for k, op in ops.items():
            line[k] = op
            if op == "F":
                self.off[k] += 1
            elif op == "B":
                self.off[k] -= 1
            elif op == "T":
                self.on[k] = not self.on[k]
        self.lines.append(line)

    def step_toward(self, k, value):
        target = self.offs[k][value]
        if self.off[k] < target:
            return "F"
        if self.off[k] > target:
            return "B"
        return None

    def walk(self, a, b):
        ops = {}
        for k, v in ((self.ea, a), (self.eb, b)):
            op = self.step_toward(k, v)
            if op:
                ops[k] = op
        self.tick(ops)

    def jump(self, a, b, lift):
        other = self.eb if lift == self.ea else self.ea
        targets = {self.ea: a, self.eb: b}
        d_lift = self._remaining(lift, targets[lift])
        d_other = self._remaining(other, targets[other])
        if self.on[lift]:
            total = max(d_lift + 2, d_other)
            lift_ops = ["T"] + ["move"] * d_lift
            other_ops = ["move"] * d_other
        else:
            total = max(d_lift, d_other + 1) + 1
            lift_ops = ["move"] * d_lift
            other_ops = ["T"] + ["move"] * d_other
        lift_ops += [None] * (total - 1 - len(lift_ops)) + ["T"]
        other_ops += [None] * (total - len(other_ops))
        for t in range(total):
            ops = {}
            for k, seq in ((lift, lift_ops), (other, other_ops)):
                op = seq[t]
                if op == "move":
                    op = self.step_toward(k, targets[k])
                if op:
                    ops[k] = op
            self.tick(ops)
        assert self.on[lift] and self.on[other]

    def _remaining(self, k, value):
        return abs(self.offs[k][value] - self.off[k])


def lift_cost(da, db):
    return min(max(da, db + 2), max(da + 2, db))


def build_program(r, cells, count, fa, fb):
    ea, eb = fa, fb
    plan = Plan(r, ea, eb)
    lim = r - 1
    pat = {(c[fa], c[fb]) for c in cells}

    def allowed(a, b):
        return (a, b) in pat or abs(a + b) >= r

    cur = (0, 0)
    started = False
    for _ in range(count):
        todo = set(pat)
        if started and cur in todo:
            plan.tick({})
            todo.discard(cur)
        while todo:
            best_walk = None
            if started:
                prev = {cur: None}
                dist = {cur: 0}
                q = deque([cur])
                while q:
                    p = q.popleft()
                    if p in todo:
                        best_walk = p
                        break
                    for da in (-1, 0, 1):
                        for db in (-1, 0, 1):
                            n = (p[0] + da, p[1] + db)
                            if n in prev or not (-lim <= n[0] <= lim and -lim <= n[1] <= lim):
                                continue
                            if not allowed(*n):
                                continue
                            prev[n] = p
                            dist[n] = dist[p] + 1
                            q.append(n)
            best_jump, jump_cost = None, None
            for t in sorted(todo):
                da, db = abs(t[0] - cur[0]), abs(t[1] - cur[1])
                c = lift_cost(da, db) if started else max(da, db) + 1
                if jump_cost is None or c < jump_cost:
                    best_jump, jump_cost = t, c
            if best_walk is not None and dist[best_walk] <= jump_cost:
                path = []
                p = best_walk
                while p != cur:
                    path.append(p)
                    p = prev[p]
                for p in reversed(path):
                    plan.walk(*p)
                    todo.discard(p)
                cur = best_walk
            else:
                t = best_jump
                da, db = abs(t[0] - cur[0]), abs(t[1] - cur[1])
                lift = eb if max(da, db + 2) <= max(da + 2, db) else ea
                plan.jump(t[0], t[1], lift)
                started = True
                todo.discard(t)
                cur = t
    return plan.lines


class Emitter:
    def __init__(self, k, offs):
        self.k = k
        self.offs = offs[k]
        self.at = {o: v for v, o in self.offs.items()}
        self.val = self.at[0]
        self.on = False
        self.free = 1
        self.ops = {}
        self.hist = [(self.val, False)]
        self.pending = False

    def do(self, t, op):
        assert t >= len(self.hist), (self.k, t, len(self.hist))
        while len(self.hist) < t:
            self.hist.append((self.val, self.on))
        if op == "T":
            self.on = not self.on
        else:
            step = 1 if op == "F" else -1
            self.val = self.at[self.offs[self.val] + step]
        self.ops[t] = op
        self.hist.append((self.val, self.on))

    def state_at(self, t):
        return self.hist[t] if t < len(self.hist) else (self.val, self.on)

    def move_to(self, value, start):
        t = start
        while self.val != value:
            self.do(t, "F" if self.offs[value] > self.offs[self.val] else "B")
            t += 1
        return t

    def clone(self):
        c = Emitter.__new__(Emitter)
        c.__dict__ = dict(self.__dict__)
        c.ops = dict(self.ops)
        c.hist = list(self.hist)
        return c


def build_bands(r, cells, count, fw, max_gap=4, alpha=1.0):
    offs = line_offsets(r)
    em = [Emitter(k, offs) for k in range(6)]
    fs = [f for f in range(3) if f != fw]
    rigs = [(em[fs[0]], em[fs[0] + 3], em[fw]), (em[fs[1]], em[fs[1] + 3], em[fw + 3])]
    last = 0
    prev_rig = None

    for _ in range(count):
        remaining = set(cells)
        while remaining:
            best = None
            for ri, (s1, s2, w) in enumerate(rigs):
                f = fs[ri]
                lines = {}
                for c in remaining:
                    lines.setdefault(c[f], []).append(c[fw])
                stats = {u: (min(v), max(v), len(v)) for u, v in lines.items()}
                keys = sorted(stats)
                pairs = [(u, None) for u in keys]
                pairs += [(u1, u2) for i, u1 in enumerate(keys) for u2 in keys[i + 1:]
                          if u2 - u1 <= max_gap]
                for u1, u2 in pairs:
                    for a1, a2 in ((u1, u2), (u2, u1)):
                        used = [(s, u) for s, u in ((s1, a1), (s2, a2)) if u is not None]
                        lo = min(stats[u][0] for _, u in used)
                        hi = max(stats[u][1] for _, u in used)
                        gain = sum(stats[u][2] for _, u in used)
                        for d in (1, -1):
                            bs = lo if d > 0 else hi
                            n = hi - lo + 1
                            dist = abs(bs - w.val)
                            t0 = last + 1
                            if w.on and prev_rig == ri:
                                t0 = max(t0, w.free + dist - 1)
                            else:
                                t0 = max(t0, w.free + dist)
                            for s, u in used:
                                k = (stats[u][0] - bs) if d > 0 else (bs - stats[u][1])
                                t0 = max(t0, s.free + abs(u - s.val) - k)
                            t1 = t0 + n - 1
                            score = gain / (t1 - last) ** alpha
                            if best is None or score > best[0]:
                                best = (score, ri, used, bs, d, n, t0, t1)
            _, ri, used, bs, d, n, t0, t1 = best
            s1, s2, w = rigs[ri]
            other_w = rigs[1 - ri][2]
            if other_w.on:
                other_w.ops[last + 1] = "T"
                other_w.on = False
                other_w.free = last + 2
            keep_on = w.on and prev_rig == ri
            if keep_on:
                w.move_to(bs, w.free)
            else:
                if w.on:
                    w.ops[w.free] = "T"
                    w.free += 1
                w.move_to(bs, w.free)
                w.ops[t0] = "T"
                w.on = True
            w.move_to(bs + d * (n - 1), t0 + 1)
            w.free = t1 + 1
            f = fs[ri]
            for s, u in used:
                s.move_to(u, s.free)
                need = {(c[fw] - bs) * d for c in remaining if c[f] == u}
                state = False
                for k in range(n):
                    want = k in need
                    if want != state:
                        s.ops[t0 + k] = "T"
                        state = want
                if state:
                    s.ops[t0 + n] = "T"
                s.free = t0 + max(need) + 2
                s.on = False
                remaining -= {c for c in remaining if c[f] == u}
            last = t1
            prev_rig = ri

    lines = []
    for t in range(1, last + 1):
        lines.append([e.ops.get(t, "-") for e in em])
    return lines


def neighbours(c):
    a, b, d = c
    return [(a, b + 1, d - 1), (a, b - 1, d + 1), (a + 1, b, d - 1),
            (a - 1, b, d + 1), (a + 1, b - 1, d), (a - 1, b + 1, d)]


def build_cross(r, cells, count, fw, max_gap=4, alpha=1.0, top_k=5, dual=True, seed=None,
                hot_transit=True, lookahead=0):
    rng = random.Random(seed) if seed is not None else None
    offs = line_offsets(r)
    sweep_families = [fw] if fw is not None else [0, 1, 2]
    pattern = set(cells)
    halo = {n for c in pattern for n in neighbours(c)
            if n not in pattern and max(map(abs, n)) <= r - 1}
    lim = r - 1

    def fam(e):
        return FAMILY[e.k]

    def resolve(fixed, candidates, remaining):
        on = list(fixed)
        chosen = []
        made = set()
        for cand in candidates:
            trial = on + [(fam(cand[0]), cand[1])]
            hits = {}
            ok = True
            for i in range(len(trial)):
                fi, vi = trial[i]
                for j in range(i + 1, len(trial)):
                    fj, vj = trial[j]
                    if fi == fj:
                        if vi == vj:
                            ok = False
                        continue
                    c = [0, 0, 0]
                    c[fi], c[fj] = vi, vj
                    c[3 - fi - fj] = -vi - vj
                    c = tuple(c)
                    if max(abs(c[0]), abs(c[1]), abs(c[2])) <= lim:
                        hits[c] = hits.get(c, 0) + 1
            if not ok:
                continue
            new = set()
            for c, n in hits.items():
                if n == 1:
                    if c in halo:
                        ok = False
                        break
                    if c in remaining:
                        new.add(c)
                elif c in pattern and c not in remaining:
                    ok = False
                    break
            if ok and len(new) > len(made):
                on = trial
                chosen.append(cand[0])
                made = new
        return chosen, made

    def schedule(em, last, sw, used, on_ticks, hot, d, t0, length):
        sc = {e: e.clone() for e in em}
        t1 = t0 + length - 1
        sw_set = {w for w, _, _ in sw}
        used_on = [(s, u) for s, u in used if on_ticks[s]]
        busy = {s for s, _ in used_on}
        for e in em:
            c = sc[e]
            if c.on and not c.pending and e not in sw_set:
                c.do(last + 1, "T")
                c.free = last + 2
            elif c.pending and e not in busy:
                c.do(c.free, "T")
                c.pending = False
                c.free += 1
        for w, x, end in sw:
            c = sc[w]
            c.move_to(x, c.free)
            if not c.on:
                c.do(t0, "T")
            c.move_to(x + d * min(length - 1, abs(end - x)), t0 + 1)
            c.free = t1 + 1
        for s, u in used_on:
            c = sc[s]
            ticks = on_ticks[s]
            if c.pending and s not in hot:
                c.do(c.free, "T")
                c.free += 1
            c.move_to(u, c.free)
            state = c.on
            tick_set = set(ticks)
            for k in range(ticks[-1] + 1):
                want = k in tick_set or (s in hot and k < ticks[0])
                if want != state:
                    c.do(t0 + k, "T")
                    state = want
            c.pending = True
            c.free = t0 + ticks[-1] + 1
        return sc

    def hot_ok(em, sc, s, ta, tb, remaining):
        fs_ = fam(s)
        for t in range(ta, tb + 1):
            v, on = sc[s].state_at(t)
            if not on:
                continue
            lines = [(fam(e),) + sc[e].state_at(t) for e in em if e is not s]
            lines = [(f, ve) for f, ve, one in lines if one]
            for fe, ve in lines:
                if fe == fs_:
                    if ve == v:
                        return False
                    continue
                c = [0, 0, 0]
                c[fs_], c[fe] = v, ve
                c[3 - fs_ - fe] = -v - ve
                c = tuple(c)
                if max(abs(c[0]), abs(c[1]), abs(c[2])) > lim or (c not in pattern and c not in halo):
                    continue
                if c in halo or c in remaining:
                    return False
                if sum(1 for f, x in lines if c[f] == x) > 1:
                    return False
        return True

    def ready_tick(s, u, hot):
        dist = abs(u - s.val)
        if s.pending:
            if hot:
                return s.free - 1 + max(dist, 1)
            return s.free + 1 + dist
        if s.on:
            return s.free + 1 + dist
        return s.free + dist

    def sweeper_start(w, dist):
        if w.pending:
            return w.free + 1 + dist
        if w.on:
            return w.free + dist - 1
        return w.free + dist

    def first_tick(stats, u, starts, d, length):
        best_k = None
        for x0 in starts:
            for v in stats[u]:
                k = (v - x0) * d
                if 0 <= k < length and (best_k is None or k < best_k):
                    best_k = k
        return best_k

    def plan_t0(em, last, fw_c, sw, used, hot, d, length, stats):
        t0 = last + 1
        for w, x, _ in sw:
            t0 = max(t0, sweeper_start(w, abs(x - w.val)))
        starts = [x for _, x, _ in sw]
        for s, u in used:
            k = first_tick(stats[fam(s)], u, starts, d, length)
            if k is not None:
                t0 = max(t0, ready_tick(s, u, s in hot) - k)
        return t0

    def select(em, last, remaining, no_hot, banned, noise):
        found = []
        for fw_c in sweep_families:
            fs = [f for f in range(3) if f != fw_c]
            stats_by_f = {}
            options = {}
            for f in fs:
                lines = {}
                for c in remaining:
                    lines.setdefault(c[f], []).append(c[fw_c])
                stats = {u: sorted(v) for u, v in lines.items()}
                stats_by_f[f] = stats
                keys = sorted(stats)
                groups = [(u,) for u in keys]
                groups += [(u1, u2) for i, u1 in enumerate(keys) for u2 in keys[i + 1:]
                           if u2 - u1 <= max_gap]
                e0, e1 = em[f], em[f + 3]
                opts = []
                for g in groups:
                    for order in ((e0, e1), (e1, e0)):
                        used = list(zip(order, g))
                        lo = min(stats[u][0] for u in g)
                        hi = max(stats[u][-1] for u in g)
                        gain = sum(len(stats[u]) for u in g)
                        reach = max(abs(u - e.val) for e, u in used)
                        opts.append((gain / (hi - lo + 1 + reach), used, lo, hi, gain))
                opts.sort(key=lambda o: -o[0])
                options[f] = [None] + opts[:top_k]
            sweepers = [em[fw_c], em[fw_c + 3]]
            for oa in options[fs[0]]:
                for ob in options[fs[1]]:
                    if oa is None and ob is None:
                        continue
                    used = (oa[1] if oa else []) + (ob[1] if ob else [])
                    lo = min(o[2] for o in (oa, ob) if o)
                    hi = max(o[3] for o in (oa, ob) if o)
                    gain = sum(o[4] for o in (oa, ob) if o)
                    if oa and ob:
                        for _, u0 in oa[1]:
                            for _, u1 in ob[1]:
                                c = [0, 0, 0]
                                c[fs[0]], c[fs[1]] = u0, u1
                                c[fw_c] = -u0 - u1
                                if tuple(c) in remaining:
                                    gain -= 1
                    n = hi - lo + 1
                    plans = []
                    for d in (1, -1):
                        bs = lo if d > 0 else hi
                        for w in sweepers:
                            plans.append((d, n, [(w, bs, bs + d * (n - 1))]))
                        if dual and n >= 2:
                            n1 = (n + 1) // 2
                            low_w, high_w = sorted(sweepers, key=lambda e: (e.val, e.k))
                            if d > 0:
                                halves = [(low_w, lo, lo + n1 - 1), (high_w, lo + n1, hi)]
                            else:
                                halves = [(low_w, lo + n1 - 1, lo), (high_w, hi, lo + n1)]
                            plans.append((d, n1, halves))
                    optimistic = {s for s, _ in used if s.pending and s.k not in no_hot}
                    for d, length, sw in plans:
                        key = (fw_c, tuple((s.k, u) for s, u in used), d,
                               tuple((w.k, x) for w, x, _ in sw))
                        if key in banned:
                            continue
                        t0 = plan_t0(em, last, fw_c, sw, used, optimistic, d, length, stats_by_f)
                        end = t0 + length - 1
                        score = gain / (end - last) ** alpha
                        if noise:
                            score *= 1 + 0.15 * noise.random()
                        found.append((score, fw_c, d, length, sw, used, key, gain, end, stats_by_f))
        found.sort(key=lambda p: -p[0])
        return found

    def commit(em, last, remaining, plan, no_hot, fallback):
        _, fw_c, d, length, sw, used, key, _, _, stats_by_f = plan
        hot = {s for s, _ in used if s.pending and s.k not in no_hot}
        while True:
            t0 = plan_t0(em, last, fw_c, sw, used, hot, d, length, stats_by_f)
            ready = {s: ready_tick(s, u, s in hot) - t0 for s, u in used}
            on_ticks = {s: [] for s, _ in used}
            last_mark = -1
            after = set(remaining)
            for k in range(length):
                fixed = [(fw_c, x + d * min(k, abs(end - x))) for _, x, end in sw]
                cands = sorted((su for su in used if k >= ready[su[0]]), key=lambda su: -sum(
                    1 for _, v in fixed if cell_of(fw_c, v, fam(su[0]), su[1]) in after))
                chosen, made = resolve(fixed, cands, after)
                for e in chosen:
                    on_ticks[e].append(k)
                if chosen:
                    last_mark = k
                after -= made
            if last_mark < 0:
                return ("empty",)
            hot = {e for e in hot if on_ticks[e]}
            sc = schedule(em, last, sw, used, on_ticks, hot, d, t0, last_mark + 1)
            bad = {e for e in hot
                   if not hot_ok(em, sc, e, e.free, t0 + on_ticks[e][0] - 1, remaining)}
            if not bad:
                return ("ok", sc, after, t0 + last_mark)
            if not fallback:
                return ("hot", {e.k for e in bad})
            hot -= bad

    em = [Emitter(k, offs) for k in range(6)]
    last = 0
    all_k = set(range(6))
    for _ in range(count):
        remaining = set(cells)
        while remaining:
            banned = set()
            no_hot = set() if hot_transit else set(all_k)
            done = None
            while done is None:
                plans = select(em, last, remaining, no_hot, banned, rng)
                if not lookahead:
                    res = commit(em, last, remaining, plans[0], no_hot, False)
                    if res[0] == "ok":
                        done = res
                    elif res[0] == "empty":
                        banned.add(plans[0][6])
                    else:
                        no_hot |= res[1]
                    continue
                best_value = None
                for plan in plans[:lookahead]:
                    res = commit(em, last, remaining, plan, no_hot, True)
                    if res[0] != "ok":
                        banned.add(plan[6])
                        continue
                    _, sc, after, new_last = res
                    gain = len(remaining) - len(after)
                    span = new_last - last
                    if after:
                        nxt = select([sc[e] for e in em], new_last, after,
                                     set() if hot_transit else set(all_k), set(), None)
                        if nxt:
                            gain += nxt[0][7]
                            span += nxt[0][8] - new_last
                    value = gain / span ** alpha
                    if rng:
                        value *= 1 + 0.15 * rng.random()
                    if best_value is None or value > best_value:
                        best_value, done = value, res
            _, sc, remaining, last = done
            for e in em:
                e.__dict__.update(sc[e].__dict__)

    for e in em:
        if e.pending and e.free <= last:
            e.do(e.free, "T")
    lines = []
    for t in range(1, last + 1):
        lines.append([e.ops.get(t, "-") for e in em])
    return lines


def cell_of(fw, beta, f, u):
    c = [0, 0, 0]
    c[fw], c[f] = beta, u
    c[3 - f - fw] = -beta - u
    return tuple(c)


CROSS_SETTINGS = [
    (8, 1.0, 16, True, None), (6, 0.8, 12, False, None), (8, 0.8, 16, True, None),
    (4, 1.0, 16, True, None), (6, 1.0, 12, True, None), (4, 1.0, 12, False, None),
    (6, 1.0, 12, False, None), (8, 0.6, 16, False, None), (6, 0.8, 16, True, None),
    (4, 0.6, 16, True, None),
]
CROSS_SETTINGS += [s + (True, 30) for s in CROSS_SETTINGS[:4]]
BAND_SETTINGS = [(4, 0.8)]


def solve_one(case):
    r, rows, count = case
    grid_cells = {(y, x) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == "M"}
    cube = {to_cube(r, y, x) for y, x in grid_cells}
    candidates = []
    for fw in (0, 1, 2, None):
        for setting in CROSS_SETTINGS:
            candidates.append((build_cross, (fw,) + setting))
    for fw in range(3):
        for setting in BAND_SETTINGS:
            candidates.append((build_bands, (fw,) + setting))
    best = None
    for build, args in candidates:
        prog = build(r, cube, count, *args)
        if (best is None or len(prog) < len(best)) and simulate(r, grid_cells, prog) == count:
            best = prog
    if best is None:
        best = min((build_program(r, cube, count, fa, fb)
                    for fa, fb in ((0, 1), (0, 2), (1, 2))), key=len)
    assert simulate(r, grid_cells, best) == count
    return best


def parse(text):
    lines = [ln for ln in text.splitlines() if ln.strip()]
    n = int(lines[0])
    pos = 1
    cases = []
    for _ in range(n):
        r, rows, _, count = map(int, lines[pos].split())
        cases.append((r, lines[pos + 1:pos + 1 + rows], count))
        pos += 1 + rows
    return cases


def solve(text, pool=None):
    cases = parse(text)
    progs = pool.map(solve_one, cases, chunksize=1) if pool else map(solve_one, cases)
    return "".join("\n".join(" ".join(line) for line in prog) + "\n\n" for prog in progs)


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    with ProcessPoolExecutor() as pool:
        for inp in sorted(folder.glob("in_level-6_*.txt")):
            out = folder / inp.name.replace("in_", "out_", 1)
            result = solve(inp.read_text(), pool)
            out.write_text(result, newline="\n")
            score = sum(1 for ln in result.splitlines() if ln.strip())
            print(f"{inp.name} -> {out.name}  (score {score})", flush=True)


if __name__ == "__main__":
    main()
