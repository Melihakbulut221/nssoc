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

## Retime passive leaf candidate and retained device-gate improvement

The retime-drive-v2 physical candidate now implements all four resistor widths
at4um and both MIM dimensions at7.2x7.2um. The two matching retime instances
are checked from the same parent source; other filter families remain unchanged.
The native12-device leaf campaign retains the original five faults and adds
rejection of the old resistor width and old MIM dimensions.

Separately, full data-cm-v9 wave campaign39207756405 completed. Both nominal
cases pass every original transistor voltage/current gate with no native
diagnostics. The original sampler error counts remain unchanged: early
A/B/C/D=121/311/358/396; late=251/128/377/372. Overall data/phase acceptance
therefore remains rejected. Clock-stopped and V/I-bias-off faults are detected.
The new input-drive parent must retain the proven2.4um data header repair.

The0.4V minimum-VCE screen remains a project headroom criterion. IHP public
[process-control BJT tables](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/03_bjt_params.html)
list breakdown and current process parameters; they do not make this complete
project screen a foundry reliability approval. The
[IHP stress study](https://www.iee.et.tu-dresden.de/iee/eb/forsch/AK-Bipo/2021/6_Fischer_IHP_AKB2021_MaximumTolerableCurrentDensityHBT.pdf)
also distinguishes voltage/current operating regions and self-heating limits.
Neither source is used to relax any current gate or claim qualified lifetime.


## Input-drive physical checker repair

Run 39209252154 stopped before native LVS/DRC: the IN resistor layer-28 region reported cached area 15840000 but an empty bounding box and polygon iterator after independent PCell registration. This is not accepted physical evidence. The complete rejected result remains in release cloud-results-39209252154-1-cdr-sampler-input-drive-physical.

The checker now freezes every primitive region with `flatten()` before merging and checks candidate polygon/bounding-box/area identity again after golden PCell generation. Exact XOR comparison and all original physical/fault gates remain. This addresses an original-layer view lifetime hypothesis; a fresh cloud run must validate the repair and actual geometry. KLayout's maintainer documents original-layer views and explicit freezing here: https://www.klayout.de/forum/discussion/2659/value-of-begin-shapes-rec-variable-changes-if-new-shapes-added-to-cell . No local CAD or output files are created.
