# Fresh RC for physical power128
Native physical39609833404 passes all560 DRC categories with zero markers,
deep/flat8088-device LVS, exact165 ports and original deliberate faults.
It also retains the original two1.9um TopMetal2 via-end width markers and
the measured full6um metal repair. GDS and flatLVS digests are pinned.

The new native wire workflow uses exactly the already qualified original8088
graph extractor with only the new GDS digest and distinct output/status names.
It must rebind every28620 terminal to the real physical netlist, retain703
metal components and768 electrical nets and prove no metal split/short.
The source-delta checker reconstructs the candidate exactly from frozen source.
This is geometry preparation, not RC or electrical acceptance.

After successful graph extraction, create fresh anchors, intrinsic extraction,
native RC and composition, retaining original fullwave and transistor bounds.
The previous8088 physical/RC/waves are preserved as the prior candidate.
Do not reuse old RC with new power128 GDS or claim full PHY signoff.
All scripts, CAD and outputs remain cloud-only.
