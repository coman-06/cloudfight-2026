import sys
from pathlib import Path


def board(r):
    rows = []
    for i in range(2 * r + 1):
        d = abs(r - i)
        k = 2 * r + 1 - d
        if i == 0 or i == 2 * r:
            cells = ["*"] * k
        else:
            cells = ["*"] + ["O"] * (k - 2) + ["*"]
        rows.append("-" * d + "-".join(cells) + "-" * d)
    return "\n".join(rows)


def solve(text):
    nums = list(map(int, text.split()))
    n, radii = nums[0], nums[1:]
    return "".join(board(r) + "\n\n" for r in radii[:n])


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    for inp in sorted(folder.glob("in_level-1_*.txt")):
        out = folder / inp.name.replace("in_", "out_", 1)
        out.write_text(solve(inp.read_text()), newline="\n")
        print(f"{inp.name} -> {out.name}")


if __name__ == "__main__":
    main()
