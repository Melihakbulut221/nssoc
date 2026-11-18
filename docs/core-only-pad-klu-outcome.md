# KLU diagnosis outcome

Native KLU was confirmed in every case of run44372922971. It did not repair0-turnoff: the same22.7529ns/vhold#branch failure remained. Other five captures completed. Both synthetic failure/readback tests passed. Exact artifact and all79 output hashes verified; completed waveforms compared at identical printed sample times against Sparse1.3. See accompanying JSON for per-column differences and exact source binding.

Do not repeat linear-solver or Newton-limit sweeps. Next controlled diagnosis is smaller maximum time steps (2.5ps and1ps) with unchanged circuit/model/PVT/tolerances and native KLU/Gear2. Failure at the same internal state would motivate a reduced transistor/model reproducer rather than treating an incomplete capture as success. No slew waiver or Liberty change.

Manual used for documented solver selection: https://ngspice.sourceforge.io/docs/ngspice-html-manual/manual.xhtml sections11.1.1/12.6. Core route44337630426 remains active and independently requires admission then actualSPEF timing. ExternalIO specification remains unselected.
