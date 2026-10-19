# Saved mainchip route verification and next timing repair

The original native flow39161219456 returned0 and preserved detailed-route/RC/all-corner STA outputs, but its controller rejected final antenna report43net headings against an earlier route count36. Saved-state validation39198113984 now independently reproduces actual43violating nets and51violating pins against final antenna__violating__nets/pins and ANT0001/0002 summaries. Seven corrupted-report cases are rejected. The earlier36counter remains recorded; it cannot authorize signoff.

The unchanged native ODB topology comparison passed for all146728 original cells: masters, locations/orientations, pins, nets, NDRs and ports preserved; only permitted antenna diodes added. Four actual comparison mutations rejected. This is not transistor LVS. Native routingDRC and critical disconnected pins are zero. Final antenna counts remain nonzero.

Original20/4/8/8ns clocks, propagated clocks, uncertainty and derates remain. Slow setup9676violations/WNS-20.719766ns and hold5/-0.509508ns; typical setup7865/-6.616752ns and hold13/-0.429901ns; fast setup3720/-3.039382ns and hold22/-0.372231ns. RC and script-integrity evidence remains in the receipt; no qualified-RF or full-chip signoff claim.

The slow critical path starts at Ibex register-file word9 bit22, includes fanout7880/buf1 with2.20ns output slew, followed by XNOR/XOR/NOR logic and further logic. The fast setup critical path starts at PCIe replay_read_onehot[44] and reaches pcie_tx_data_o[4]; it includes loaded buf1 stages then NAND4/NOR4 logic. Blindly resizing50buffers did not close the design. Next repair must use complete native cell-delay/logic-depth evidence, address these actual paths, preserve sequential behavior and remeasure all corners.

Worst hold starts at pcie_rx_valid_i and reaches slice1192852/D through the existing input62/AND/buffer/mux path. Original input min delay0.2ns and clock uncertainty0.25ns are retained. Physical delay insertion must be evaluated against both setup and hold; do not hide the violation by changing constraints.

The full max/min reports and firsteight native paths per corner/type are permanently retained, avoiding another route just to inspect failures.
