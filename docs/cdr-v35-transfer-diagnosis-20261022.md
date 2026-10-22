# v35 full-capture transfer diagnosis

All four v35 intrinsic candidates were rejected by their original data/phase/current gates. One B sampler in slave_load16 nominal_late passed its own output checks; that does not accept the complete CDR.

The new cloud workflow reads the four immutable native captures from run39788103410. It verifies each original capture and reproduces all120 HBT and all4 sampler checks, then measures real master/slave inputs, outputs, selector currents and retimer follower behavior at the existing samples and steering crossings. No native simulation is restarted.

The known v33 diagnosis is retained under a byte-for-byte source adaptation manifest. Only pinned source identities, variant names and the verified16 slave-resistor changes differ. All master collector loads and HBT dimensions must remain unchanged. There is no new layout or RC claim.

This diagnosis is intended to distinguish C/D input transfer or capture delay from output settling before choosing the next physical candidate. Internal100mV markers and interpolated crossing observations remain diagnostic, not new acceptance gates. Full original waveform, clocks, loads, windows and failed results remain unchanged. Pending cloud verification; no conclusion about cause yet.
