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
