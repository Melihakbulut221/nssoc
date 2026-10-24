# Compact driver geometry after the rejected wide loaded study

Wide loaded run38886315151 completed its original34ns test and failed. The avdd wire reduction55.4577→18.2673ohm improved CMOS common-mode to1.84645–1.85225V, but output wrong-sign samples rose32→124 and147samples fell below100mV; minimum margin−264.679mV. The candidate is rejected. All672MOS pass,12HBT fail. No sampling phases, source bits or electrical limits change.

The next real physical candidate preserves every raw device, intrinsic tie, resistor value, Metal1 access and imported material geometry. It shortens wiring using a24um HV instance pitch (from40), buffer translation x144 (from200), resistor start196/pitch28 (from260/40), and Metal5 spine start60/pitch7 (from100/8). M3/M4/M5 widths and upper2x2via arrays remain unchanged. Cell translation is not cell scaling; source MOS geometry and84raw fingers are unchanged. Native DRC and all raw/aggregate deep/flat LVS checks plus seven real corruptions must pass before any new extraction.

This geometry is unverified until the cloud receipt completes. All wire RC, terminal planes, LEF and loaded electrical evidence must be regenerated for a passing compact GDS; neither the old nor wide network can be substituted. Full serial PHY and chip timing remain open.
