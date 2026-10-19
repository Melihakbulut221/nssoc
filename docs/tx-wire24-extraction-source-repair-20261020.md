# Repair candidate receipt comparison before native extraction

Run39340008926 stopped before native RC extraction because the adaptation
compared the new physical report against the old baseline receipt.
The complete failure is retained. No RC or electrical result was produced.

The corrected assertion compares the restored candidate report with its
exact new candidate receipt. Its source SHA, release summary/archive hashes
and every member hash remain required. The old baseline is still independently
checked for placement, child, route and source ancestry; the new candidate
must satisfy all28width-change, GDS, schematic/LEF and native physical gates.
Only the erroneous expected receipt variable changes. No failure is ignored,
and no geometry, RC audit or electrical threshold is changed.
