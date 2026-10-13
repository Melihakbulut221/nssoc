<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# NSSOC cloud continuation — 13 October 2026

The user requires cloud execution and removal of local NSSOC working data after
verified preservation. Use `Melihakbulut221/nssoc`, branch
`codex/complete-open-work`. Read this file and
`docs/evidence/cloud-closure-continuation-20261013.json` through the GitHub API
when the local workspace is empty. Do not recreate a local CAD checkout or
resume historical local producers. Only GitHub-hosted runners run CAD/tests.

## Preservation and local retirement

- Main output migration completed: 397,166 planned paths, 448 archive batches,
  274,984,789,765 logical original bytes removed after immutable remote receipt
  verification. This is a logical byte count, not an allocated disk-space claim.
- PNR and tool-file migrations completed earlier; their independent hosted
  readbacks passed. Historical sources, links, scratch and external checkouts
  have separate receipts under `docs/evidence/cloud-*-cleanup-20261013.json`.
- Final all-family reconstruction:
  [38364679770](https://github.com/Melihakbulut221/nssoc/actions/runs/38364679770).
  Inspect its actual outcome; dispatch is not acceptance.
- Temporary `/dev/shm/nssoc*` and `/tmp/nssoc*` preservation uses release
  `cloud-migration-transients-20261013`. The first two batches had local full
  remote readback; subsequent batches use hosted per-member readback. Each
  manifest binds an immutable archive, original paths, modes and hashes.
- Final checkout preservation uses release
  `cloud-migration-final-checkout-20261013`. It includes **all Git objects**,
  sources and controller state, including original-location records for six
  ancillary `/tmp` scripts. Do not infer that cleanup completed from this file:
  the authoritative proof is that release's `retirement-progress.json`, with
  status `COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE`.
- Final checkout deletion requires completed transfers, pushed clean source,
  a dispatched cloud reconstruction, stopped local controllers, and exact
  hosted archive member proof for each batch. Original files are rehashed
  immediately before unlinking. Links are preserved as metadata; targets are
  never followed. Changed or newly created files stop final completion.
- If interrupted during final retirement, the temporary restart controller is
  `/tmp/nssoc-final-checkout-20261013/resume.py`; run it with
  `PYTHONDONTWRITEBYTECODE=1` only to resume transfer/cleanup. It is deleted on
  success. Its code, inventory and manifests also reside in the final-checkout
  release. Do not restart a full migration blindly.

The eight-hour task automation now reads cloud state and prohibits local CAD
and recloning. It reports meaningful changes, not unchanged polling results.

## Engineering state — still open

Full serial PCIe Gen3 x4 PHY, main-chip PCIe/Ethernet detailed routing and final
setup/hold are **not complete**. Component screens are not full PHY, qualified
RF/body extraction, assembled analog clock/CDR/ESD integration or foundry
acceptance.

- Main routing run `38347061685` failed with GRT-0116: the native SRAM M5
  reservation regressed total overflow from 147 to 158 (M5 itself fell from
  108 to 94). Exact failure ODB and marker hashes are preserved in
  `cloud-reserved-m5-route-failure-20261013.json`; use congestion probe
  profile `reserved_m5` to diagnose it. Broader placement run `38334595459`
  is diagnostic.
  Inspect the live outcomes; do not cancel healthy jobs based on age.
- Combined via-array loaded tree `38360782776`: compact control passed; wire
  case rejected with 69 wrong signs, all 128 early samples below 100 mV, and
  six HBT minimum-VCE failures. All interface amplitude/common-mode gates
  passed. Original bits, sample phases and limits remain unchanged.
- Dense final MUX: native physical run `38362060912` passed DRC, strict LVS and
  five fault controls. Native extraction `38362407566` passed graph checks and
  13 corruption controls, producing **2875 R / 1986 C**. Exact composition
  `38364385250` passed, retaining 54 native devices. Loaded-tree run `38365522474` completed: compact passed; wire rejected.
  Wrong signs fell to zero, but 128 early samples remain below 100 mV
  (minimum 4.927 mV), and four HBT minimum-VCE gates fail. Both interface
  gates pass. The candidate is not adopted.
- Use `tx-tree-physical-cloud.yml` with `streams=4`,
  `physical_profile=power_trunks_vias`, `physical_final=matched`,
  `physical_final_profile=kelvin_dense`. Discover an existing run before
  dispatching. Run `38365522474` is the completed nominal comparison; do
  not duplicate it. Each compact/wire job publishes complete immutable captures.

Persist meaningful source fixes and evidence to the same branch; use release
assets for large results. Do not download bulk CAD results onto this computer.
