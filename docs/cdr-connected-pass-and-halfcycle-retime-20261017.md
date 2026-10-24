# Connected comparator passed; next actual half-cycle retiming path

Feedforward-v4 run39054158225/sourcebb23c0b8939d620a521b103d8ae0b55deceed8d9 passed all three normal native tests and both actual faults. Normal minimum signed margins:149.960mV nominal,122.958mV hot,132.343mV cold. Maximum clock-to-valid:59.53125ps,69.21875ps,54.84375ps respectively. Every normal test had768correct samples and zero below100mV. All57HBT limits, four native MIM voltage checks,57actual OFFreadbacks, zero-source OP and clean numerical diagnostics passed. Source/model hashes and full reports are preserved in cdr-feedforward-v4-pass-20261017.json. This closes the specific connected comparator failure, not a full CDR.

A complete sampled phase detector must preserve consecutive sample identity and opposite-edge timing. The new halfcycle-retime test physically connects one native sampler's output through four native rppd and two native MIM devices into a second native sampler on the opposite clock edge. There is no ideal voltage source or Boolean regeneration between them. Converter W1/L5.4 and W1/L12.6 nominally form a0.7 divider;3.6um-square MIM devices compensate the series legs. These are unproven native circuit values.

First sampler must reproduce original PRBS bit i after rising edge START+(i+0.5)UI; second must reproduce that same original bit after falling edge START+(i+1)UI. Both retain100mV/37.5ps valid gates and fixed0.3/0.6/0.9UI sample phases. Native bounds cover all30HBTs, four tail currents and both MIM terminal voltages.150fF loads remain on all four outputs, alongside actual connected loading. Two500uA references and8GHz clock remain explicit external boundaries.

Nominal/hot/cold, swapped final output, stopped clock and actual wrong-edge second sampler are six separate Actions cases. All outcomes are preserved. Wrong-edge must fail original bit identity rather than a metadata check. This alone is not the three-sample/two-comparator phase detector, clock recovery, jitter/BER, physical routing or x4 integration.

Architecture context: the Alexander detector uses three consecutive samples to distinguish clock/data phase (https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/el.2016.3368). This motivates actual sample timing; it is not evidence that this transistor cascade works.

## Capture correction

The initial half-cycle run39054982732 failed evaluation because the voltage list was derived from HBT terminals only. Converter nodes udp/udn connect through the sampler's input resistors, so they were absent from the saved waveform. Hot report651141978 records the exact KeyError after native simulation returned0 with clean diagnostics. No whole-circuit pass/fail is claimed from this incomplete capture. The source receipt is cdr-halfcycle-capture-error-20261017.json.

The correction saves the union of actual HBT, resistor and MIM terminal bindings and checks all four interstage voltage probes before simulation. Circuit wrapper SHA d1e16573ce5b0ea30a8c37d13fe60867eee13310027e2247e2a2e09776635e52, stimulus, native engine, device limits and timing gates are unchanged. All six cases must rerun with complete waveforms in Actions; old captures remain preserved.
