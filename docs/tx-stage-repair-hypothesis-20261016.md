# Source-bound final-selector and driver-series hypotheses

Native tree binding inventory38937012080 restores the exact original binding
SHAf54124fa051b49a32f0c3837ef8f771e6cda3ea9aba18417ba5cc932e856c3b9.
XD0001 and XD0003 both have C=$I50,B=sn,E=$I54,body=$4,Nx6. XD0002/4
use B=sp and C=$I51; both pairs share the final tail node driven by the two
Nx8 tail HBTs whose bases are mr. These are the final2:1 clock selectors,
not the first stage. The previous checkpoint's first-stage wording is corrected.
Native IDs alone were insufficient to establish a stage role.

Two bounded schematic hypotheses follow, starting from the actual fresh-RC
l2p4 physical driver model8eec4846d8cef0e3367c07f8e1a0f3413f4a628684bbb1a283c6f6883b95ad79:

- Driver XD86/XIN length6.92um to6.2um at unchanged width2um tests stronger
  differential drive into the physical tree. It may hurt common-mode or device
  stress. All other raw99devices and all260R295C remain unchanged.
- Native clock-reference XOFFSET length6.5um to6.2um at unchanged width4um
  tests lower reference common-mode and more final-selector VCE headroom.
  The native resistor feed, reference HBT, clock phase/amplitude and full
  waveform gates stay unchanged. No ideal offset source is introduced.

The helper proves exact source identity and rejects changed gate damping,
wire resistance, clock HBT or missing offset resistance. These are proposed
parameter sensitivities, not a passing circuit or layout. First inspect the
active actual l2p4 loaded run38936139904; use its complete source-bound result
as the baseline for separate series/clock/combined experiments. Do not change
healthy runs or repeat the previously rejected data8_select10 sizing study
38773059353. Every original34ns/256bits/672MOS/62HBT/zeroOP/source phase and
engineering limit remains required; a useful outcome needs new matching
physical geometry/extraction and PVT validation.
