# Nanofabricator: Cloudflight Coding Contest solutions

Python solutions for all six levels of the Cloudflight Coding Contest problem
"Nano Fabricator": a hexagonal board where laser emitters create matter where two
beams cross and destroy it where three or more meet.

Levels 1–5 are simulation tasks with exact answers. Level 6 is an optimization task:
for each pattern, write the shortest emitter program that builds it the required
number of times.

## Levels

| Level | Task | Solution |
|---|---|---|
| 1 | Draw a hexagonal board of radius `r` as text | `level1.py` builds each row from its indent `abs(r - i)` and its cell count |
| 2 | Simulate one laser beam | `level2.py`: the six hex directions are fixed (row, column) steps on the character grid |
| 3 | Several beams: 2 hits make matter, 3+ destroy it | `level3.py` counts all hits first, then applies the rules |
| 4 | Run a program of emitter instructions (`F`, `B`, `T`, `-`) | `level4.py`: the border is a clockwise loop of `6r` cells; emitter `k` starts at index `k*r` |
| 5 | Count how often a pattern is picked up | `level5.py`: a pattern counts only if it is complete and no other matter touches it |
| 6 | Generate the shortest programs (score = total lines) | `level6.py` plus improvement passes, see below |

Each script reads `in_level-N_*.txt` from its own folder and writes the matching
`out_level-N_*.txt`. For Levels 1–5 the script first checks its output against the
example file.

## Level 6 approach

Every cell lies on three lines, one per beam direction (cube coordinates). Each emitter
can be slid along the border to fire along any line of its direction. The solvers build
on that:

- **Sweeps.** Up to four emitters stay on fixed lines while one or two "sweepers" slide
  across them. Still emitters switch on only when the sweeper is over a pattern cell,
  so up to 8 cells are made per tick and switching costs no extra ticks.
- **Exact per-tick check.** Every tick, the beams through each cell are counted: a cell
  next to the pattern may never get exactly 2 beams, and a finished cell may never get 3.
- **Moving while on.** An emitter moves to its next line without switching off when every
  crossing of its moving beam is harmless.
- **Look-ahead.** The 30 best-looking sweeps are each tried on copies of the emitters and
  judged together with the sweep that would follow them.
- **Verification.** Every candidate program is run through a simulator of the Level 5
  rules and is only kept if it submits the pattern exactly the required number of times.

Improvement passes start from the existing outputs and only replace a program with a
shorter, verified one:

| Script | What it adds |
|---|---|
| `level6_small.py` | Much heavier search for patterns of 24 cells or fewer |
| `level6_static.py` | Fixed emitter positions that rebuild a pattern every 1–3 ticks |
| `level6_paint.py` | Painting whole lines at once (two emitters on the same line), with holes punched by three beams |
| `level6_wide.py` | 60-wide look-ahead; writes to `improved/` instead of overwriting the outputs |

### Results (lines, lower is better)

| Input | Lines |
|---|---|
| small | 149 |
| medium | 9,034 |
| large | 9,548 |
| enormous | 9,426 |
| **Total** | **28,157** |

The first working version scored 70,571, so the final programs are 60% shorter.

## Running

Python 3.10 or newer; no external packages.

```bash
python level1.py
```

Level 6 runs in parallel on all CPU cores. The main run takes about an hour on 32 cores;
the passes take a few minutes each.

```bash
python level6.py
python level6_small.py
python level6_static.py
python level6_paint.py
```
