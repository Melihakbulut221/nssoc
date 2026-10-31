# Cloud continuation — checkpoint v184

Updated: 2026-10-31T17:53:29.128649+00:00

All RTL tests, simulation, CAD and numerical/native processing run on GitHub. Never acquire native archives, models, ODB/GDS, raw waves or native-frame gzip locally, including RAM. Source/API derived text coordination uses RAM only. Workspace and project temporary prefixes are empty; no local CAD process runs.

## Actual qualified RTL integrated

Run [41223635170](https://github.com/Melihakbulut221/nssoc/actions/runs/41223635170), exact source17033684f3dfd0c760ac7cf64d2e1dc1a4b2fdb0:50named positive RTL tests passed,0positive skips; two compiled semantic mutants detected by exact independent assertions; two production top hierarchies each have1sharedfront/4aligners/4CDC/4FIFO.

Complete12file859103byte proof imported from1006eae3d1198e12ed1d3f22e3eaf800be13a788 under docs/evidence/pcie-shared-serial-front-terminal-41223635170/. ReceiptSHA04be01120e1a35be523bead9c5bb4cdd0ec75c25d9c2e51cacde8288e53fcde1.

Ten tested source files plus qualified documentation/provenance are now integrated byte-for-byte. All17existing protected dependencies match. Candidate-specific workflow is intentionally not imported: runner remains bound to its tested execution branch, and root execution acceptance is not inferred. The actual consumer chain is events_v3 -> owned_rx_v2 -> recovered_x4_v5 -> shared front_x4_v1. soc_top still has external packet-interface status, not integrated serial PHY.

## New training transport source

Branch codex/pcie-training-epoch-ingress-v1, corrected source2a69d010371aff75fb8be204c92ef4c1d384d48e. Run41226031156 passed16source/refusal controls, no failures/errors/skips. Complete proof9fa7ac82df98e32db95d08bb527580fbaf31a1c8 is imported.

Four-phase bundled command mailboxes, safe modulo epoch reuse and actual Gen12/sharedGen3 transport composition were reviewed by root and peer. A real reset/completion coincidence bug was fixed with direct abort priority and success masking; dedicated same-edge and stopped-lane WAIT_LOW tests added. Test oracles now use valid lane slices and actual ready pin snapshots.

Planned110positive RTL tests,6compiled mutants and4hierarchies have NOT run. Native execution remains disabled at the tested source. Narrow activation adapter preparation is authorized; exactsource review, own hosted controls and independent empty destination release precede any actual dispatch. No TS/EQ/LTSSM or link-up semantics are invented. Physical composition is8FIFOs,4active for the selected encoding.

## Preserve running native work

- Router [41211382427](https://github.com/Melihakbulut221/nssoc/actions/runs/41211382427), source ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9, release429993235. Keep original job; no restart for quiet logs. Packet-interface SoC only.
- Ten-case loaded CDR [41218657461](https://github.com/Melihakbulut221/nssoc/actions/runs/41218657461), source84b8b591e10be32716947c8d6b079fd7a21ce18d. All11case/preparation releases reserved. No retry/recreation; preserve rejected cases.

Snapshots in docs/evidence/cloud-collector-recipes-20261029/qualified-shared-front-and-cloud-only-v184.json give observed job states, not completion claims.

## CDR evidence and next physical correction

Actual existing nominal readback41223527977 succeeded:2991archive members authenticated,4590queries/1530native settling windows percase, original electrical REJECTED verdicts replayed exactly. Full116file44,179,088byte proof remains imported. Wave/frame gzip stays cloud-only.

The old v57 leaf l7.4um gain pulldown is intentionally transformed to current native l5um by generate_cdr500_resistor_v59.py arm cd_shunt, exactSHA73d2eb18f3ceb4425668584f86b5e64a4c262af25c638114a4f18fcac36fb81d. Actual native IDs184/185/222/223 and PCell/reference lineage confirmed. Audit55db15f41be2779ec2e9e9e0b83d95f970f74f0c imported.

GainmaxVCE margin is only25.470mV while failedselector61 needs about58.75mV recovery. Do not blindly raise gain commonmode. Current8drain additions only shunt bounded MOS M1/M2 access, not selectorcollector paths. Four actual target nets: components17/19/61/63, native28/38/135/136. Real accessR/C and geometry diagnosis is next; V/I differences alone are not causal proof.

Readonly collector branch codex/cdr-current-access-rc-readback sourcefca239618687303bde8dfd18c3f2139c7308ff8d has nativeauthorityfalse. Hosted sourcecontrols41226430440 and source review are underway. Current500device/R24356/C15566 composition and all original electrical limits stay unchanged; no new analog simulation or geometry candidate is yet accepted.

## Routed-chip timing gate

After actual router terminal authenticate all17commands/full capsule and final-measured.odb. If physical gates pass and only old host16-command expectation fails, use qualified adapterc6132e91884c796bfdb5c38f9b4c1bb015ccc74d; never relabel physical failure. Routed-view source26controls passed but actualexport remains disabled until candidate/engine/LEF/Liberty binding.

Keep153129original instances+1351diodes=154480 and143820nets. Fresh RC/STA retains20/4/8/8ns clocks,5percent uncertainty, threePVT and zero setup/hold/slew/cap/fanout. Old netlist/SPEF is inadmissible; nominalRC is not RCmin/max qualification.

Monitor: 467handles, inventoryv184, every8hours, automatic_native_dispatch=false. EarlierHTTP502 monitor issue not claimed fixed. Allcommits [skip ci], nonforce CAS. Use scoped subtrees; whole-root recursive Git tree truncates.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable receipt: docs/evidence/cloud-collector-recipes-20261029/qualified-shared-front-and-cloud-only-v184.json

Full serial PHY, final routed-chip setup/hold, RCmin/max qualification and production approval remain open.
