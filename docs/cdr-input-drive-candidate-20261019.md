# Physical input-drive repair candidate

The fixed-phase native input summary39208135958 shows acquisition failure
already at the master data-pair bases. At the original nominal late A edge,
95/255 inputs have the wrong sign; even0.1UI later69 remain wrong. At nominal
early B,129/255 inputs have the wrong sign at the original edge. Retimed C/D
input margins are also small. These are descriptive samples, not new gates.

The sampler already uses fourfold HBT and load drive, while the four input
divider resistors retain their original1um widths. This candidate changes only
IP/IN/BP/BN to4um width at unchanged lengths, preserving the nominal divider
ratio while reducing source impedance. This is a design hypothesis, not a
measured improvement. Native parasitics, contact resistance and actual input
loading remain mandatory in the eventual full-parent test.

A separate retime-network adaptation is required before parent integration:
scale the four passive resistors per retime leaf to4um width and its two MIM
capacitors from3.6x3.6um to7.2x7.2um. This follows the original fourfold drive
intent; no behavioral gain, sample shift or slower clock will substitute for
physical checks and the original loaded gates.

The first hosted job independently compares50 unchanged primitive drawings
and four rebuilt native resistor PCells, then runs560-rule DRC, deep/flat
54-device LVS, native LEF and all14 prior faults plus two old-width faults.
Earlier standalone electrical screens are retained only as baseline ancestry.
This modified candidate has no electrical acceptance yet. Full PHY, CDR loop
and chip setup/hold closure remain open.
