# Complementary interface-profile qualification

The retained cocotb regression defaults to base. Its six SpaceWire/CAN cases are explicitly skipped, so that job alone does not qualify the retained production interfaces. This companion runs the unchanged pin-level APB suite with both authenticated base and full bundles.

The current suite has 14 named cases. Base must pass eight and skip exactly the six named SpaceWire/CAN cases. Full must pass thirteen including all six, and skip only the disabled-slot error test, which base exercises. The union must pass all fourteen; no extra failure, missing test, new skip or modified tracked source can pass this qualification. Source hashes, prepared interface manifests, simulation commands, native XML and logs are retained. Skipped cases remain visible in each individual profile and are not relabeled passed there.

This tests I2C, SPI, SpaceWire and CAN protocol behavior at APB/pins. It does not replace native core-only boot, CPU interrupt integration, routed timing, pad electrical verification or physical signoff. PCIe/Ethernet remain outside release scope.

## Verified cloud result, 18 November 2026

[Run44247358676](https://github.com/Melihakbulut221/nssoc/actions/runs/44247358676) succeeded at source97ffca0ad84ab2bf103f6647e0a11ea4008fb7d4. Artifact14401534424 SHA256 d258566a1676f065cadfcb87e161690bb76669cff5ab01321a5d9d64b20c9578 and all10 inner output hashes were independently verified. Native XML matches the recorded exact case sets: base8 passed/6 expected skips, full13 passed/1 expected skip, zero failures, union14 passed. All six CAN/SpaceWire cases passed in full. Source hashes were unchanged. This closes the complementary pin/APB RTL case coverage for this exact source, not netlist, physical, external link or production qualification. Full result is in evidence/core-only-interface-profiles-20261118.json.
