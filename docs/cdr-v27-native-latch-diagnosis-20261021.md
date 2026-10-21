# Native v27 transfer diagnosis

Both cases in run39555076416 independently reproduced all120 HBT measurements and all four original sampler checks from the complete retained34.25ns waveforms. The three physical-graph mutation controls per stage, parallel-bank controls and original raw reader checks passed. The nominal electrical rejection remains in force.

All four actual samplers still steer their master/slave current between track and hold; there are257/258 observed transitions of each direction in the captured active interval. Their clock transistor base differences span approximately-299mV to+283mV. Thus the collapsed select0/select1 interface signals are not evidence that the actual sampler clocks stopped: those interface signals belong to a different part of the network.

A/B master-input signed margins at the early0.3UI diagnostic point exceed124mV. C/D master-input signed differentials are below the100mV diagnostic marker at every sampled bit; the C minimum is about-3.50mV and D+5.39mV. The frozen graph verifies these are the real input transistor bases, not an ideal substituted waveform. C/D consequently fail the original output sampling gates.

The8 shortened BP/BN pull-ups increased input common mode enough to clear all original device bounds, but the complete loaded candidate still fails function. The next circuit decision must account for the source loading and level-shift transfer at C/D while keeping selector VCE bounds. Do not interpret this diagnosis as approval of stronger pull-ups, waive the voltage/data gates, or alter the expected bit sequence or sample clocks. Any next physical candidate requires new native geometry, DRC/LVS, raw parent extraction, composition and the unchanged full loaded cases.
