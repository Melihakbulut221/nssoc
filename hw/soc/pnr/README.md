# SoC physical profiles
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

No profile here constitutes a qualified final chip. Acceptance belongs to a
specific netlist, PDK, toolchain, constraints, routed image and its check results;
see [the product gates](../../../docs/92-product-acceptance.md).

`flow/pnr_soc_top.sh` selects a profile by the **actual mapped SRAM inventory**
in `SYN_NETLIST`. The default search covers the profiles below. An explicit
`PNR_CONFIG` must also match every macro name and master, and the selected
`SOC_BOOT_ROM` implementation. Missing, extra or mismatched macros fail before
launching LibreLane. This prevents the former six-macro unprotected default
from being applied silently to an ECC or Ethernet netlist.

```sh
python3 hw/soc/flow/select_pnr_profile.py \
  --netlist /path/to/soc_top.netlist.v --directory hw/soc/pnr --rom logic
```

| Profile | Placed SRAMs | Scope |
|---|---:|---|
| `config-interfaces-logicrom.json` | 20 | ECC RAM, packet SRAMs and immutable logic ROM; current physical candidate family |
| `config-interfaces-synpre.json` | 24 | ECC RAM/ROM and packet SRAMs, before the logic-ROM migration |
| `config-interfaces.json` | 8 | ECC RAM/ROM; Ethernet packet storage is not placed as SRAM macros |
| `config-ecc-rom.json` | 8 | Historical protected RAM and protected SRAM ROM floorplan |
| `config-ecc.json` | 6 | Historical protected RAM and unprotected SRAM ROM |
| `config.json` | 6 | Historical unprotected RAM/ROM baseline; never a generic hardened default |
| `config-npu.json`, `config-synpre.json` | 6 | Historical NPU inclusion / mapping experiments |
| `config-timing*.json` | 6 | Historical timing and electrical experiments |
| `config-lvs-a*` through `config-lvs-f*` | 6 | Diagnostic LVS experiments; their rule changes are not product waivers |
| `config-lvs-ecc-rom.json` | 8 | Historical ECC macro LVS experiment; not successful SRAM-interior LVS |

Files named `config-fp*.json` and `config.resolved.*.json` are ignored generated
experiments and per-run source-list snapshots. The explicitly tracked ECC and
interface profiles remain versioned inputs even if their floorplan began with
a generator. Preserve all historical configs while their recorded evidence
depends on them; do not rename a diagnostic config to imply signoff.

The selector verifies only macro inventory and ROM profile. It does not prove
placement legality, complete parameter equivalence, SDC correctness, timing,
DRC, LVS, power integrity or package integration. The current SRAM activity
path below migrates the inventory; historical energy values remain tied to
their original six-macro profile.

## SRAM activity inventory

Use `flow/macro_activity.py` and `flow/macro_energy.py --netlist` for current
macro inventories; the old fixed six-instance calculation requires explicit
`--legacy-six-macros`. The new path requires every ECC/packet macro and both
ports of each dual-port SRAM. See [the dated power correction](../../../docs/57-power-under-a-duty-cycle.md)
for commands, clock sampling rules and the limited energy components priced.
A separate `flow/check_macro_activity.py` native-model calibration checks the
reader with an inventory and independent A/B clocks; it is not a SoC workload
power measurement.

## Recoverable physical runs

The first hosted `current-full` attempt hit its 330-minute job limit in
post-GRT setup repair; its artifact omitted the actual ODB/DEF views. See the
[source-bound failure record](../../../docs/evidence/current-physical-timeout-20260922.json).
The workflow now limits the implementation step to 300 minutes, leaving time
for checkpoint collection within the job budget. Post-GRT setup search uses
100 iterations; post-CTS keeps 600. This bounds optimization effort, not
acceptance: timing, derating, electrical and physical-verification criteria
remain unchanged. The shorter search may leave violations that need another
repair; a completed flow is not automatically a passing product.

```sh
python3 scripts/collect_physical_checkpoint.py capture \
  --run hw/soc/pnr/runs/current-full --out hw/soc/out/current-full-checkpoint
# After downloading the checkpoint directory to a new machine:
python3 scripts/collect_physical_checkpoint.py restore \
  --bundle /absolute/path/to/current-full-checkpoint
```

Capture selects the last completed top-level step and includes every file
referenced by its state, with hashes and relative paths. Missing or external
views, an invalid latest state and changed inputs fail explicitly; no older
state is silently substituted. Restore verifies the files and writes
`state.local.json` with paths for its current location. Existing outputs are
never overwritten. Use that state as the input to the appropriate next flow
step with the matching pinned tools, PDK and configuration. This does not
reconstruct an interrupted optimizer's uncommitted in-memory changes, and
the older incomplete artifact cannot supply missing views retroactively.


The retry reached detailed routing, including three intermediate passes with
zero router DRC violations, but timed out in antenna repair iteration 3.
The last antenna check still had 11 net / 12 pin violations. Its
[pinned archive receipt](../../../docs/evidence/physical-route-checkpoint-20260922.json)
identifies the completed pre-route state and ten verified physical views.
`scripts/resume_physical.py` validates the entire archive, all 138 prepared
source/configuration hashes, boot image, mapped netlist and checkpoint hashes.
It restores the original resolved configuration (including native `5.0`
derating) beside the original design directory. The dedicated
`soc-physical-resume` workflow starts at `OpenROAD.DetailedRouting` with the
same pinned runtime and PDK. No synthesis or placement is repeated.

```sh
python3 scripts/resume_physical.py --archive /absolute/path/to/source.zip --verify-only
```

Omit `--verify-only` only in a freshly prepared checkout with space for the
restart views. The restore itself does not start the physical tools. The flow
retains the existing configuration's disabled built-in foundry DRC/LVS steps;
independent foundry deck checks and SRAM-interior LVS remain separate open
acceptance requirements. Intermediate router DRC is not foundry signoff.
