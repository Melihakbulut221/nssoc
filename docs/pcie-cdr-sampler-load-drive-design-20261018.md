# Native sampler load-drive candidate v2

This is an unaccepted component experiment toward the full8GT/s serial PHY. No mainchip macro is replaced by this source. All work executes on GitHub-hosted runners.

## Measured reason

Whole physical PD420 run39119999874 failed original sampling gates and early-phase direction. Read-only run39121253725 reproduced the actual wave failures; the receipt cdr-hybrid-v2-native-path-review-20261018.json pins both native reports and original captures. The retimed input pairs are strongly attenuated. Incident extracted wire capacitance reaches0.748pF on aqn and0.702pF on aqp; these sums include coupling and are NOT equivalent grounded output loads. Nominal HBT/MOS safety passing did not establish valid data or CDR operation.

## Explicit component change

Keep12HBT instances,3nativeLVNMOS and12rppd topology. Scale each HBT emitter multiplicity4x (data/hold2→8, clock4→16; totalNx32→128), tail width32→128um at0.3um length, and collector resistor width8→32um with length2.12um unchanged. Reference stays8um/0.3um and500uA: nominal mirror ratio4→16. Intent is more output current at approximately retained static swing and current per emitter; this is a design hypothesis, not measured success. Increased input/clock capacitance, resistor parasitics, power, startup and supply droop can defeat it. No ideal gain or latch is added. Input level-shift resistors remain unchanged so this experiment does not claim to solve the separate retimed-interface attenuation.

## Unchanged acceptance and harder load

Use1pF grounded at each output as an explicit stress experiment, instead of the old standalone150fF. It is not substituted for the distributed parent network. Preserve256PRBS source bits,34.25ns trajectory,0.3125ps maximum step,10ohm data/clock sources, original clock phase,100mV minimum data margin and37.5ps clock-to-valid limit. Preserve every startup, native OFF flag, transistor terminal/current and source-immutability gate. Run nominal/hot_low/cold_high and actual swapped-output/stopped-clock negative controls. A detected fault does not establish transistor safety under that fault. Exact source/controller delta guards retain the old guard chain and acceptance expressions.

All results and failures are published. Before any integration, require measured outcomes, actual new geometry and DRC/LVS, fresh distributed extraction/model binding, full parent trajectory and complete CDR/PLL loop/corner verification. Final mainchip timing and fullPHY acceptance remain false.

## Actual first run rejected

Run39122483815 passed exact source/controller guards but all five cases failed native startup; no valid bit-error, delay or device-limit characterization was produced. Nominal simulator returned0 while its log reported temperature limiting NaN and transient timestep failure at50.063ps; the existing diagnostic gate correctly rejected it. Read-only cloud diagnosis restores original logs/decks and OP without weakening any gate or substituting a new waveform. See the pinned startup-rejection receipt.

## Native model domain correction: split-drive v3

Read-only diagnosis39123356324 restored exact archived HBT model SHAae9288f885dd30fab24b07ed1e7e02e69eac9154022a0a6da576985183b0bd79. It explicitly limits npn13G2 Nx to1..10 and defines Csub=2.30e-14-1.50e-15*Nx. The v2 clock devices atNx16 were outside this domain and produced negative1fF substrate capacitance. This is a design/model-domain error, not an acceptable simulator-warning waiver. Original failed trajectories (175nominal rows ending50.063ps) and all five original cases remain archived. The Latin1 text-display failure39123097913 is also retained.

The new v3 schematic replaces each Nx16 clock selector with two actual separate Nx8 transistors with shared electrical C/B/E/substrate nodes and separate native model internal/thermal nodes. It has16HBT instances (allNx8, totalNx128),3MOS and12rppd. No ideal model replacement or capacitance clipping is used. This differs physically from one Nx16 device; subsequent geometry must implement both real devices and re-extract parasitic/thermal coupling. Tail width128um, collector width32um,1pF output stress, all original timing/data/safety gates and five cases stay unchanged. The binder now rejects every out-of-domain HBT before simulation; actual source mutations Nx0/Nx11/Nx16 must all be rejected. No larger-driver acceptance until actual full-window wave gates pass.

## Measured split-drive v3 outcome and headroom v4

Run39123587911 completes all five full34.25ns native trajectories without diagnostics. Original768samples/corner all pass at1pF: nominal minimum133.867mV/30.781ps delay; hot_low110.864mV/35.469ps; cold_high148.205mV/27.969ps. Both actual fault controls are detected. Domain controls rejectNx0/11/16. This validates removal of the observed native startup failure, not fullPHY or physical integration.

The component is still REJECTED: master clock-select HBTs fall toVCE0.35355V nominal and0.31774V hot_low (limit0.4V). Four slave data/hold HBTs reach0.36908..0.37766V hot_low. Cold master input HBTs reach1.60934/1.61149V (limit1.6V). AllMOS gates pass. Negative fault detection does not waive these device failures. Exact receipt: cdr-sampler-split-drive-data-pass-device-rejection-20261018.json.

V4 changes only the actual input AVDD pullup rppd lengths3.6→2.4um (width1um). Input series resistors stay3.6um. Unloaded divider weight towardAVDD changes0.5→0.6, intended to raise master input common mode and reduce the cold maximum collector-emitter voltage while increasing master selector headroom. Reduced input differential gain and unchanged slave circuitry may retain or worsen failures; actual simulation decides. All1pF/clock/source/256bit/window/diagnostic/device/data gates remain unchanged. No new physical macro is accepted or integrated.

## Headroom v4 actual result

Run39123948513 passes full-window data at all three corners; nominal and cold now pass all retained device gates, and both actual faults are detected with device gates passing. No diagnostics remain. Hot_low is still rejected: slave DP/DN minimumVCE0.38608/0.38658V, slave LP/LN0.36935/0.36971V. All master and MOS checks pass. Data hot_low minimum110.576mV and35.469ps remain within the unchanged original gates. The next read-only native review reconstructs these four extrema and exact nearby terminal/current samples from the preserved full waveform before choosing a slave-emitter/headroom circuit repair. Do not lower the0.4V gate.

## Native extrema and slave-only bleed v5

Read-only39124255052 reproduces all four hot extrema from the original full waveform. Slave hold LP minimum occurs at33.87609375ns: collector2.150008V, emitter1.780662V, base2.374836V, VCE0.369346V, VBE0.594174V, collector current88.676uA, clockphase0.00875UI. Slave data DP minimum at33.81390625ns has VCE0.386082V, VBE0.603356V and91.724uA. These are low-current intervals around switching; the0.4V gate is preserved for them. Exact nearby native vectors and archive provenance are in cdr-sampler-headroom-native-extrema-20261018.json.

V5 keeps the master latch unchanged and explicitly duplicates its native subcircuit for the slave so only the slave SE/HE emitter bleeders change: rppd width1um/length38.4um→9.6um. The intended4x conductance discharges inactive slave emitter nodes faster and increases their VBE/headroom; extra loading, data margin, master/slave interaction and all device limits must be measured.16HBT/3MOS/12rppd counts and totalNx128 stay fixed. No behavioral clamp, source-phase change, model edit or relaxed gate. All five full-window cases rerun at1pF. Physical folded/parallel128um tail implementation and fresh DRC/LVS/RC/full-parent simulation remain future mandatory work.

## Actual v5 and balanced v6

Run39124621809 passes nominal/hot_low and both faults with no diagnostics; all three normal data tests pass. Hot slave data minimumVCE0.41926V and hold0.40415V now exceed0.4V. Cold remains rejected for exactly one HBT: slaveDP maximum|VBE|1.000106822V exceeds1V; no rounding or epsilon waiver is applied. Nominal margin145.156mV/delay29.531ps, hot118.112mV/34.219ps, cold162.101mV/26.719ps. Receipt cdr-sampler-bleed-cold-vbe-rejection-20261018.json retains all5cases.

V6 changes only slave DATA emitter bleeder length9.6→12.8um(width1um); HOLD bleeder stays9.6um to retain its smaller hot VCE margin. This reduces data-branch bleed strength from4x to3x baseline with more hot data headroom available. Master, input bias, native model, source boundaries, full-window waveform and device acceptance thresholds are unchanged. Three temperatures/supplies and actual faults must rerun. These screens still use the pinned nominalHBT model; full process/mismatch/jitter/qualifiedPEX/closed-loop validation is not established.

## Verified v6 component milestone

Run39125008269/source13e670e3b356924603e18e7cc4fd4e16d0ae4d7b passes all five native screens. Every normal condition has768correct samples, minimum100mV margin and maximum37.5ps delay limits met; all16HBT/3MOS retained device checks and clean zeroOP/startup/diagnostic/domain/source controls pass. Both actual faults are detected and their device checks also pass. Exact full reports, model/runtime/input hashes and native archive digests: cdr-sampler-balanced-native-pass-20261018.json.

Measured values (SI; full exact records retained):

```json
{
  "nominal": {
    "minimum_signed_margin_v": 0.14217847259138994,
    "maximum_clock_to_valid_s": 3.0156249999994135e-11,
    "devices_passed": true,
    "data_passed": true,
    "actual_fault_detected": false,
    "minimum_hbt_vce_v": 0.4505560322188863,
    "maximum_hbt_abs_vbe_v": 0.9413524352396969
  },
  "hot_low": {
    "minimum_signed_margin_v": 0.1155084677485214,
    "maximum_clock_to_valid_s": 3.4843749999993246e-11,
    "devices_passed": true,
    "data_passed": true,
    "actual_fault_detected": false,
    "minimum_hbt_vce_v": 0.40692920104936237,
    "maximum_hbt_abs_vbe_v": 0.851124069036306
  },
  "cold_high": {
    "minimum_signed_margin_v": 0.158880029880191,
    "maximum_clock_to_valid_s": 2.7031250000161818e-11,
    "devices_passed": true,
    "data_passed": true,
    "actual_fault_detected": false,
    "minimum_hbt_vce_v": 0.5005378235904757,
    "maximum_hbt_abs_vbe_v": 0.999419126227099
  },
  "swap_output": {
    "minimum_signed_margin_v": -0.2426777388662699,
    "maximum_clock_to_valid_s": 1.189062500003487e-10,
    "devices_passed": true,
    "data_passed": false,
    "actual_fault_detected": true,
    "minimum_hbt_vce_v": 0.4505560322188863,
    "maximum_hbt_abs_vbe_v": 0.9413524352396969
  },
  "clock_stopped": {
    "minimum_signed_margin_v": -0.23364639544578442,
    "maximum_clock_to_valid_s": 1.1890625000113618e-10,
    "devices_passed": true,
    "data_passed": false,
    "actual_fault_detected": true,
    "minimum_hbt_vce_v": 0.5499849619339559,
    "maximum_hbt_abs_vbe_v": 0.9105858067038834
  }
}
```

This is only a standalone external-clock1pF stress screen using the pinned nominalHBT model at three temperature/supply/RES/MOS conditions. It is not full process/mismatch/jitter or qualified thermal/PEX/closed-loop compliance. It does not repair the already rejected actual PD420 parent. Next implement actual physical16HBT/3MOS/12rppd circuit or explicitly revalidate a folded/parallel tail topology, nativeDRC/LVS/LEF/RC and parent reconnection. Preserve every original loaded parent/PHY gate. The128um singlefinger tails do not fit the old<70um generator height; physical fingers/body contacts must be real, extracted and matched.

## Physically realizable tail partition v7

The existing actual PCell generator uses a device row below70um and local body contacts for32um strips. A single128um finger cannot reuse that geometry. V7 explicitly replaces each128um tail by four independent32um/L0.3um/ng1 native NMOS with common D/G/S/B nodes:16HBT/9MOS/12rppd, unchanged total128um tail width/stage and original8um reference. No multiplicity macro or ideal substitute. A topology check binds every new terminal to the exact passingv6 circuit and proves all HBT/resistor/reference records unchanged. Electrical equivalence is NOT assumed; all five full-window1pF screens rerun before physical adoption. The original stage minimum tail-current gate applies to the actual sum of all four native drain-current waveforms; every individual NMOS voltage check remains mandatory. Native current vectors for all nine MOS are retained.

After electrical passage, actual native PCell generation needs16HBT/9MOS/12rppd plus17finite body contacts (8original distributed +9local MOS). Native deep/flat54device LVS, all560DRC rules, real fault controls, LEF and fresh extracted parasitics remain mandatory. Do not reuse v6 acceptance or the old38device layout as proof of v7.

## Parallel32 actual rejection and physical-drive v8

Run39125446778 confirms the tail partition is not electrically identical: nominal/cold and bothfaults pass, all five device/startup/diagnostic gates pass, but hot_low conservative clock-to-valid37.65625ps exceeds37.5ps. Hot minimum sampled margin100.415mV passes. Do not round the delay or change its gate/timestep. Original stage-current sums are retained. Receipt cdr-sampler-parallel-hot-delay-rejection-20261018.json.

V8 changes only the eight actual tail MOS widths32→36um, eachL0.3/ng1, total144um perstage (18:1 relative to8um reference). All other native devices, loads, boundaries and gates remain fixed. Extra current/power and terminal voltages are measured in all five cases; prior v6 success is not substituted. Width36um still fits the existing device-row height bound with a central local body contact in principle; actual560DRC/LU,54deviceLVS and physical terminal geometry must prove it. New topology receipt explicitly records original128um versus candidate144um, without claiming equivalence.

## Parallel36 measured pass and actual54device geometry

Run39125857951/source3c5d2dcde9235c499ed0238e057fd2c3e6cb9605 passes all five native screens with16HBT/9MOS/12rppd. All normal768samples, device gates and fault controls are verified from full reports (cdr-sampler-parallel-drive-native-pass-20261018.json). The exact topology is144um/stage,4x36um, not the original128um; inherited generic fourfold wording in the scope string does not override these explicit source parameters and recorded current sums. No fullPHY or PEX claim.

The physical workflow now generates actual separate native PCells,17finite substrate contacts (8distributed +9local), all ten real Metal5 boundary ports and TopMetal2 output shunts. Exact source/generator/checker/controller deltas preserve the original560DRC and unsimplified deep/flat LVS/LEF gates. Expected extracted census is16npn13G2/9sg13_lv_nmos/12rppd/17ptap1=54. Original twelve corruption controls remain; missing parallel-tail and missing clock-selector devices add two more. The controller restores all five exact electrical receipts and compares the physical source hash before geometry. Width36um LU/body-contact spacing is verified by native rules, not assumed. This commit launches actual cloud generation/DRC/LVS/LEF; inspect its real result before parent integration or new RC.

## Actual54device first physical rejection

Run39126125731 at43e3002bbc2f87a523f9cb2a5bb0dc65cbd518b0 restored allfive electrical proofs and generated actual946.125x191.03um geometry. Native560category DRC completed and rejected193markers:Cnt.b60, Cnt.g1=12, CntB.a48, CntB.a1=24, CntB.h1=48, M4.b1. LVS/remaining controls were not reached. The generatedGDS and failures remain in cdr-sampler-parallel-first-drc-rejection-20261018.json and its pinned native archive; do not adopt it. The new cloud-only read-only review restores exact native marker coordinates/cells and source geometry, with no regeneration or rule waiver, before choosing contact/route repair.


## Native tap overlap repair, pending fresh physical validation

Read-only run39126723857 at5604b9caf2fda8ebda5d56851149deb1d78594c1 reproduced all193markers. The192contact errors locate six local taps shifted onto their own MOS strips; source32/36um electrical topology was not the cause. One same-SUB M4 pair has only0.14um edge separation. The generator now reserves18um between primitive bboxes, rejects localtap overlap with every actualprimitive bbox (1um clearance), and spaces all M4 columns including same-net SUB. Electricalv8 source,54device census,560native rules, unsimplifieddeep/flatLVS and14faults unchanged. This commit triggers fresh cdr-sampler-parallel-physical-cloud; inspect actual result, not workflow submission. No samplerphysical/parent/fullPHY acceptance yet. Mainchip39121691046 and TX39112087217 still in_progress, preserve. All modifications through GitHub API in RAM; localworkspace remains empty.


## Authoritative sampler physical pass and new parent484

Run39127236215 at0d73c02a6311a7abf3d99a774a510d2857917829 passed actual560-rule DRC with zero markers, unsimplified deep/flat54-deviceLVS, nativeLEF and all14actualfaults. GDS a361748f617e202e509cb78489c0593d4596200a0c6621f096c01485b2dc7341; bbox1134.69x191.03um. Fullreceipt cdr-sampler-parallel-physical-native-pass-20261018.json. Prior193marker rejection remains archived.

This commit launches cdr-retimed-parallel-v3-parent-cloud: replace exactlyfourold38device sampler leaves with verified54device v8 leaves. Exact sourceplan41cards/16macros, expected484devices =116HBT+46NMOS+102rppd+11MIM+209taps. Allotherleafreceipt hashes and native560rules/deep-flatLVS/fivephysicalfaults remain; add explicit extractedprimitive-kind census. Actualleafshapes must be conserved. Supplyoverlay retains the two verified XOR redundant-via omissions and independently binds any new sampler omissions to actualsame-net retainedrisers within4um. Original420source/failedloadedwave evidence unchanged. No newparent electrical acceptance until actualfreshgeometry/RC/modelbinding and ORIGINALfull loadedearly/late/fault gates pass.

Mainchip39121691046 and TX39112087217 remain in_progress at this checkpoint. Cloud-only; localworkspace empty. Full serialPHY/mainchip/finaltiming remain OPEN.


Parent484 run39127789321 at36e1c530d71671261e2380e5ba7b57a213208b7b generated actual484device layout2128.29x4505.08um, but native560rule DRC rejects54TM1.b markers; LVS not reached. Sampler54child remains independentlypassed. Receipt cdr-parallel484-first-drc-rejection-20261018.json preserves fullrejection. This commit launches cdr-parallel-v3-drc-review to expose all54actual native markercoordinates and parent supplyoverlay metadata. Nextfix actualTopMetal1 geometry, retain childconservation/strictDRC/LVS/faults; nofreshRC orparentacceptance yet.


Native54marker review39128067557 reproduced allTM1.b errors. ActualsamplerM_T3/S_T0/S_RP supplyspans run0.085/0.965/1.17um from fixedQP/QN M6via patches; nativeTM1.b requires1.64um. This commit shifts onlythose12spans(+2um, fourcopies) and addsactualM6 endpointbridges tooriginalnativevias. Existingchilddrawing/terminalnets retained. Same-net redundantshunt omission radius4→5um prevents endpointnotches; everyomission stillbindstoactualsame-net retainedriser, originaltwoXOR omissions preserved. Fullparent physical rerun starts; noacceptanceuntilnativeDRC/deepflatLVS/faults pass. Receipt cdr-parallel484-native-tm1-diagnosis-20261018.json.


NativeLVS review39129071316 at85d8a92da366a663321dc6a8541d567c63a60b91 proved onecluster joins aqp/aqn/bqp/bqn/cqp/cqn/dqp/dqn/avdd/avss; noopenedpublic/childnet. Exact484device census preserved. DRC0 alone was insufficient: overlappingM6 conductors merged asshorts. Fullreceipt cdr-parallel484-native-lvs-short-diagnosis-20261018.json. Newrepair checksEVERY sampler supplyspan plus endpointbridges against actualbaselineM6 and already-added overlayM6 with1.645um clearance. Deterministic nearest5nm-grid offset within10um; originalM4/M5 endpoints preserved; allnon-sampler spans unchanged; fixedthree-path patch replaced. Native560DRC/unsimplifieddeepflatLVS/faults remain mandatory. Inspectnewparentrun beforeanyfreshRC acceptance.
