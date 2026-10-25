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
| 6 | Generate the shortest programs (score = total lines) | `level6.py` |

Each script reads `in_level-N_*.txt` from its own folder and writes the matching
`out_level-N_*.txt`. For Levels 1–5 the script first checks its output against the
example file.
