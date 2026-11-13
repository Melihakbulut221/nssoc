# Full cut10 native MBIST boot attempt

Current timing/combined RTL, cut10 MEM_RDREG=2, MBIST_PIPE=1 and unchanged execute/PMP/PCIe/Ethernet knobs. SOC_SRAM_MBIST=1 enables actual system and both Ethernet memory tests before all 28 firmware checks. Previous run 43475775445 did not enable system MBIST.

Require actual MBIST busy-to-done handover, both Ethernet done bits, no failure flags, and firmware completion using the corrected reporter. No forced status or ROM/RAM preload. PCIe is link-down; traffic, SDF, serial PHY, physical faults and direct post-route simulation remain outside this test.

The 3,000,000-cycle ceiling preserves complete registered-compare MBIST and firmware sequences. A 20,000-second simulator budget leaves preparation/preservation room within the 360-minute hosted job ceiling. A timeout is failure/incomplete evidence. No MBIST completion claim until actual result and source bindings are verified.
