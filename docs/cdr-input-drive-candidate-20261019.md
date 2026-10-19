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


## Verified leaves and new parent integration

Sampler run39210361374 at3516bc984adc46b99ae5cc501bac861dec5db647 passed exact native drawing comparison with three corruption controls,560-category DRC,unsimplified deep/flat54deviceLVS and16physical fault controls. Retime run39209600711 at37ef8347e55818db81ccffd37b68e01ac8ec52bf passed560-category DRC,unsimplified deep/flat12deviceLVS and7physical fault controls. Full reports and SHA256-bound receipts accompany the child manifest. Neither leaf result is electrical/fullPHY acceptance.

The input-drive-v10 parent substitutes only these two leaf types in the16macro/484device/25port hierarchy, preserving the measured2.4um data-header repair and six other leaf types. It reruns original native physical gates plus explicit rejection of rolled-back16sampler resistor widths,8retime resistor widths and4retime MIM dimensions. Fresh full-parent wire/MIM extraction and original loaded nominal/fault simulations remain mandatory. All computation runs on GitHub-hosted runners; local workspace remains empty.


## Whole-parent native physical pass and hosted extraction chain

Parent run39211268312 passed at6022f4da7d52df977974e2cbf894bd59a54a53a3:560-category DRC, unsimplified deep/flat484device transistor LVS and all9 physical corruption controls. The original data-header rollback control and three new input/retime rollback controls all reject. The receipt stores the complete report and immutable release digests.

The hosted extraction workflow now runs planes, then wire inputs, then independent model-binding and raw wire-RC jobs. Each dependent job reads the exact same-run published summary/parts manifest, binds the source SHA, and delegates archive integrity checks to the original restore methods. Original158plane/1394terminal geometry checks,12model controls and13raw-RC controls are retained. Failures stop dependent work and preserve raw outputs. Full MIM-aware extraction, loaded sampling and phase/device tests still follow; neither physical success nor wire-only RC means completePHY acceptance.


## Fresh extraction and model binding

The hosted chain39212026475 at9037bd2010e204d1949a5ad2db2ec9201fb2f3bd passed all four stages:158native reference planes and19fault controls, whole484device/1394terminal graph with946actual anchors, native compact-model binding, and wire-only RC with13raw corruption controls. The exact full reports and release digests are committed. The next workflow captures actual11MIM masks and dimensions together with the new complete wire graph; the original MIM terminal and device ownership checks are unchanged. This remains unqualified for substrate/RF extraction or electrical/fullPHY acceptance.

Measured wire-only R/C census: 15459 resistors, 11516 capacitors. These are extraction counts, not timing or signal-quality pass criteria.
