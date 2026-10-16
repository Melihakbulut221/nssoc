# Exact graph minima and native slack selection

The four-branch routed candidate remains unaccepted. Run 38850059650 failed the old exact equality check between native `Vertex.slack` and the strict minimum of `PathEnd.slack`. Diagnostic run 38851027534 reproduced one mismatch at `$auto$ff.cc:337:slice$1183756/D`: 1.438214791704695e-08 versus 1.4382139035262753e-08 seconds. Slow rise and fall queries reproduced the values at both path limits 1 and 20.

The pinned OpenSTA implementation selects Vertex slack through `delayLess`, which delegates to `fuzzyLess`; the raw Path slack itself is the required/arrival difference. Thus a source-derived hypothesis is that an earlier, almost equal path remains selected. This does not justify rounding measurements or relaxing timing gates.

The opt-in graph proof enumerates every native rise and fall Path for every endpoint and min/max delay. It compares the exact numerical graph minimum against the exact PathEnd minimum using the unchanged strict equality helper. It retains the old aggregate guard's failures and all raw graph path rows. For any aggregate mismatch, it requires the native worst-slack Path to reproduce the Vertex value exactly and to appear among the raw paths, with unchanged sign. It then builds and executes the exact SHA256-pinned upstream Fuzzy.cc to check that the engine's comparator explains the choice. An unexplained difference, omitted finite path, missing constraint, identity change or sign change fails the proof. No arbitrary tolerance is added.

The full endpoint comparison retains original SDC, libraries, routed ODB and SPEF hashes, all raw slacks, all corner comparisons against both baseline and the 50-cell parent, and targeted setup/hold failures. A successful workflow establishes diagnostic completeness only, never timing closure, qualified extraction or PHY acceptance.

Primary implementation, pinned revision 857316ff001b2a8dbbdc5996944d08a6d38c87ab:

- [Sta.cc: native vertex selection](https://github.com/The-OpenROAD-Project/OpenSTA/blob/857316ff001b2a8dbbdc5996944d08a6d38c87ab/search/Sta.cc#L3097)
- [DelayFloat.cc: comparator delegation](https://github.com/The-OpenROAD-Project/OpenSTA/blob/857316ff001b2a8dbbdc5996944d08a6d38c87ab/graph/DelayFloat.cc#L104)
- [Fuzzy.cc: native equality and ordering](https://github.com/The-OpenROAD-Project/OpenSTA/blob/857316ff001b2a8dbbdc5996944d08a6d38c87ab/util/Fuzzy.cc#L40)
- [Path.cc: raw slack and complete iterator](https://github.com/The-OpenROAD-Project/OpenSTA/blob/857316ff001b2a8dbbdc5996944d08a6d38c87ab/search/Path.cc#L362)

All builds, controls and native route verification run on GitHub-hosted infrastructure. Local project storage remains empty.
