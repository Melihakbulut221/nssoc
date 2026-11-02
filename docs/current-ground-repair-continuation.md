## Current continuation: bounded route retry and actual source-ground M2 bypass

Full serial PCIe Gen3x4 PHY, completed mainchip routing and final setup/hold remain OPEN. All native CAD/GDS/ODB/RC/waves remain GitHub-only. Local workspace empty. Prior verified rootv290=2aa3f2a110716dd059c9f60212e538fba4140a4a preserves mainchip41393730481 memory failure and Via1-only41412504017 zero-admission failure in full.

Mainchip route resource fix on codex/mainchip-route47-repair sourcef808321a65ca9197f10e75f2f59073d47095a718:
Original same64iteration/seed42/2thread route,47selectednets,1691protectedclocks,12GiB no-swap container and2GiB minimum available host memory retained. Only isolated supervisor RSS constant AND its supervised keyword default are changed10GiB->11GiB, leaving1GiB non-RSS cgroup reserve. Command evidence checker derived from authenticated14874bytes SHA059e3e4edde4a63997cc841728f02d5b6a2aaf77335cb7d1b8dba70ed7d2e321 by single reversible constant replacement; every function body AST-identical. DerivedSHA08b30b1fcb7319ca5a204bf94da2ce8a7f03ead5e17d310aa0baaf8fc17c9e84. No physical/electrical/time/output/PID/cleanup/identity threshold changes. Growth may still exceed available memory; no success guarantee.

Initial controls41415300286/source7cd3336db272810b86d756bf42e9ccd1d7ea9909 refused a stale nested workflow digest before native execution. Fix updated only nested full64/snapshot manifests and their transitive pins, not original control bodies. Independent same-source41415631201 PASSED original suites plus19new resource/exit-boundary/owned-keyword-default controls. Authenticatedartifact13127009267 includes route47-memory-controls/result.json. Production41415994457/release431237039 now owns this retry; follow this exact run, do not duplicate or infer success from control-only result. Full candidate output/original route-class restoration,PG/connectivity/LVS/final3cornerSTA still required.

PHY sourceM2 physical bypass experiment on codex/cdr-source-m2-bypass:
Input actual4ccf1212 GDS/current freshRC41404030506/actual32query41407813062. Prior Via1-only41412504017 tested existing overlaps but admittedZEROcuts at all28critical terminals. New geometry instead adds1400nmwideM2 columns from existing1500x4000nm sourceM1 patches to actual same-netM3 ground access17.6um below, a290nm landing to originalM2,24Via1+3Via2 per each of8sources. All216cuts190nm,480pitch,50nm bothmetal enclosure,240nm existing/newvia spacing. Require all13original native unions,actualavss ownership,240nm foreignM2 spacing,50nm foreignVia1/2 clearance,extent/grid,all8sourcearrays,exact serialized onlyM2/Via1/Via2 delta and reversal. No devices/parameters/originalmaterial removed. Original95geometry controls plus8newM2 guards.

First41416167847/sourcec59d1c25092d95e5ffab69be402b17a8ea7103a4 PASSED103controls and firstactual M2owned/foreigngeometry guards, then failed FileExistsError because partial progress reused an exclusive-write filename. Preserve failure, initial proposal and logs. Fix2671a5b64f65df0195b7a3e1e724735521609a5b uses unique per-source/per-cut progress files while retaining exclusive-write save and ALLgeometry guards unchanged. Retry41416430071/release431239884 follows this exact source. No generation or electrical acceptance assumed.

Ground bypass can change bias/current; previous small ground improvement slightly worsened HBT Vce. Require full560DRC,deep-flatLVS13,new canonical full partition proof,newRC,unchangedloaded phase/current/Vce/sampler gates,actualcurrentdistribution/PVT/EM and bias review. Priorloaded41405079602 remainsREJECTED despite physicallyclean block. No completeclosedloopPHY or finalmainchipSTA accepted.

Read-only8hour monitor stays automatic_native_dispatch=false. Each native job is explicitly dispatched only after checking source and terminal predecessor evidence.

Observed at 2026-11-02T08:56:22.982255+00:00:
- 41415300286: completed/failure
- 41415631201: completed/success
- 41415994457: in_progress/None
- 41416167847: completed/failure
- 41416430071: completed/success
