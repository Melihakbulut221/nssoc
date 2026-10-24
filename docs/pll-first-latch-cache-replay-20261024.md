# Exact first-latch native cache replay

This diagnostic restores only the immutable 131-column, 3,201,410-row selected native cache published by failed full-capture observer run 40096538128. That observer already verified all 5,106 columns and all original 130,771,392,219 bytes before failing in its later voltage snapshot analysis. Its acquisition rejection is retained. This replay neither restores that full capture nor starts a simulator.

The original failure is an empty AssertionError at frozen `cloud_pll_first_latch_sinks.py` line 142. The old snapshot code requires an interior upper row even when an event is exactly the first recorded native time. The new controller must reproduce that exact exception, code object, line, event, interval and actual row-zero time before invoking the separately reviewed sampling helper. An unrelated exception or a missing reproduction fails the replay.

The helper reversibly replaces only the old snapshot block. An event exactly on a recorded time uses that native row; a strictly intervening event uses the same two-row interpolation as before. Out-of-range events remain rejected. Thresholds, all event lists, half-open intervals, statistics and original diagnostic hash remain unchanged. The replay requires at least one actual endpoint witness and matches it to the reproduced failing event.

## Transport and native evidence

The original failed run, attempt, source, job and complete job-log hash are pinned. The authenticated release metadata must match all five assets. All three archive parts are exhausted and individually verified before the combined archive is accepted. The reader permits only the exact root directory and five exact regular members; duplicates, links, sparse files, traversal, alternate roots and extra files are rejected.

The 3,355,077,680-byte selected cache is hash-checked, then scanned in bounded chunks for every finite value and strictly increasing time, including chunk boundaries. Chunked extraction of its prior 80 columns and original eight analyzer columns must reproduce their independent byte hashes. No samples are removed, resampled or reordered. The original 80-column diagnostic must reproduce SHA b876a488ff086e045605544b3d6a3daeedd1ac0215b0b2a6c9df3ceeaa47a0b7.

The controls use actual immutable failure metadata mutations, successful and rejected synthetic three-part streams, exact archive-member fixtures and finite/nonfinite/time/order/bit-corrupt cache fixtures. These are transport and analysis controls, not new circuit simulations. Original observer/source-map controls and the endpoint helper controls remain mandatory.

The selected cache stays in a runner temporary directory. Only small JSON results, original-failure metadata and the resulting diagnosis are published. No large cache is republished. Push activates controls only; a separately guarded manual replay depends on controls. All acquisition, full-device safety, qualified-PEX and full-PHY acceptance flags remain false.

## Preserved hosted CLI rejection and raw-byte correction

Replay 40108109320 at 5508d3a6 passed all 44 original transport controls and the original observer/endpoint controls, then stopped before restoring the actual selected cache. The newer hosted GitHub CLI refused the exact original ANSI-bearing job log unless raw escape sequences were explicitly permitted. The small failed result was published successfully; this was transport rejection, not a newly evaluated PLL waveform.

The corrected captured-log and binary archive pipes explicitly use --allow-escape-sequences. Nothing strips, rewrites, renders or interprets those bytes; the original cryptographic hashes and failure checks still apply. The controls now additionally reject removal of actual ANSI bytes from the authenticated source log and one-byte truncation, for 46 total transport/metadata/cache faults. The successful opaque stream fixture also contains an escape sequence. All original cache, analyzer, acquisition and publication gates remain unchanged.
