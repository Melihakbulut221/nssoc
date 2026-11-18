# Prepared core-only nominal extraction and fresh STA

The manual job is PREPARED, NOT DISPATCHED until detailed-route44263061910 is reviewed. scripts/cloud_core_only_routed_extraction.py binds that immutable producer and all mapping/CTS/repair ancestry, compares its native/summary archives, verifies outputs and protected inputs, then feeds its own routed ODB/netlist/SDC to the qualified nominal OpenRCX and actual-SPEF standalone OpenSTA adapter.

A derived configuration changes only STA_THREADS=1 and the explicit three existing cell corners. Clock20ns,5%derate, macro views and pin constraints stay unchanged. Nominal RC rules and SPEF capacitance conservation remain checked. Neither min/max RC nor annotation completeness is accepted automatically. The macrofast-55C/stdcellfast-40C qualification issue remains.

CoreExtractedSTA now records each native run_corner return directly as fresh_metrics.json, requires finite setup/hold/count metrics for that exact corner and rejects mixed corners. This avoids consuming inherited state.metrics as a fresh result. All3standalone logs must contain the propagated core-clock guard and noEST-0026. This new capture path is not yet circuit-executed; actual cloud execution will test it. Native script generation qualification remains narrower than this circuit run.

Successful execution only yields nominal extracted analysis evidence. Missing loaded-net annotation, unqualified RC corners, timing/electrical failures, transistorLVS/DRC, postECOequivalence, padframe/DFT/CDC/ESD/package andmanufacturing approval stay independent gates. No completed routed producer is assumed merely because this script exists.
