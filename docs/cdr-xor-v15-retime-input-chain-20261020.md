# Source-bound C/D retime input-chain diagnosis
The prior native latch replay39326235115 showed low C/D master-input differential markers and persistent wrong outputs, but did not isolate which actual resistor, MIM or interconnect segment lost amplitude/common-mode/settling.

This cloud-only diagnostic binds both physical ac/bd retime macros to A/B slave collectors and C/D master bases using real native clusters and device ownership. Each differential leg must have exactly one actual filter series resistor, shunt resistor, feedforward MIM, sampler input series resistor and bias resistor. Missing/ambiguous elements fail. Corrupted physical ownership, actual sampler terminal and native bias-rail controls must be rejected.

It measures source collectors, every bound component terminal and actual master-base nodes at the original8phase offsets on both unchanged rejected fullwaves. It records differential/common-mode voltages and physical terminal-to-terminal voltage differences. No linearized resistor currents, shifted clock, new waveform or relaxed acceptance gate is introduced. The complete original116HBT and4sampler checks are still reproduced. Internal100mV markers remain diagnostic; fullPHY acceptance stays false.

Next use the measured loss distribution to choose a real input-drive/bias/interconnect repair, then native geometry/LVS/DRC, fresh complete RC and original electrical gates. This report alone is not a repair or signoff.
