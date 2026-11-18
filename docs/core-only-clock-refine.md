# Zero-fanout routed repair: verified improvement, closure still open

Run44256809783/source0a055a1269f48e386e01b95eada858ae25671429 completed successfully as execution. Independently verified all archived output hashes and six fresh corner metrics. All three final STA logs confirm global routes and contain no EST-0026 warnings. See docs/evidence/core-only-clock-postgrt-20261118.json.

Final slow setup91, worst-1.06292ns, TNS-37.4915ns, improved from1092/-3.84906ns. Typical/fast setup0. Hold0allcorners; worst slow/typical/fast +0.496148/+0.213365/+0.0506166ns. Fanout0allcorners remains preserved. Slew24/0/0, capacitance2/2/2 remain. These are global-route estimates, not final extracted timing or signoff.

The continuation runner restores the exact original mapping/CTS/CTS8/clock split and this repair, verifies all archives/protected sources/fresh metrics and starts the authenticated final database. It runs electrical repair and another200setup/1000hold search with rerouting and fresh corners. No constraint or acceptance relaxation:20ns/5%derate, four system SRAMs, PCIe/Ethernet excluded. Compare final fanout and hold as well as setup; none are automatically accepted. Old original-clock candidate has0setup/hold but748fanout; do not combine its metrics with this topology.
