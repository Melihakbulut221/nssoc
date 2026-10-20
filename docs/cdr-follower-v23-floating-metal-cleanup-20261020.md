# Native floating-metal rejection and physical correction
The new parent passes transistor LVS, but extraction run39474349718 rejected
metal components with no attached native device terminal. No RC acceptance was
issued; dependent capture must stop on that failed prerequisite.
The cleanup starts from exact passed parent39473538977. It independently rebuilds
the metal/via graph, matches every component to the native unsimplified LVS net,
and records every terminal-free component and its complete polygon inventory.
Only components with no device terminals, no public ports and every metal/via
polygon exclusively owned by the parent may be removed. Any child/device
intersection aborts. All remaining parent shapes, labels, instance transforms,
device geometry, circuit and external LEF are preserved; serialized geometry is
checked against the exact declared subtraction. The same full native DRC/LVS
and all nine fault controls then run again. Fresh extraction must retain the
original strict no-floating gate. This is a correction of real geometry, not
a waiver or a capacitance approximation.
