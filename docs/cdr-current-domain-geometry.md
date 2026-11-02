# Actual current MOS geometry audit for independent-unit layout

This cloud job authenticates physical41435641296/source262ac9b4d9142be6235c68d279c67aac9b92e3a8 and its complete native archive, selects exact current GDS/flatLVS and qualification, and reads all500 native matched devices. It binds all50 original MOS to actual GDS PCell enclosures and D/G/S/B shapes, preserving complete observations and failures. It does not generate a new layout or claim650-device physical verification.

The new model-range proposal uses independent units; original source/drain areas, perimeters, contacts, substrate taps, spacing and external wires must be accounted for in new geometry. This audit supplies the actual current placement/terminal ownership input, rather than historical geometry IDs. Every mapped terminal, extracted parameter and schematic identity must match current correspondence; an ID/order change is an explicit failure to diagnose, not a reason to skip mapping.

Native GDS/LVS remain cloud-only. Complete output is preserved in an independently reserved exact-source release; derived JSON is separately available. Actual electrical trial41528163238 is independent and remains subject to full gates. No new layout, freshRC, closedloopCDR/PLL, complete serialGen3x4 or finalSTA acceptance is implied.

API references: [KLayout terminal shapes](https://www.klayout.de/doc-qt5/code/class_LayoutToNetlist.html#method55), [native cross-reference](https://www.klayout.de/doc-qt5/code/class_NetlistCrossReference.html), [device geometry](https://www.klayout.org/downloads/master/doc-qt5/code/class_Device.html). Execution uses pinned klayout0.30.4.post1.
