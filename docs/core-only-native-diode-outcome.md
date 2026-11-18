# Native darea transient failure: standalone evidence

Run44377766116/head daddaf140a6373b3ba24fa5a7666a410d8f83d79 excludes all transistor models,OSDI and pad hierarchy. Native ngspice47/KLU/Gear2/itl4=100,125C,1ps,default tolerances. Twelve independent cases executed: only antenna-release and area-release fail at21.3262ns. All ten constant/remainder-component controls complete50ns. Thus darea alone is sufficient to reproduce the transient failure in this runtime/model combination. This does not yet establish whether the defect belongs to the model or simulator.

Artifact14460369885 SHA2567e8223586fd3a7b6f4f9f290991b87663da1f532cfdb7b651e7641eebea00b08 and every output hash verified. Completed waveform duration,increasing times and finite three-column values independently checked. Full-pad and native diode failures remain recorded,never waived.

A portable fixture is preserved under hw/soc/analog/diagnostics/darea-release/. Its deck inlines the exact diodes.lib bytes in place of the original absolute include; the included model values and licensing text are unchanged. The adjacent spinit preserves original startup configuration. This portability transformation itself is not yet independently rerun. No transistor or proprietary model is needed. Run from that directory with SPICE_SCRIPTS set to its absolute path and the pinned ngspice47 binary using -n -b bench.cir. A zero simulator exit code is not success: require no TRAN abort and full50ns wave.dat.

Next investigate native diode charge/convergence implementation or an independently pinned simulator revision using this unchanged fixture. Do not delete antenna protection,change transit time/resistance/capacitance parameters,relax tolerances or claim model correctness because a different diagnostic circuit passes. A verified runtime correction must be rerun on the original full pad and across timestep/PVT before Liberty review.

Core detailed route44337630426 remains independently active. On terminal result admit its exact artifacts and run staged actualSPEF extraction. ExternalIO/package and full-chip production signoff still open.
