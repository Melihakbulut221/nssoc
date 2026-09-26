# 98 — Portable physical-tool entry points
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

This closes a host-path assumption, not physical acceptance. Historical layouts
used custom per-tool shims and LibreLane 3.0.5. A version-equal LibreLane package
can contain different OpenROAD, STA, Yosys or other dependencies; every new
physical result therefore needs a fresh tool identity and acceptance record.
The frozen pilot flow is unchanged.

## 1. Checksum-pinned devshell

The [official 3.0.5 release](https://github.com/librelane/librelane/releases/tag/3.0.5)
provides Linux x86-64 and AArch64 AppImages. The installer pins both byte counts
and upstream asset SHA256 digests. It does not execute a downloaded file,
replace an existing target, change the shell or install system packages.

```sh
python3 scripts/bootstrap_flow.py
python3 scripts/bootstrap_flow.py --check
# Offline source, subject to exactly the same byte-count and SHA256 checks:
python3 scripts/bootstrap_flow.py --archive /path/to/librelane-devshell-x86_64.AppImage
```

The default destination is `hw/soc/tools/physical/` inside this checkout. These
ignored files are not published as source assets. Free-space checks precede
network access; a truncated, oversized or modified download cannot be installed.
The image alone needs about 1.40 GB on x86-64; full PDK and run storage are
additional. The tested installer controls do not imply a completed download or
a smoke-test pass on this workstation.

Follow the release's [AppImage instructions](https://github.com/librelane/librelane/blob/3.0.5/docs/source/installation/appimage_installation/installation_linux.md)
for host prerequisites and entering the environment. Inside that devshell:

```sh
librelane --smoke-test
export FLOW_TOOL_MODE=environment
export PDK_ROOT="$PWD/hw/soc/tools/pdk"
```

The repository's physical flow then selects `python3`, `librelane` and
`openroad` from this explicitly selected environment. It does not infer that
an arbitrary ambient shell is the devshell. Explicit `FLOW_PY`, `LIBRELANE`
and `FLOW_OPENROAD` overrides remain available. PDK installation/enablement
must use the **full** IHP kit at the hash in this LibreLane's
`pdk_hashes.yaml`; the native-boot model subset is not a physical PDK.
`pnr_soc_top.sh` still checks the enabled Ciel hash against that package pin.
Full-kit bootstrap and an independently reproduced physical run remain open.

## 2. Existing explicit tool installations

Default `FLOW_TOOL_MODE=project` resolves tools only to project-local paths:

| Variable | Default within this repository |
|---|---|
| `SHIMS` | `hw/soc/tools/physical/bin` |
| `VENV` | `hw/soc/tools/flow-venv` |
| `OSS_CAD` | `hw/soc/tools/oss-cad-suite/bin` (or explicit `OSS_CAD_SUITE/bin`) |
| `FLOW_PY` | selected `VENV/bin/python` |
| `LIBRELANE` | selected `VENV/bin/librelane` |
| `FLOW_OPENROAD` | selected `SHIMS/openroad` |
| `PDK_ROOT` | `hw/soc/tools/pdk` |

Existing custom installations must be supplied explicitly using these variables.
No other project directory or host home-directory shim is an implicit fallback.
Per-tool wrappers must contain their own library configuration; an inherited
`LD_LIBRARY_PATH` is cleared so that OpenROAD's runtime libraries cannot leak
into host utilities. `scripts/ci_local.sh` also defaults its optional checker
interpreter to the project-local flow environment. A missing installation is
an explicit skip in that optional checker, not a physical verification pass.

## 3. Validation boundary

Installer fixtures check digest/size failures, truncated and oversized downloads,
lock/target preservation, insufficient disk space and atomic no-clobber install.
Shell controls verify project paths from a different working directory, paths
with spaces, explicit overrides, environment opt-in and missing tools. They do
not run placement/routing, establish AppImage host compatibility or reproduce
historical timing. The complete physical acceptance obligations remain docs/92.

## 4. Independent devshell / IHP integration job

The `physical-tools` workflow uses a fresh Ubuntu 22.04 runner, verifies the
same x86-64 AppImage and executes `scripts/check_flow_smoke.py` inside it.
The script requires LibreLane 3.0.5 and the physical tool executables, records
their identities, installs the full IHP PDK at the package's exact pin into a
fresh project directory, then runs the upstream `spm` example with IHP. It
retains the flow directory instead of using the upstream smoke command that
deletes its outputs. This follows the upstream release's
[AppImage command invocation](https://github.com/librelane/librelane/blob/3.0.5/.github/workflows/ci.yml).

```sh
# Run only after the checksum check above and with enough free PDK/run storage.
hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage python3 scripts/check_flow_smoke.py
```

Existing output/PDK paths are refused. Nonzero commands, a wrong enabled PDK,
or absent/empty final GDS, DEF or netlist views fail the check. JSON/log receipts
survive both success and failure. CI uploads those diagnostics and view hashes;
it does not copy the PDK into Git. The workflow runs when its installer/runner
changes, with a separate concurrency group from long SoC native/formal jobs.

The runner's twelve failure-path fixtures and the sixteen installer/environment
controls pass locally. Those fixtures do not download the image or run a real
physical flow. Hosted installation/SPM acceptance is pending until its actual
receipt is collected. Even a passing SPM flow would cover this tool/PDK example,
not SoC timing/LVS, the frozen pilot, or another host architecture.

**Measured update, 21 September 2026:** the independent
[hosted run](https://github.com/Melihakbulut221/nssoc/actions/runs/35552817322)
at `6de8170` passed the actual verified download, full IHP installation and
retained SPM flow. The package pin is
`c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`. Its 420-standard-cell example has
zero final route, Magic, KLayout, XOR and LVS error counts. Setup slack is
5.897 ns and hold slack 0.340 ns in that example's own constraints. The
[receipt](evidence/physical-tool-bootstrap-20260921.json) binds the driver,
commands, tools, logs, metrics and final view hashes to the hosted revision.

The bundled Yosys is 0.62, Magic is 8.3.623 and KLayout is 0.30.7; OpenROAD
identifies commit `dcf36133a369abc8f3c5e5738cd4d82e4903c0e0`.
These differ from the historical custom flow tools. They are now explicit
reproducibility inputs, not evidence of equivalent SoC results. The example
also leaves its wire-length threshold unset and lacks top-level voltage-source
locations; its router reports unsupported LEF58 enclosure clauses. Those
warnings are retained. This does not close SoC, SRAM-interior, package or
supply qualification. The workstation's disk-space refusal still stands.

## 5. Current SoC implementation entrypoint

`implement_interfaces.sh` now builds the loader afresh and explicitly selects
logic ROM, WAKE_GNT=1, protected RAM/ROM, SYNPRE=1, MEM_RDREG=1, REQ_REG=1,
clock gating, the 256-cycle APB timeout and 256-word Ethernet SRAM banks. This
corrects its obsolete WAKE_GNT=0 / SRAM-ROM reproduction profile. Standalone
synthesis defaults and historical configs remain unchanged.

```sh
# After make soc-prepare and full-kit installation; inside the devshell:
export FLOW_TOOL_MODE=environment
export PDK_ROOT="$PWD/hw/soc/tools/pdk-bootstrap"
SOC_INTERFACE_PROFILE=full bash hw/soc/flow/implement_interfaces.sh unique-tag
# Compile and map without claiming placement or routing:
SOC_INTERFACE_PROFILE=full bash hw/soc/flow/implement_interfaces.sh another-tag --synthesis-only
```

The selected `base`/`full` interface policy remains explicit. Each unique output
contains `firmware/`, `boot-rom-reference/`, `synthesis/`, logs and `inputs.json`.
Synthesis owns and replaces only its own child directory. The flow compares
its generated ROM against the reference, checks listed source hashes after
mapping, and selects the floorplan from the actual SRAM instance inventory.
An explicit incompatible `PNR_CONFIG`, changed loader or changed source fails
before placement. Existing output directories are refused, and failure logs
remain available. Additional LibreLane arguments follow the tag.

The separate `soc-physical` workflow installs the verified digital/physical
toolchains and complete PDK on a fresh runner, retains the upstream control,
then runs this entrypoint for the full-interface core. Its 330-minute job budget
and retained reports are execution limits, not passing verdicts. A configured
workflow alone does not close SoC reproduction. A successful core flow also
still needs the independent DRC, SRAM-interior LVS, electrical/timing, pad,
package and qualification gates in docs/92; the existing core config does not
automatically run every independent deck.

The [22 September local measurement](evidence/current-implementation-entry-20260922.json)
passes actual full-profile mapping on Yosys 0.67+146: 68,534 cells, 9,459
flip-flops and twenty SRAM macros (four RAM, sixteen Ethernet, zero boot-ROM
macros). The loader and generated ROM identities match across the handoff;
all inventoried source hashes remain unchanged. There are 191 unique synthesis
warnings / 199 occurrences, retained in the record. Eighty-four flow/profile
checks pass, including six new end-to-end shell handoff/failure controls.
This measurement deliberately stops before placement.
