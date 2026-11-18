# Native pad controls outcome

Run44371726618/head74064e31fddbc80df68236fae25ef372eec23ce3: five of six native cases completed50ns without numerical diagnostics. Only0-turnoff aborted at22.7529ns; its printed waveform has two repeated timestamps near the abort and is not accepted. Both static polarities show approximately2.1mA enabled drive and-2.34nA disabled clamp current. The completed1-turnoff reaches1percent of initial current1.8725ns after enable midpoint; this is a current-decay metric, not a Liberty voltage transition or qualified external load contract.

Artifact14459915702 SHA2561ca5633e5a79e792d6efe6148b4b787b5ac279dc28e5d10b34f47ce9d3da3a86: all79 output hashes and exact runner source verified. Independently checked finite six-column waveforms and increasing time/full50ns for all five complete captures. The aggregate correctly failed.

Next target the low-drive turnoff transient; do not repeat unchanged static controls or increase Newton iterations blindly. Alternative solver diagnosis requires native readback, unchanged models/tolerances and subsequent capture/step convergence. No partial capture closes22slow pad transition violations. Physical parasitics, Liberty qualification and externalIO budgets remain open; package/PCB/devices are unselected.

Core route44337630426 remains independently active; admit exact route artifacts before staged extraction. Native six-case source is tag cloud-pad-six-controls-native-20261118. Earlier duplicate general checks44367860149 were cancelled only after exact comparison proved unchanged RTL/formal sources against live44365289855, releasing capacity. No physical job cancelled.
