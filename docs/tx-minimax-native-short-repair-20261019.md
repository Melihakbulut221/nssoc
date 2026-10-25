# Native two-short diagnosis and physical candidate repair

Run39260578443 read the exact failed1674device LVS database and bound534 actual macro/public TopMetal2 anchors. Two merged native logical groups were found, with no opened logical nets:

- p16_11n and p8_7p share native cluster180.
- p16_11p and sp8_7n share native cluster190.

Actual p16_11_on anchor is (424985,8575930) database units; p8_7_op is (1124985,8577535). The horizontal data stub and the shifted macro output are only1.605um apart inY. The p16_11_op/p8_7_sn anchors have the same1.605um offset. The chip reference and transistor counts remain unchanged. This is a real routing collision, not a reason to waive LVS or alter the schematic.

The repair retains all other solved macro rows and moves p8_7 from7808.605um to8100um, on the original300mod600um row lattice used by this stage. All60 routes and channel allocations are regenerated; leaf/final rows and native child shapes stay fixed. The original minimax objective is still a lower bound for its unconstrained planning problem, not an optimality claim for this repaired candidate. Every new route length is recorded.

The new native physical run must repeat the original full DRC/deep-flatLVS/fault controls. The repair is not accepted from coordinate spacing alone; private metal collisions, new routing interactions and increased p8_7 load remain possible. Any physical pass requires fresh RC and full electrical qualification. Full serialPHY/mainchip/finaltiming remain OPEN. All work and evidence stay in GitHub.
