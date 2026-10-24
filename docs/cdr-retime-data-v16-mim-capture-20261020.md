# Retimed CDR v16: fresh MIM-aware capture

The revised Metal3/4/5 access geometry passed native DRC and both hierarchical
and flat LVS in run 39334427158. GDS SHA256:
c920186862bde235868d3fa009fedcff868246750f0fa38874e3c6b42ba7255e.

The next cloud capture is bound to extraction run 39335172776 at
bb3819f5c2e6081fb754f7a5aa1a0b349b47aeb9. It waits for planes, wire-inputs,
binding and RC to finish successfully and verifies their release digests,
source commit, run attempt, stage names and cross-stage physical provenance.
It never restarts a live prerequisite or consumes old v15 R/C.

The unchanged native capture controller restores all 946 physical points,
111 conductors and 484-device intrinsic binding. It includes the eleven
actual MIM masks, moves bottom-plate references only to native bottom access
metal, checks original native cluster ownership and preserves the five
actual corruption controls. Source adaptations are checked byte-for-byte.

This is a capture step, not qualified PEX or PHY acceptance. A successful
capture still needs the original raw wire/MIM audit, compact-model composition
with each intrinsic capacitor included exactly once, and the original loaded
256-bit electrical gates. The prior failed sampling results remain retained.
Added metal capacitance and retained via resistance must be measured anew.
All CAD and output storage remain on GitHub-hosted runners/releases.
