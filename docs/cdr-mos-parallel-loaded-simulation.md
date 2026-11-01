# PD650 loaded simulation: actual electrical rejection

Run [41288195752](https://github.com/Melihakbulut221/nssoc/actions/runs/41288195752), exact source d638e0e3cd15a0ee930212c27ab1f238b5085237, completed the native transient. The engine returned 0 after 1037.3823876919998 seconds. There were no simulator diagnostics and protected sources remained unchanged. Original electrical acceptance failed.

Full115-file proof: 6fdf10cd1683b920950104e7edb6206865eab78e, `docs/evidence/parallel-mos-native-terminal-41288195752`. Complete native wave/model archive remains in release430445706; no native payload was acquired locally.

The real capture retains all1301 vectors (977 node voltages,124 HBT currents,200 MOS currents),11 save commands,200 independent MOS units from50 origins,192 tail units in16 original groups and7 MIMs. Device voltage/current gates and the loaded VI gate pass. All six data stages fail:

| Stage | Max clock-to-valid (ps) | Minimum signed margin (mV) | Below100mV samples | Wrong-sign samples |
|---|---:|---:|---:|---:|
| A |42.65625|59.369517|97|0|
| B |37.96875|97.230100|22|0|
| C |118.90625|-17.551896|167|33|
| D |118.90625|-24.196656|129|50|
| X |118.90625|-112.636678|753|385|
| Y |118.90625|-18.551353|717|58|

Each stage has765 sampled points. Original sampler limits remain100mV and37.5ps; XOR limits100mV and75ps. Phase mean19.616143590646336mV fails30mV. Loaded VI reports59.817713930936uA and17.667962748922mV and passes its original limits.

This corrects the former live status. Previous41287653458 failed before engine execution because baseline namespace globals were overwritten; its failure remains preserved separately. New41288195752 executed the real engine and was rejected electrically. The isolated namespace source correction worked.

The200-unit model remains the explicit domain-corrected candidate, not accepted timing or layout. It retains original wire RC; its geometry has not been expanded/re-extracted. Do not revert to the42 original out-of-model-domain widths to recover a superficially better result. Four native unit widths are being physically qualified independently. Complete sampler corrections, independent references, full DRC/LVS, fresh RC, PVT, closed loop and serial integration remain mandatory.
