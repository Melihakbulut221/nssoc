# Cloud continuation — authenticated core route completed

PCIe and Ethernet remain out of the production target by user decision. Core target remains 50 MHz, 20 ns, 5% derate.

Core route 44263061910 completed successfully. Its native and summary ZIP digests, matching result bytes, all 126 output hashes and ten protected repository source files were verified independently. Native routing reports zero DRC and zero antenna violations; these are not foundry signoff. See docs/evidence/core-only-detailed-route-admission-20261118.json.

This branch pins those exact artifacts for fresh nominal RC extraction and native slow/typical/fast SPEF timing. No archived inherited SDF or pre-route metrics may be promoted to final timing. Dispatch cloud-evidence-summary.yml on this branch, then verify the actual run/artifacts before accepting any timing metric. Qualified RC min/max and SRAM model temperatures remain open.

Pad repair is independently running in 44302346053, source 0842574f18a3bc53b15d9438d08bebb940964a09 on codex/core-only-chip-pad-repair. Do not duplicate it. Its output is only a legalized candidate until connectivity audits, fresh routing, RCX and timing pass.

General checks 44302348083 are retained. Superseded checks 44300151585, 44299676431 and 44298692859 were cancelled only after API comparison proved their heads are ancestors of 0842574f. No physical run was cancelled.

Next: inspect extracted core timing; qualify routed functional boot using scripts/cloud_core_only_routed_boot.py with the same artifact pins; finish pad electrical repair and fresh parent routing; integrate actual core netlist/SPEF into parent timing with real IO/CDC constraints. Full SRAM transistor LVS, foundry DRC, Liberty/RC qualification, DFT/package/ESD and manufacturing approval remain unclosed.

## Pad repair power correction
Run 44302346053 failed its strict audit: 145 inserted buffers on 20 selected pad nets were unpowered because repair preparation marked VDD/VSS do-not-touch. Native global_connect explicitly warned ODB-0382/0379 and skipped these rails. Native artifact 14426956887 SHA256 6e9cae12e1b0b6975dd3cf4f2cbf555e66971fd8ed7a188ac1c874ce83bf9f43 and all output hashes were verified. Existing geometry passed before the power check. No candidate accepted.

The corrected preparation protects non-target signal nets but leaves native POWER/GROUND nets available to global_connect. The audit still rejects missing or wrong buffer supplies, original geometry changes, logical splits/shorts and any unexpected buffer source. Original net flags are restored after the audit. Fresh physical/timing proof remains mandatory.

Core extracted timing run 44303529050 uses head 20bedd917c6f98bf6afeea1ee991d2ca4c4f03ea. Routed boot run 44303624006 uses head 2c2bc900d3ad9034d78c87d71434eb98533f383d. Both use the pinned routed core artifacts; preserve live jobs.

## Prepared pad repaired routing
This branch contains a route runner requiring docs/evidence/core-only-pad-repair-admission.json with independently verified artifact identities and buffer count. Admission is deliberately false until run 44303799761 completes and its outputs are audited. Do not dispatch unadmitted data. The runner restores the exact unrouted ODB under a byte-checked compatibility filename, derives required routed net count as 1794 plus admitted new buffers, and retains native four-rail PG, exact identity, exact coincident pad omission, native DRC and visible geometry audits. No timing is claimed.

## Pad repair admitted for route only
Run 44303799761 passed: 145 powered buf2/buf4 cells added to 20 selected pad input nets. Both archive digests, native/summary equality, all 17 output hashes and protected repository sources were independently verified. Original instances/pins/PG geometry and contracted connectivity were preserved. The route admission is now pinned in docs/evidence/core-only-pad-repair-admission.json. Expected routed net count is 1939 plus 76 exact coincident pad connections. This is not acceptance of extracted timing or production readiness.
