# CDR native waveform transport repair

The via-rich full loaded run39165464508 nominal_early did not pass. Its native solver returned0 but reported approaching the max-data limit at10471.504MB versus10687.379MB. The original gate rejects these diagnostics; no electrical acceptance is inferred. The unchanged full run and all failures remain in Releases.

The ngspice manual documents immediate rawfile storage instead of retaining transient plots in memory (section12.8): https://ngspice.sourceforge.io/docs/ngspice-45-manual.pdf . The project already implements native binary raw streaming in scripts/cloud_tx_stream.py. The new CDR transport control reuses that pinned implementation, moving identical tran parameters to .tran and using run wave.raw. Every save/alter/model/source/solver statement is retained.

Before full-window use, cloud_cdr_via_rich_stream_control.py compares original ASCII and streamed binary output for the same entire484-device13186R10127C model over3ns. All1107 vectors and every unshifted native row must match the existing decimal-format transport bounds. Original solver readbacks,116HBT initialization flags and zero-source operating point remain checked; changed samples and omitted vectors must be rejected. The shortened interval validates transport only, not CDR electrical behavior. Full34.25ns/256bit loaded runs with original timestep, loads and all acceptance gates are still required.

## Actual command overflow found

Native header review39167449500 found10137 raw columns rather than1108. All945 requested voltages were present, but all162 requested HBT/MOS current histories were missing. The original controller issues one save command for1107 vectors, exceeding ngspice's1000-argument save limit. `run_cloud_tx_mux4.native_save_commands` already uses bounded commands for larger TX observations. The CDR control now requires the original native save rejection log, uses that pinned helper to emit nine commands of at most128arguments, verifies exact vector order/completeness and rejects command errors. It retains the strict1108column raw reader; extra or missing vectors are not accepted.

The same full physical3ns comparison will be repeated with bounded save commands for both ASCII and binary transports. All original voltages must also agree with the prior preserved waveform. The162 old versus new current histories are separately diagnosed; the old unrecorded device-current expressions cannot support transient current-limit claims. Full-window native voltage/current and operating-limit acceptance is still required after a transport pass.

## Same-model transport and command repair passed

Cloud run39167905272 passed at source052a821570faa1843ec94b4cb160e7eedf2683b8. Both native runs returned0 with no diagnostics, same KLU/trapezoidal numeric settings,116verified HBT flags and zero-source operating points. All1107 vectors across9722unshifted native samples matched within the existing decimal-format bounds; all945 original voltages also matched the prior unbounded-save capture. All162 requested device current histories are present and vary in the corrected native record; 162of162 old histories were constant. The original log explicitly reported `save: too many args.` Missing-vector and changed-sample negative controls were rejected. Receipt: cdr-via-rich-stream-transport-pass-20261019.json.

The new full workflow cdr-via-rich-v7-mim-streamed-cloud.yml retains all484devices/13186R/10127C, original34.25ns256bit stimulus,125psUI,.3125ps maximum step, loads and every electrical gate. Only bounded-save transport, strict binary reading and command-error detection change; the source delta and helper hashes are checked. Full-window results are not yet accepted. All prior failed runs remain retained.
