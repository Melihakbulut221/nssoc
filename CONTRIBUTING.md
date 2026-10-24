# Contributing
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

Start with a reproducible [issue](https://github.com/Melihakbulut221/nssoc/issues).
Include the exact commit, interface profile (`base` or `full`), command, tool
versions, expected result and the smallest failing log or input. A skipped
tool-dependent test is not a pass. Use [SECURITY.md](SECURITY.md) for sensitive
reports and observe the [code of conduct](CODE_OF_CONDUCT.md).

## Publication and contribution boundary

This repository publishes a subset of a private development tree. Historical
commit references in the documents can identify revisions absent from this
mirror; see the [mirror contract](docs/78-the-public-mirror.md). A public issue
or pull request does not automatically enter the private upstream tree.

The [signed licence decision](docs/14-licensing-decision.md), section 10,
requires a contributor agreement or matching grant before accepting third-party
source into the dual-licensed tree. No such agreement is supplied here. Discuss
an intended source contribution with the owner before submitting it; opening a
pull request does not transfer copyright or grant additional rights. Retain
component notices and do not relabel fetched code. Reports, reproductions and
review feedback can be submitted without proposing a source merge.

The pilot RTL, testbenches, root formal tree and generated TinyTapeout submission
are frozen under [docs/34](docs/34-pilot-freeze.md). Do not reformat or regenerate
those files as a side effect of SoC work. Preserve superseded measurements and
append dated corrections with their actual scope.

## Development checks

Follow [README.md](README.md) for the two simulation/Python environments and
explicit IP preparation. For the optional development tools, use Python 3.12:

```sh
python3.12 -m venv hw/soc/tools/dev-env
hw/soc/tools/dev-env/bin/python -m pip install -r sw/requirements-dev.txt
hw/soc/tools/dev-env/bin/ruff check sw
hw/soc/tools/dev-env/bin/mypy
hw/soc/tools/dev-env/bin/pre-commit run --all-files
```

Ruff checks fatal syntax/name errors across `sw/`; mypy checks golden models
and the transport library, with complete function annotations required for
the handwritten golden models. Neither command replaces runtime tests. The
MicroPython-only `time.sleep_us` import has one documented platform exception.
Generated register definitions must be regenerated from their YAML sources.

`pre-commit install` is an explicit local choice. Hooks check Python, SPDX and
register generation without changing files. The manual `soc-verilator` hook
runs the existing whole-SoC diagnostic gate and requires prepared dependencies:

```sh
make soc-rtl-prepare
hw/soc/tools/dev-env/bin/pre-commit run --hook-stage manual soc-verilator --all-files
```

Set `SOC_INTERFACE_PROFILE=full` consistently to verify optional LGPL interfaces.
Each lint run retains a new evidence directory; it does not overwrite earlier
results. The hook fails if tools or prepared sources are missing.

Run tests relevant to the change, then `make check`. Report commands and real
pass/fail/skip counts in the pull request. Physical source changes also need
their profile-specific RTL/synthesis checks and physical acceptance evidence;
a lint pass is not timing, DRC or LVS closure. Do not commit local checkpoints,
ignored tool installs, credentials or host-specific output trees.
