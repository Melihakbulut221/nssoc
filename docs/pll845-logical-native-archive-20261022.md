# Lossless logical archive qualification for the original PLL acquisition

The real 1 us, 5,106-column PLL acquisition remains saved at 892.691247612 ns in run 39674830790. No complete capture or lock is claimed. Sparse working-file native continuation and the original prefix reader were qualified separately; production archive publication/restoration remained missing.

The new storage path writes an ordinary tar member using every current retained header byte, the verified immutable archived prefix, and the actual current tail/append. It consumes the immutable source to EOF, validates both source SHA256 and original payload SHA256, checks source-tree identity and caller-established process quiescence, and requires every upload receipt before publishing a manifest. Failed or partial publications never produce a complete manifest. Only the exact temporary compressed part is removed after remote verification; native sources are retained.

The corresponding restore verifies each archive part and the whole ordered stream, while materializing only retained head/tail portions of the original native member into a new sparse working file. Native activation is not performed by either helper. An unreconstructed sparse file remains invalid as a waveform.

Cloud controls preserve the 12 original archive and 16 sparse-corruption controls, then exercise 16 additional publication/restore failures. The independent native-prefix case uses the exact recorded 2 MiB, 5,106-column PLL prefix, including its incomplete final row, publishes through real GitHub assets, restores through the original archive reader and reproduces the unchanged 16 native-reader controls. It also checks sparse re-restoration. No probes are removed or rows decimated. These are qualification jobs; their actual results must be reviewed before production use.

The helper uses Python 3.12 streaming tar compression and explicitly selects the data extraction filter; see the [Python tarfile documentation](https://docs.python.org/3.12/library/tarfile.html). Full native checkpoint-capsule continuation and the complete 1 us reader/safety gates remain required after this storage test. Existing 12 GiB checkpoint, 4 GiB backing and 6 GiB allocation safeguards are not relaxed.

All tests and evidence publication run on GitHub-hosted runners. The local workspace remains empty.
