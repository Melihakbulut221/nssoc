# Core-only routing continuation

The authenticated postCTS producer [44242709956](https://github.com/Melihakbulut221/nssoc/actions/runs/44242709956), source d6e690676c9f1fecaccea89b0ef4fcc6146d2e1b, completed both repair phases. Native artifact 14401785833 SHA256 32ccd56e3e7091231c0ddb7a60ef033d7cb15ff54bacd44101add577b137d3d2 was independently checked, including all 365 inner output hashes and all six fresh per-process corner metric files.

At 20 ns / 5 percent derate, final placement-estimated results:

| Corner | Setup worst slack ns | Hold worst slack ns | Setup / hold violations | Slew / cap violations |
| --- | ---: | ---: | --- | --- |
| slow | 1.38514 | 0.509246 | 0 / 0 | 2 / 0 |
| typical | 8.04945 | 0.219521 | 0 / 0 | 1 / 0 |
| fast | 10.6079 | 0.055888 | 0 / 0 | 0 / 0 |

There are also 748 reported fanout violations at each corner. None is waived here. These are core placement estimates, not extracted timing or full-chip signoff.

The new cloud runner restores and authenticates mapping, placement/CTS, and repaired postCTS artifacts. It retains the exact source and constraints, runs native global routing, then runs each timing corner in its own process. The STA wrapper rejects a database without global routes instead of falling back to placement estimates. Fresh metric files are required. Native output is retained even on failure. Successful execution is not timing acceptance: detailed routing, electrical repair, qualified RC, padframe, DRC/LVS, boot, DFT and production approval remain independent gates. PCIe and Ethernet remain outside the release scope.
