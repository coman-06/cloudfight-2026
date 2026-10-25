import sys
from collections import Counter
from pathlib import Path

DIRS = [
    (0, 2),
    (1, 1),
    (1, -1),
    (0, -2),
    (-1, -1),
    (-1, 1),
]


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


def run(r, program):
    grid = empty_board(r)
    ring = border_ring(r)
    pos = [k * r for k in range(6)]
    active = [False] * 6
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
    return "\n".join("".join(row) for row in grid)


def solve(text):
    lines = [ln for ln in text.splitlines() if ln.strip()]
    n = int(lines[0])
    pos = 1
    out = []
    for _ in range(n):
        r, length = int(lines[pos]), int(lines[pos + 1])
        program = [ln.split() for ln in lines[pos + 2:pos + 2 + length]]
        pos += 2 + length
        out.append(run(r, program) + "\n\n")
    return "".join(out)


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    for inp in sorted(folder.glob("in_level-4_*.txt")):
        out = folder / inp.name.replace("in_", "out_", 1)
        out.write_text(solve(inp.read_text()), newline="\n")
        print(f"{inp.name} -> {out.name}")


if __name__ == "__main__":
    main()
