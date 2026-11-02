# Actual drain M2/M3 reinforcement candidate

Complete current fullwave diagnosis41424462139 reproduces sourceM2 loaded41422407076 rejection: actual HBT emitter-to-MOS drain losses51..57mV remain. Current native physicalmap41424965941 authenticates978anchors/24530resistors/13conductor unions and identifies narrow same-net M2/M3 drain routes.

Target exact8MOS drains3/4/5/6/32/33/34/35 on the original two emitter nets. At each actual anchor(x,y), retain every original device/material and add M2+M3 rectangle[x-150,y-200,x+1250,y+17800]nm, attached at original lower and upper17.6um M2/M3 accesses. Insert190nm Via2 squares on480nm pitch at x offsets0/480/960 and y0..17280, only when existing/new cut spacing240nm and enclosure50nm in both owned metals pass. Require at least70cuts on EVERY drain. Retain all original dense Via1 cuts; the earlier Via1-only failed candidate remains rejected, its gate is not changed.

All103original geometry controls and all acquisition/guard/publication bodies remain unchanged. Use the original attached-metal predicate for M2 against foreignM2/Via1/Via2 and for M3 against foreignM3/Via2/Via3. Check foreign-metal240nm and via50nm clearance, exact5nm grid, original extent, each real native owner and allcandidate mutual spacing. Only layers10/29/30 may change. Roundtrip serialized GDS and reverse additions to every original layer exactly.

This generator is only a guarded candidate, not electrical/physical acceptance. Require full560DRC/deep-flatLVS13, new whole canonical partition proof, actual freshRC and unchanged loaded gates; also via-current/EM/PVT checks. No bias/primitive/netlist/gate changes. All native work and failed evidence remain GitHub-only.
