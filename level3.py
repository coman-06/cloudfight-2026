import sys
from collections import Counter
from pathlib import Path

DIRS = {
    "1": (0, 2),
    "2": (1, 1),
    "3": (1, -1),
    "4": (0, -2),
    "5": (-1, -1),
    "6": (-1, 1),
}


def fire(grid):
    hits = Counter()
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch in DIRS:
                dr, dc = DIRS[ch]
                y, x = r + dr, c + dc
                while 0 <= y < len(grid) and 0 <= x < len(grid[y]):
                    if grid[y][x] in "OM":
                        hits[y, x] += 1
                    y, x = y + dr, x + dc
    for (y, x), n in hits.items():
        if n == 2:
            grid[y][x] = "M"
        elif n >= 3:
            grid[y][x] = "O"


def solve(text):
    lines = [ln for ln in text.splitlines() if ln.strip()]
    n = int(lines[0])
    pos = 1
    out = []
    for _ in range(n):
        _, rows, _ = map(int, lines[pos].split())
        grid = [list(ln) for ln in lines[pos + 1:pos + 1 + rows]]
        pos += 1 + rows
        fire(grid)
        out.append("\n".join("".join(row) for row in grid) + "\n\n")
    return "".join(out)


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    for inp in sorted(folder.glob("in_level-3_*.txt")):
        out = folder / inp.name.replace("in_", "out_", 1)
        out.write_text(solve(inp.read_text()), newline="\n")
        print(f"{inp.name} -> {out.name}")


if __name__ == "__main__":
    main()
