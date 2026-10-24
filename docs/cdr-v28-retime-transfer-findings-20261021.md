# Real v28 retime follower observations

Both native transfer diagnoses39572394402 passed their source, waveform, original sampler and120-HBT reproduction checks. The circuit remains electrically rejected.

The four physical ac/bd follower HBTs remain conducting throughout the active capture: minimum collector currents are approximately0.212–0.401mA, with no nonpositive samples. VBE stays above0.767V. These measurements do not support follower cutoff as the residual v28 failure cause. Increasing the pull-down current alone is not established as a solution.

Actual input/output differential ranges are about0.28–0.31V and0.23–0.27V respectively; their mean output common modes are1.364V for ac and1.387V for bd. The downstream sampler divider and actual interconnect still attenuate/delay these signals: native latch diagnosis observes substantially lower C/D master-base margins. All four outputs pass the later0.6/0.9UI samples but fail the original0.3UI gate; C selector VCE remains below0.4V. No threshold, load, clock phase or oracle changed.

Next circuit correction must address both the sampler input transfer/common-mode and the early clock-to-output response, then repeat fresh native geometry/RC and original full loaded gates. A retime gain-stage redesign is a possible architecture to evaluate, not an accepted or simulated implementation. Neither a leaf model nor diagnostic reproduction proves closed-loop CDR, full serial PHY or mainchip closure.
