# Core-only whole-SoC lint

The historical lint runner called resolve(interface_profile) directly and did not apply release_define, so SOC_RELEASE_PROFILE=core-only did not select SOC_NO_ETH. This change adds an explicit --release-profile (defaulting to the existing environment) and uses the same hardware release guard as the simulation/synthesis flow. Legacy profile keys remain unchanged. Core-only forbids Ethernet MBIST and contradictory PCIe/Ethernet environment selections.

Core-only has separate warning-ledger keys, such as full-core-only and full-sram-logic-mbist-core-only. A missing ledger is a failure after saving actual native diagnostics; it never accepts an empty/generated policy implicitly. Existing diagnostic classes, owned-warning review, immutable hashes, exact line/message/multiplicity comparison and frozen no-implicit-net compilation remain active. New warnings must be reviewed against native evidence before policy entries can be added.

The first cloud run compiles the full retained interfaces with array memory, MEM_RDREG=1/REQ_REG=1, explicitly SOC_NO_ETH. This does not cover physical SRAM/logic-ROM/SYNPRE or MBIST lint until those exact profiles are separately measured. It is not mapped, timing, CDC, padframe or production acceptance.
