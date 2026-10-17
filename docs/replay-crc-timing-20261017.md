# Replay EOP CRC timing change

The slow setup path in the targeted banked chip runs from ACK encoder busy through packet selection to retry count. The replay controller previously put the eight-step CRC32 update before its end-of-packet validity comparison. The new Boolean expression reverses the fixed DEBB20E3 residue to00BE26ED and compares it to the current CRC state XOR the input byte. CRC state updates, packet storage, error handling, clocks and cycle latency are unchanged.

Hosted run39041074376 proved the Boolean predicate for every defined41-bit state/data/SOP combination and full unmasked sequential equivalence for DEPTH2/3/4 and MAX_BYTES18/38. It proved642/1289/1610 equivalence points with none unproven. Wrong-residue and wrong-byte SAT controls produced counterexamples. Original baseline and candidate each passed7 replay plus4 reliable-packet port tests; wrong residue failed all7 replay tests with no skipped cases.

The canonical source is exactly the proven candidate SHA2561a15c0b9d6cfdfbf5ebed9a61c52901e126ca826008d167ff96bea4218a8f4dc. The pre-change fixture preserves the source used by physical bootf65c0c35. Complete reports and original failed-control captures are pinned in `evidence/replay-crc-exact-adoption-20261017.json`.

This adopts a functionally proven RTL optimization, not a timing-closed chip. Fresh native protocol tests, system/Ethernet MBIST boot, source-bound mapping and physical implementation must pass before replacing the existing layout. The ongoing clock200 routing trial remains bound to its older proven netlist. No clock relaxation or false path is introduced.
