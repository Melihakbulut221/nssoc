# Whole physical PLL: full-terminal native acquisition

The candidate is the actual 845-device model plus four native well contacts, 26 MIM capacitors and raw conductor RC (3381 resistors, 5105 capacitors), already bound by loaded preparation run 39360285698 and native zero-source OP review 39361546966. This is not qualified RF PEX or a complete serial PHY.

The new cloud workflow starts the unchanged 1 us transient with the original 0.3125 ps maximum step, KLU tolerances, supply ramps, reference/reset stimulus and clock loads. All 1694 unique terminal voltage vectors are retained. The 2737 terminal records and four auxiliary contacts are checked against the prepared model. All 102 actual HBT OFF settings must read back one.

The engine and portable native image come from the previously verified cross-host process checkpoint experiment. Each cloud stage runs the same simulator process; CRIU preserves its state. The following stage verifies every checkpoint image and the complete existing raw payload prefix before continuing. Cold restarts and waveform concatenation are forbidden. Four hours is a host-stage budget, not a shortened electrical transient.

A bounded-memory binary reader validates every column for finiteness, exact identities/units, complete rows, native point count and monotonic time across chunk boundaries. Final acceptance requires more than three million native rows, original full duration and original maximum step. The original frozen acquisition analyzer still evaluates both final 100 ns windows. Finite full-terminal voltages alone do not prove device safety or PLL acquisition.

Checkpoint publication retains all raw bytes and native state. A disk reserve trigger checkpoints before exhaustion without dropping probes. If the preserved capsule cannot fit the next hosted machine, further execution requires more cloud storage; such a checkpoint is not full capture or acceptance.

The initial controls test large native-style headers, every terminal including the last unsummarized column, boundary time errors, malformed metadata and partial payloads. These are reader controls, not an analog simulation result. Actual analog and timing results must be recorded separately after the cloud jobs finish.

Existing TX normal run 39344566214 and mainchip route run 39369450310 continue independently. No PHY, mainchip timing, signoff or manufacturing approval is claimed here.
