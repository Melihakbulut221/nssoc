# CDR v40 selector-area experiment: all four native cases rejected

Run39878490784/source28d16083644ae3aea1d9763f27b62bb345c2ea95 completed all four original34.25ns captures:113475rows,1104columns, native exit0, no numerical diagnostics, unchanged sources. No candidate passed the original data/phase gates.

| Candidate | Phase | A minimum / delay | C wrong samples / delay | D wrong samples / delay | Device gates |
|---|---|---|---|---|---|
| slave_select4 | early |89.134mV /38.594ps |46 /54.219ps |64 /51.094ps | pass |
| slave_select4 | late |86.407mV /38.906ps |30 /51.406ps |64 /51.094ps | pass |
| all_select34 | early |86.374mV /38.906ps |46 /53.594ps |64 /50.469ps | fail |
| all_select34 | late |83.522mV /39.219ps |36 /51.094ps |64 /50.156ps | fail |

The B sampler passed in all four cases. Increasing selector area did not repair the A/C/D failures. The all_select34 early case also falls to0.373335V minimum active HBT VCE, below the unchanged0.4V gate. This is a measured failure, not a solver or timeout failure.

Do not promote these candidates into the mainchip or claim a fresh physical implementation. The frozen-RC screen retained the inherited54um MOS diffusion hypothesis; any new successful electrical candidate still needs real placement, native DRC/LVS, fresh extraction and the full original loaded simulations. Future changes must account for both added clock loading and the measured headroom loss, rather than repeatedly increasing selector area.

All raw failures, control checks, exact assets and hashes are preserved; compact results are in docs/evidence/cdr-v40-four-full-screen-rejections-20261023.json.
