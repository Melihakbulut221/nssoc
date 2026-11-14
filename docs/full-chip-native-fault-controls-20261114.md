# Full-chip native fault controls — 2026-11-14

The saved full-chip engineering LVS graphs now pass an identity replay and reject three deliberately introduced faults. This qualifies detection on the exact previously extracted design; it does not validate a later route or establish manufacturing approval.

[Cloud run 43607561776](https://github.com/Melihakbulut221/nssoc/actions/runs/43607561776), source `0af445ae8447e48a7fbd1252f1693df19acc3bfb`, ran the identity check first and then the three negative controls. No command failure was accepted as fault detection.

| Case | Native comparison | Strict port check | Expected result |
| --- | --- | --- | --- |
| Unchanged design | 108 Match | Pass | Accept |
| Disconnect top-cell input A | 107 Match, 1 NoMatch | Not run after mismatch | Reject |
| DP SRAM transistor width 0.30 to 0.45 | 107 Match, 1 NoMatch | Not run after mismatch | Reject |
| Rename CAN_RX_I reference net | 108 Match | Fail | Reject |

The SRAM mutation changes one transistor in a shared bitkit definition; it is not a claim of a single isolated physical-instance defect. The signal mutation disconnects `NSCELL_0` (`SG13G2_NOR2_1`) input `A` from `NSNET_356`. The port mutation leaves topology unchanged and proves that the strict label check is effective independently of topology matching.

Every case independently restores the same immutable native database and verifies its SHA-256 afterward. It does not reuse original net or pin matches, blackbox SRAMs, remove devices, or introduce net equivalences. Original circuit-name correspondence and validated device-model correspondence are retained.

The replay explicitly clears stale cross-reference results. It also restores the original SPICE reader's case-insensitive reference semantics, which the stored database did not retain. The original KLayout v0.30.13 [SPICE reader](https://github.com/KLayout/klayout/blob/v0.30.13/src/db/db/dbNetlistSpiceReader.cc#L1325) explicitly sets that mode. Both top interfaces have 354 unique names under those semantics. Names are not rewritten and the strict port check remains mandatory.

## Reproduction

Run only on a cloud runner with Python 3.12 and `klayout==0.30.13`. Obtain native artifact `14117582646` as `native.zip`; the helper checks the exact archive and database hashes. Invoke the tested helper in this order, stopping on any failure:

```sh
set -euo pipefail
for case in identity signal_open sram_mos_width port_name; do
  python3 scripts/check_full_chip_native_faults.py "$case"
done
```

The original run's final aggregate required exactly these four results, unchanged database hashes, and each intended gate result. Safe artifact `14118697093` contains the aggregate and per-case JSON. Its hash and the full result are recorded in `docs/evidence/full-chip-native-fault-controls-20261114.json`. Native databases remain on the cloud runner; only derived reports are published for inspection.

This result supplements the full engineering transistor LVS pass for the old packet-interface GDS. New routed GDS, full serial Gen3 x4 PHY, all-corner timing, qualified extraction, padframe/DFT and manufacturing approval retain their separate acceptance requirements.
