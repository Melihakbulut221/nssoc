# Exact codec source nettype integration

The real generic CI run40099402814 rejected two unguarded Chuck Benz derivatives. They are actual synthesized DUT modules, not simulation-only references. The independent published IEEE table remains the codec test oracle.

This change preserves every upstream, derivative, wrapper, testbench and codec-oracle byte that passed corrected native run40102483214 and authenticated reader40106066552. It registers only the two exact derivative hashes in the existing frozen-pcie-nettypes.json mechanism, preserving all34 prior entries. Every registered file is parsed by the mandatory external default_nettype none wrapper with Yosys -noautowire. Hash drift, any in-file nettype override, unregistered unguarded sources and a missing compiler still fail. There is no wildcard vendor exemption.

The targeted GitHub job runs all original SoC lint and frozen-source tests plus exact provenance checks and two mutations of actual codec source: removing the real ai declaration while keeping its assignment/use. Each mutation has a correctly rebound temporary fixture hash so actual compiler rejection, not stale provenance, is required. It requires31 tests with zero failures, errors or skips and all36 real guarded sources. Tests execute only on the hosted runner; original source hashes are checked before and after.

The original CI rejection is preserved in the evidence receipt. This source preparation is not a targeted lint pass, a rerun of whole-SoC lint, a codec functional rerun, or full PHY acceptance. The exact lint result is pending.
