# Fresh route after native fanout repair

Run 39409367521 failed actual OpenROAD DRT connectivity checking before RC
extraction or final STA. The saved native log lists many disconnected data
nets, including nssoc_coverage_data_local_115. No timing closure was obtained.

The verified source ECO added 1684 positive buffers and legalized changed
instances. Its detailed wires and guides were inherited from an earlier
placement/topology. The next candidate removes only ROUTED non-clock data
wires, preserving the original source ODB. Native exported DEF comparison
checks all non-wire physical content and every unrelated net record; a
persisted ODB readback repeats this check. Three corruption controls cover
physical header, data connectivity and fixed clock routing.

Native global routing now generates fresh guides from the current pins
before detailed routing. Signal/clock layers, 20 percent routing adjustment,
200 congestion iterations and zero congestion waiver are explicit. The
existing fixed-clock antenna handling and post-route clock-wire proof remain.
Every original functional, topology, DRC, antenna, disconnected-pin, nominal
RC and three-corner STA gate remains in force. The original 20/4/8/8 ns clocks,
5 percent derating and 20 SRAM macros are unchanged.

The use of a separate global-routing stage follows the native tool interface:
[OpenROAD global routing](https://openroad.readthedocs.io/en/latest/main/src/grt/README.html).
Whether this resolves the observed failure must be established by the new
native run; neither this preparation nor old estimated timing is acceptance.
