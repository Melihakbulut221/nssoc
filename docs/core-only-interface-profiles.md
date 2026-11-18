# Complementary interface-profile qualification

The retained cocotb regression defaults to base. Its six SpaceWire/CAN cases are explicitly skipped, so that job alone does not qualify the retained production interfaces. This companion runs the unchanged pin-level APB suite with both authenticated base and full bundles.

The current suite has 14 named cases. Base must pass eight and skip exactly the six named SpaceWire/CAN cases. Full must pass thirteen including all six, and skip only the disabled-slot error test, which base exercises. The union must pass all fourteen; no extra failure, missing test, new skip or modified tracked source can pass this qualification. Source hashes, prepared interface manifests, simulation commands, native XML and logs are retained. Skipped cases remain visible in each individual profile and are not relabeled passed there.

This tests I2C, SPI, SpaceWire and CAN protocol behavior at APB/pins. It does not replace native core-only boot, CPU interrupt integration, routed timing, pad electrical verification or physical signoff. PCIe/Ethernet remain outside release scope.
