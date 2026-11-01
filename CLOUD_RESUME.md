# Cloud continuation — checkpoint v215

Updated: 2026-11-01T04:19:30.552719+00:00

Latest direct user instruction is CLOUD ONLY and local project cleanup, superseding older goal text that said local. Workspace and project temp areas are empty; no local CAD/native processes. Source authoring/static inspection and API-derived text coordination are RAM-only. Tests, numerical/geometry analysis, simulations and CAD execute on GitHub. Never acquire native archives/models/SPICE/raw waves/ODB/GDS/native-frame gzip locally, including RAM. Preserve unrelated files and original attachments.

## Two current actual jobs

1. [Mainchip41270471645](https://github.com/Melihakbulut221/nssoc/actions/runs/41270471645), source2b8931b9c8988fc5dbf497a7b561db579e39f64c, branch codex/mainchip-net459-diode-prune, independently reserved exactsource release430345631/tagcloud-results-41270471645-1-mainchip-bulk-postdrt-antenna. Source controls pass; latest step clear828/routing active. Do not infer detailedrouter subphase from step name. The tuple/list snapshot repair uses complete persisted JSON on both sides and keeps strict geometry guards unchanged.

2. [Coupled sampler-load CDR41272254964](https://github.com/Melihakbulut221/nssoc/actions/runs/41272254964), source8a07e8f773d931f9cb7f4ac72e5520b68bb133be, branch codex/cdr-sampler-load-headroom. Independently created/read-back empty exactsource release430356103/tagcloud-results-41272254964-1-cdr-sampler-load. Full6-file reservation proof imported. Source controls passed; native job active. Do not duplicate either run or mutate native branches until terminal.

## New concrete circuit candidate

Eight sampler Q collector pullups XD0175/176/191/194/202/205/212/214: rppd L2.6um->1.5um,W32um unchanged.
Four shunts XD0184/185/222/223: L5um->7.4um,W4um unchanged.
Hypothesis: improve loaded output settling and raise upstream output common mode to counter the four-shunt-only input-buffer maxVCE regression. Smaller output swing may fail; no improvement is asserted before native measurements.

Only12 exact intrinsic length tokens change; baseline full500device model and all unrelated bytes/parameters/terminal identities/wireRC retained. No regenerated layout/freshPEX. Original prepare/measure executable bodies unchanged, original1151vectors,13actualbindingcontrols,10ohm/150fF/50fF workload and all gate thresholds remain. Source has33pinned files. Sourcecontrols41272126724 passed13circuit corruption and5archive corruption refusals; full13-file proof imported. See docs/cdr-sampler-load-headroom.md.

## Qualified result comparison, not yet actual comparison

Branch codex/cdr-sampler-load-comparison sourcefe337c7dd83d1f1d3e11657b36ea45d1ca144e24.
Controls41272429110 passed10refusals; full10-file proof imported. It checks exact12resistor delta in full bound circuit and every original electrical predicate, all124HBT and1530bit delays; separate VIcurrent/voltage pass fields. Candidate_context is fixed to run41272254964/source8a07; candidate.json descriptor is deliberately null until full terminal proof exists. Do not substitute synthetic control data for a native candidate.

After collecting native result, pin its exactderived report bytes/SHA/source/path, change only that input descriptor, and dispatch one compare with controls repeated. Preserve full comparison artifacts/logs and all failed experiments.

## Retained findings

Original mainchip41266854050 failed before detailed_route because equal coordinates were Python tuples versus JSON lists. Cloud readback41269689818 passed unchanged strict delta over complete saved snapshots/all828nets and reproduced representation mismatch. All735 authenticated emitted records remain in complete prior failure logs, native archive in release430325810. Old reservation consumed.

CDR four-shunt-only41268684044 engine returned0 but electrical gates rejected. Prior minVCE failures disappeared and maxVCE failures T59/T60/T111/T112 appeared. All6data stages/phase/VIcurrent still failed. VIvoltage passed its0.005V minimum. Full61-file terminal and15-file comparison proofs retained.

Clock diagnosis41271280278 reproduced original metrics and measured all32clockdevices/eighttails/32paircombinations/both255edge directions/all255samplerbits. Internal delay1.95–4.06ps is relative to already-loaded externalports. First externaledge is~11ps after nominal. Do not claim wholeclockpath only2–4ps. Complete31-file proof retained; see docs/cdr-clock-path-results-and-design-next-step.md. No need to re-download native wave just to aggregate derived records.

## Next actions

1. Observe the SAME two actual jobs above; preserve full success/failure evidence, no native local downloads.
2. Collect CDR terminal source/controls/derived reports and releaseindexes. Activate qualified comparator only with exact real terminal report. All gate/clock/data/load predicates remain.
3. Electrical pass still requires real changedlayout/fullDRC-LVS/freshRC/corners/closedloop. Failed result remains rejected and retained.
4. At mainchip terminal verify actualclear/router,828connections/1351diodes/1691protectedrecords,zeroDRCantenna andfinalSTA separately.
5. Keep8h read-only monitor automatic_native_dispatch:false, inventory576runs.
6. FullserialGen3x4PHY, routedmainchip, finalsetup/hold andproductionapproval remain OPEN.
