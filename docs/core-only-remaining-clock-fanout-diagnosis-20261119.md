# Remaining clock fanout diagnosis — 2026-11-19

Status: measured baseline diagnosis, not an implemented repair or production acceptance.
PCIe and Ethernet remain excluded; retain 50 MHz / 20 ns and the existing 5% derating.

## Authenticated source

Inventory run https://github.com/Melihakbulut221/nssoc/actions/runs/44571330223
at 06f837a24a95b979f1bb316b9e42a3546e613d4b.
Artifact 14553853079 SHA256:
5bae77546b494ad46ac8d7f83b10ea7420c596fa7c9c4f1808ac9c7ce7232385.
The archive digest and every output digest were checked on this review.
Source ODB: 12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458.
This is the 106693-instance baseline before the 413-buffer signal experiment.

## Findings

Both clock drivers are sg13g2_buf_16. All three nominal-RC PVT reports
show actual fanout 9 against limit 8 at each driver:

| Net | Driver | Loads |
| --- | --- | --- |
| clknet_1_0_0_clk_i | clkbuf_1_0_0_clk_i/X | Four SRAM A_CLK pins, clkload0/A, ANTENNA_2520/2548/2549/2565 A pins |
| clknet_7_92__leaf_clk_i_regs | clkbuf_7_92__f_clk_i_regs/X | Six leaf-clock buffer A pins, nssoc_sta_i_66976/CLK, ANTENNA_2521/2550 A pins |

The six leaf buffers are clkbuf_leaf_584/603/617/618/619/620_clk_i_regs.
These are CLOCK nets. The ongoing signal-only candidate intentionally preserves
all 2113 original clock routes, so that candidate alone cannot close these two
known clock fanout violations. Driver resizing alone does not reduce fanout.

## Required next experiment

After the current signal routing candidate has passed admission and fresh RC,
re-evaluate these exact loads in its ODB and STA reports. Investigate balanced
clock branching with at most eight loads per driver, preserving functional
clock connectivity and positive clock polarity. Place branches according to
actual pin geometry; instance origins in this inventory are not macro pin locations.
Do not hide the violation by increasing the limit, removing protective diodes,
changing fanout weights, or buffering a diode-only dummy branch.

Clock buffering changes insertion delay and skew. A candidate needs legal
placement, real power contacts, clock/diode connectivity checks, an explicit
allowlist of changed clock nets, protection of other routed nets, native routing
DRC, independent geometric connectivity/short checks, and antenna revalidation.
Re-extract RC and check setup and hold in every existing corner, including all
SRAM paths and the affected register subtree; retain unchanged clock period,
derating and timing exceptions. Nominal RC passing is not qualified RC-min/max
or whole-chip production signoff.

No clock edit or clock route is dispatched by this record. Ongoing route:
https://github.com/Melihakbulut221/nssoc/actions/runs/44573258297
at 26b92963b1fa7080ae6baa6c5a5570ea288b3713, observed in progress.
