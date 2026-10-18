# Current cloud-only continuation — 2026-10-18

This checkpoint supersedes earlier running-state notes. All source changes use
GitHub APIs; all CAD, simulation, tests and native archive inspection run on
GitHub-hosted runners. Do not recreate a local checkout or download native
archives, waveforms, PDKs or build outputs. The local project directory is empty.
The existing eight-hour cloud-only heartbeat remains active and unchanged.
The migration Release `cloud-migration-final-checkout-20261013` records
`COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE`, with hosted archive
readback proofs. Unrelated personal files and projects are outside cleanup scope.

## New terminal results

* Mainchip resume **39149110568**, source32d3361453bb4f954d6ef447d6d34bf15ef7f139,
  completed actual detailed routing and fresh RC/three-corner STA. Native routing
  DRC0, critical disconnected pins0, antenna nets2. Original constraints retained.
  Slow/typ/fast setup counts9673/7647/3811, hold8/11/27; setupWNS approximately
  -19.586/-6.817/-3.288ns. Final timing and signoff FAILED. The green workflow
  means complete measurements, not closure. Receipt:
  `docs/evidence/onehot-load-resume-route-result-20261018.json`.
* CDR strapped-v6 physical parent484 devices passed native physical checks, then
  fresh planes39152752893, wire inputs39153187381, binding39153425908,
  RC39153425684, MIM capture39153832093, intrinsic audit39154042288 and
  composition39154204614 passed. Model `nssoc_cdr_pd484_strapped_mim_wire_v6`
  contains484devices,3286R3855C,11MIM. The original full256bit loaded run
  **39154395989** then REJECTED both nominal early and late cases. Data/device
  and VI current gates remain failed. Clock-stopped and VI-off controls detected
  their faults; those passes do not validate nominal operation or a full PHY.
  Receipt `docs/evidence/cdr-strapped-v6-full-wire-rejection-20261018.json`.
* TX original return-repair run39137607059 nominal remains electrically rejected.
  Full-wave path39153187411 and device/extrema/DC39153635231 reviews reproduced
  the failures. Final/level4 paths remain bad; shorter fast-stage routing was
  tried without changing devices, clocks, loads or thresholds.
* New six-row TX layout **39154915645**, sourceb6e85db37a8deb6be74a17a1b45a418c60952623,
  FAILED strict unsimplified native LVS: both sides have1674devices but top
  circuit is NoMatch. This is not a valid physical candidate; DRC and later
  electrical gates were not reached. All logs/GDS/extracted netlists remain in
  its cloud Release. Receipt `docs/evidence/tx-v5-fast-stage-lvs-rejection-20261018.json`.

## Continue here, entirely in cloud

1. Inspect native TX39154915645 LVS comparison/extracted connectivity on a hosted
   runner. Fix actual routing/placement shorts or opens before fresh extraction
   and full simulation. Keep all original LVS/DRC/fault checks. The candidate
   scripts are `cloud_tx_v5_fast_stage_assembly.py`,
   `check_tx_v5_fast_stage_geometry.py`, `check_tx_v5_fast_stage_sources.py`.
   Do not infer a short location from device counts alone.
2. Inspect strapped-v6 actual loaded waveform losses and failed sampler/device
   voltages with a hosted diagnostic, reproducing original gates first. Do not
   claim straps alone solved electrical operation. Original local-v5 rejection,
   load-resistor screens, waveform reviews and all physical receipts remain.
3. Review new mainchip STA/antenna reports in the preserved native archive using
   a hosted review workflow. Start from `cloud_onehot_load_route_review.py`.
   Fresh measurements are in `run/5-nssoc-onehotroutedsta/{corner}` and antenna
   reports in `run/2-openroad-checkantennas/reports/`. Select the next actual ECO
   from these paths, not stale pre-route estimates. Preserve20/4/8/8ns clocks,
   5%derate, actual20SRAM and original proof/DRC/antenna acceptance requirements.
4. Check any still-running earlier TX negative-control and generic CI jobs before
   starting duplicates. No running job was cancelled during this checkpoint.

Full serial Gen3x4 PHY, full mainchip integration/signoff and final setup/hold
remain OPEN. Physical prototypes and externally clocked loaded screens are not
complete recovered-clock PHY qualification. Preserve failed evidence.

Observed UTC: 2026-10-18T18:45:28.828928+00:00
