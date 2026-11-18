# SRAM enable pin and driver investigation

The CTS8 native probe identified bank2 A_MEN as the remaining slew pin and sg13g2_nor2_1 as its driver. Macro origin is NOT pin position: no long-wire diagnosis can be inferred from the origin and driver coordinates alone. This additional native read-only probe reports the actual A_MEN master pin rectangles, macro placement/orientation/DB units, SRAM size and available NOR2 master/Liberty cell variants. It retains the authenticated CTS8 restore and slow-corner STA.

No SRAM enable ECO is applied or claimed. Available master variants alone do not establish Boolean equivalence, permitted use, faster timing or physical acceptance. Read the actual native geometry and Liberty timing before choosing the repair. The clock split run44253264552 and routed repair44252197610 remain independent and must be preserved.
