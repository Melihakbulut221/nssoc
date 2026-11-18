# Cloud continuation — authenticated core route completed

PCIe and Ethernet remain out of the production target by user decision. Core target remains 50 MHz, 20 ns, 5% derate.

Core route 44263061910 completed successfully. Its native and summary ZIP digests, matching result bytes, all 126 output hashes and ten protected repository source files were verified independently. Native routing reports zero DRC and zero antenna violations; these are not foundry signoff. See docs/evidence/core-only-detailed-route-admission-20261118.json.

This branch pins those exact artifacts for fresh nominal RC extraction and native slow/typical/fast SPEF timing. No archived inherited SDF or pre-route metrics may be promoted to final timing. Dispatch cloud-evidence-summary.yml on this branch, then verify the actual run/artifacts before accepting any timing metric. Qualified RC min/max and SRAM model temperatures remain open.

Pad repair is independently running in 44302346053, source 0842574f18a3bc53b15d9438d08bebb940964a09 on codex/core-only-chip-pad-repair. Do not duplicate it. Its output is only a legalized candidate until connectivity audits, fresh routing, RCX and timing pass.

General checks 44302348083 are retained. Superseded checks 44300151585, 44299676431 and 44298692859 were cancelled only after API comparison proved their heads are ancestors of 0842574f. No physical run was cancelled.

Next: inspect extracted core timing; qualify routed functional boot using scripts/cloud_core_only_routed_boot.py with the same artifact pins; finish pad electrical repair and fresh parent routing; integrate actual core netlist/SPEF into parent timing with real IO/CDC constraints. Full SRAM transistor LVS, foundry DRC, Liberty/RC qualification, DFT/package/ESD and manufacturing approval remain unclosed.
