# CDR v25 data/hold capacitance candidate

This is a new physical candidate, not accepted CDR or PHY.

Both v24 native latch diagnoses in run39504732301 reproduce all120 original HBT checks and all4 original output sampler checks from the same complete captures. All output failures occur at the original0.3UI sample; 0.6UI and0.9UI samples pass. C/D master input differentials are weak and their master/slave transfer remains late. Median nearest-edge slave track-on observations are about12.6–14.3ps, with the existing explicit non-causal/edge-boundary caveat. No acceptance window is moved.

The next isolated design change reduces the eight data/hold HBT PCells per sampler from Nx4 to Nx3 while preserving all eight Nx2 clock selectors, every resistor/MOS/tap, bias, load, netlist connection, primitive position and public interface. Lower input/feedback capacitance is a hypothesis to test with new physical geometry and fresh parent RC. Old RC cannot qualify the changed layout.

The v24 maximum observed data/hold current per emitter is about2.2021mA. A fixed-current4/3 scaling estimate would be about2.9361mA, close to the unchanged3mA limit; that estimate is not a simulation or proof. Actual current, all voltage limits, full original early/late bit checks and fault controls must pass again, followed by PVT and full-loop work. The candidate is rejected if any original requirement fails.

The new cloud job produces the actual54-device sampler layout, checks46 unchanged primitive drawings and eight changed data/hold PCells, verifies all560 native main DRC categories, deep/flat transistor LVS, LEF and the existing fault controls. A physical pass only permits full-parent replacement and fresh extraction; it does not qualify timing or the serial PHY.
