# Original-master q20 actual-selector transfer diagnosis

Existing native run 41277056212 remains the sole measured circuit. No simulator or geometry mutation runs. All native data remain on GitHub.

Initial transfer analysis 41279373178 refused a wrong B-to-selector assumption. Its complete failure evidence is retained at 9aceb9e54839bc2c213aa1156c89da75a752b0d1 / docs/evidence/cdr-sampler-candidate-wave-41279373178. The actual 500-device composition proves selectors are driven by retimed D: DQP cluster18 through R234 to base150, DQN cluster17 through R236 to base151, shunts R235/R237 and parallel MIM275/276. Q131/Q132 and Q149/Q150 share those base clusters.

Paths are A->AD, C->CD, D->S0 and D->S1. Seven frozen-reader, thirteen operating-point and eight transfer controls run first. An authenticated actual-composition preflight verifies all four native paths, receiver terminals, collector polarity, series resistors, parallel MIM and real ground shunts before the separate archive job can run. The extracted native composition must equal that preflight input.

Full-wave diagnosis reproduces all124 HBT metrics, all6 stages and1530 delays and phase/VI without changing original acceptance gates. It additionally records A->C and B->D retimer crossings and expected sequence index lags. Diagnostic hysteresis is50mV for sampler/buffer and10mV for base, with causal125ps event matching; missing, ambiguous, preceding and following events remain visible. These diagnostic thresholds are not electrical acceptance limits. Pipeline crossings alone do not prove retiming correctness.

The sampler100mV/37.5ps and XOR100mV/75ps gates remain unchanged. Neither the preflight nor this analysis establishes accepted PHY, fresh PEX, new physical layout, or final chip timing.
