# Core-only whole-SoC lint

The historical lint runner called resolve(interface_profile) directly and did not apply release_define, so SOC_RELEASE_PROFILE=core-only did not select SOC_NO_ETH. This change adds an explicit --release-profile (defaulting to the existing environment) and uses the same hardware release guard as the simulation/synthesis flow. Legacy profile keys remain unchanged. Core-only forbids Ethernet MBIST and contradictory PCIe/Ethernet environment selections.

Core-only has separate warning-ledger keys, such as full-core-only and full-sram-logic-mbist-core-only. A missing ledger is a failure after saving actual native diagnostics; it never accepts an empty/generated policy implicitly. Existing diagnostic classes, owned-warning review, immutable hashes, exact line/message/multiplicity comparison and frozen no-implicit-net compilation remain active. New warnings must be reviewed against native evidence before policy entries can be added.

The first cloud run compiles the full retained interfaces with array memory, MEM_RDREG=1/REQ_REG=1, explicitly SOC_NO_ETH. This does not cover physical SRAM/logic-ROM/SYNPRE or MBIST lint until those exact profiles are separately measured. It is not mapped, timing, CDC, padframe or production acceptance.

## First native warning review

Run44248832076 compiled successfully (Verilator return0, source hashes unchanged, no owned unaccepted warning, no immutable drift) but correctly failed the absent full-core-only policy. Its exact diagnostics are a subset of the existing full profile: no new diagnostic code/path/line/column/message/multiplicity;197 warnings removed. The new policy copies only this measured subset, preserves all other profiles and does not suppress warning classes. Evidence is in evidence/core-only-lint-array-review-20261118.json. A fresh native rerun must pass before acceptance.

The next workflow also restores only the authenticated mapping producer's compiled loader bytes (SHA256 ab7440619ca719358e6598b0cf291a268c8ccf13357b50ef3a89cbe583e71801), then compiles the full-sram-logic-mbist-core-only profile. That profile has no ledger yet and must fail pending native review. No native boot or SRAM transistor qualification is implied.
