# Existing CDR500 nominal waveform diagnosis

The two original nominal cases in run 40081228425 completed the full native transient and were rejected by the original electrical gates. This workflow reads those immutable captures without running a simulator or changing a circuit.

Before analysis it verifies the failed source jobs, pinned summary/parts hashes, every complete archive part and archive hash, selected-file hashes, all 500 intrinsic bindings, the 13 binding corruption controls and exact native waveform shape/1152 columns/113475 rows/34.25 ns. The original measurement-to-interface block is executed unchanged against the restored wave and every produced metric must equal the rejected report exactly. Eight archive controls, ten source metadata controls and eight metric corruption controls must reject their mutations.

The report identifies startup versus active VCE peaks and actual C/B/E voltages for the four C/D gain HBTs, native terminal voltage differences on their physical nets, the original sampler timing/margin witnesses, and native VI collector source/sink paths. It does not equate collector currents with emitter currents or claim complete KCL. All source files are hashed again afterwards. Original waveforms remain unchanged in their pinned cloud release; only derived diagnostic reports are published anew.

A passing readback means the failed results were reproduced faithfully. It is not CDR, closed-loop, PCIe PHY, RC or product acceptance. No live source matrix job is cancelled or restarted. A physical repair must follow the measured failure and must retain the original ten cases and gates.
