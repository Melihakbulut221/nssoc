# CDR v30 physical integration and fresh extraction

The real 476-device parent from run [39706018326](https://github.com/Melihakbulut221/nssoc/actions/runs/39706018326), source 3e02237b3bc8cf1e6f4e83ad4bb105c680675204, passes native DRC and both unsimplified deep and flat LVS. Both LVS comparisons contain 476 layout and schematic devices with Match and no extraction diagnostics. All original physical fault controls remain active. The eight same-component Metal4 fills add exactly 0.392 square micrometers, preserve all 899 components, and create no new Via3/Via4 contacts.

GDS SHA256: 49914cacf6d66660c7e0373c8a60ce59e0b389c5c86b538daa54a2062324ea42. The complete native report and immutable archive pins are in the accompanying physical-pass receipt. These are physical integration results for the phase-detector parent, not serial PHY acceptance or mainchip integration.

The new cloud extraction chain uses this exact GDS and native flat LVS database. Planes, wire graph, terminal binding and raw wire RC are remeasured. Native measurement bodies, 476-device/1382-terminal coverage, strict 111-component checks, physical point ownership, all 26 receipt corruptions and the original binding/RC negative controls remain active. No previous wire RC is relabeled as v30. The 16 resistor changes and the eight new fill coordinates are explicitly bound in the source validator.

After extraction succeeds, intrinsic MIM plates must be audited and composed once, then the original loaded 34.25 ns, 256-bit, 1104-column full-wave tests must run with the same clocks, loads and electrical thresholds. Qualified PEX, closed-loop behavior, full serial PHY and final mainchip timing remain unaccepted.
