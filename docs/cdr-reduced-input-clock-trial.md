# Reduced-input clock buffer trial on actual650 load

This is a circuit experiment, not a PHY or physical-layout acceptance.

The authenticated failed loaded run43717632809 (9709f80) showed maximum model collector currents per emitter of approximately0.634mA in input pairs and0.610mA in cascodes, versus the unchanged3mA screening limit. Output followers reached2.970mA and are deliberately unchanged. Corrected diagnostic43725858840 (c73ef842) measured local clockbase crossings approximately23-26ps after original edges; sampling/phase gates still failed. Delay is a plausible contributor, not proven sole cause.

This candidate changes exactly12 input/cascode instance Nx values4->2, reducing total emitters117->93. All30 HBT instances remain, as do seven ideal resistors, bias reference, mirrors, output followers, polarity, topology and physical650 model. Smaller input/cascode devices may reduce capacitive loading; their currents and headroom must be remeasured rather than inferred from doubled current density. All terminal-voltage/model-current gates remain enabled; full terminal-current SOA remains unqualified.

The original256bit nominal_late sequence,18.75ps data offset,8GHz clock,10ohm sources,150fF sampler and50fF comparator loads,37.5ps sampler deadline,100mV sample margin and30mV phase gate are unchanged. The entire helper prefix containing stimulus/readers/measure_wave is byte-identical to9709f80. Actual650 native transient execution is required. Other PVT/data/fault cases, clock buffer layout/PEX, complete serial PHY and mainchip integration remain outstanding regardless of this experiment's result.
