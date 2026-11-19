# 21-buffer fresh nominal RC result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44567580014, head `2b14595809d4575f10b383dda6e5be77ca8b4da2`, completed successfully. Artifact `14554237236`, SHA-256 `77286a8405133cc945d5b8100925d6d13ebe18227737f3e3d67eb4366d5cf868`; all 142 output hashes independently verified.

Fresh ODB `12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458`; netlist `ab0c1367a61b3226396ee082768469ea2eddddf5772455cf1ecb38bff50ff1ca`; DEF `5489bca1a2b29d9387a7f088d2ebb1d5ea404f8f0f7e00d4f79151cd34ab0e98`; nominal SPEF `35efffc741298894c575352351a59d3ad8dd58eaf965851c5bda4a3737054f9c`. The 20 ns clock/5% derating constraints remain unchanged, SDC `f121116a72150c56126ac3d8dc4fda946e6d0040984e9264ef3d877171029de1`.

| Standard-cell corner | Setup violations | Hold violations | Setup worst slack ns | Hold worst slack ns | Slew | Fanout | Capacitance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| slow 1.08 V 125 C | 0 | 0 | 0.0215383273 | 0.4454192696 | 424 | 207 | 49 |
| typical 1.20 V 25 C | 0 | 0 | 7.4320516289 | 0.1855849971 | 0 | 207 | 50 |
| fast 1.32 V -40 C | 0 | 0 | 10.3033744453 | 0.0371606090 | 0 | 207 | 56 |

Relative to the prior six-buffer result: slow slew 456→424, all-corner fanout 210→207, capacitance 52/54/60→49/50/56. Complete pin-level comparison is required to distinguish removed and new violations.

All 1,410 cumulative added diode exports match; the 44 moved diode exports separately match. Actual preparation and baseline diode map verification also passed run 44567073873, artifact 14552601238, SHA-256 `c087cc956123c59fe350ce6538d6b4250abbbc43c9ba3384928f4ddd0c372cbf`.

The 1,403 unannotated drivers classify as 1,288 disconnected outputs plus 115 connected outputs without sinks; there are zero loaded unannotated drivers. This diagnosis does not prove complete timing coverage. Nominal-only extraction is not qualified RC minimum/maximum analysis. Remaining electrical violations, macro timing qualification, full-chip/pad timing, transistor LVS/foundry DRC and manufacturer approval remain open. This is not production acceptance.
