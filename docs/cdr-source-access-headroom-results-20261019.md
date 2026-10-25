# Measured CDR headroom failures in actual XOR macros

Cloud review39309462607 passed for both nominal early and late captures. All116original HBT checks reproduced exactly from every saved native sample; all device geometry owners were unique. The physical source-contact candidate remains electrically rejected.

All six early failures and both late failures belong to the two physical XOR macros x and y. Early failures are xd0129/xd0133/xd0135 in x and xd0147/xd0151/xd0153 in y; late failures are xd0129 and xd0147. The worst device is xd0129: early VCE0.386162075932V at19.62640625ns (VC1.699017099127V, VB1.732865874653V, VE1.312855023195V); late VCE0.386461451047V at19.63171875ns. Both are below the unchanged0.4V gate. At the early worst sample the actual collector current is -0.127067448microampere, so the minimum occurs in a nearly off transistor; it must not be misreported as a high-current overdrive or proof of physical damage. The original gate remains enforced.

The new measurement locates a collector/emitter headroom issue in the real XOR network; it does not establish causality from the sampler source contacts. Before another layout change, inspect shared XOR collector supply/load and emitter/input-commonmode paths at these exact samples, then validate any schematic change, native DRC/LVS, freshly extracted R/C and original loaded checks. Sampler data failures also remain. Do not promote the source-contact candidate or claim recovered-clock, PVT, qualified PEX or fullPHY acceptance.

Original1GBwaveforms remain in their source cloud releases; only diagnostic reports and source pins were published anew. Local project directory is empty and no local CAD process is running.
