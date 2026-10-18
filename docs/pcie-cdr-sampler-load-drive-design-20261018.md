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
