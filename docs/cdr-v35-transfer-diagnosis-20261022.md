# v35 full-capture transfer diagnosis

All four v35 intrinsic candidates were rejected by their original data/phase/current gates. One B sampler in slave_load16 nominal_late passed its own output checks; that does not accept the complete CDR.

The new cloud workflow reads the four immutable native captures from run39788103410. It verifies each original capture and reproduces all120 HBT and all4 sampler checks, then measures real master/slave inputs, outputs, selector currents and retimer follower behavior at the existing samples and steering crossings. No native simulation is restarted.

The known v33 diagnosis is retained under a byte-for-byte source adaptation manifest. Only pinned source identities, variant names and the verified16 slave-resistor changes differ. All master collector loads and HBT dimensions must remain unchanged. There is no new layout or RC claim.

This diagnosis is intended to distinguish C/D input transfer or capture delay from output settling before choosing the next physical candidate. Internal100mV markers and interpolated crossing observations remain diagnostic, not new acceptance gates. Full original waveform, clocks, loads, windows and failed results remain unchanged. Pending cloud verification; no conclusion about cause yet.

## Completed cloud diagnosis

Run39799502447 reproduced the120 HBT and4 sampler results in all four captures, with all original failures preserved. At the uniquely associated master steering crossings, C/D input signs are correct for all255 bits per case, but every C/D input is below the diagnostic100mV marker. At the original37.5ps output deadline, every master output is above100mV while slave outputs still fail. The internal marker is not an acceptance gate or a proved causal aperture.

Slave_load16 nominal_late B remains the only passing individual sampler (113.055mV,36.406ps); no complete candidate passes. Reducing all slave loads improved A/B margins but did not close C/D. Further candidates must separate primary-output swing/retimer transfer from secondary-slave settling, preserve the existing clock stimulus, and repeat the full loaded device/phase/current gates. No candidate is promoted to physical layout by this diagnostic. Exact release pins and compact original-deadline observations are in docs/evidence/cdr-v35-transfer-diagnosis-results-20261022.json.
