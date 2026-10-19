# First all-leg minimax candidate: actual LVS rejection

Run39259571215/source96b1338572b980892f896a2266e2e00e938225f4 completed native generation and independent drawing/placement checks, then failed the original strict deep transistor LVS gate. Native and reference device counts both remain1674; the deck explicitly reports NoMatch with no extraction diagnostics. Full DRC and subsequent fault stages were not reached. This candidate is not physically accepted.

The actual generated60leg layout reduced the maximum route centerline4174.000→2017.405um and total91746.400→77805.580um. All31 actual placements/frozen native child drawings and full normalized device cards passed the independent geometry checker. Its three corruption controls were rejected. These results verify the intended geometry change, not connectivity or electrical behavior.

Immutable fullfailed receipt: docs/evidence/tx-v5-minimax-first-lvs-rejection-20261019.json. The new tx-v5-minimax-lvs-review-cloud job restores that exact GDS/LVS database and binds all534 macro/public metal anchors through native KLayout probe_net. It reports every merged logical net group, opened net and actual device terminal cluster, preserving the original failure. No reference edit, LVS waiver or rerun of the same failing layout.

After identifying the concrete overlap/open, correct the actual routing/placement planner and rerun all original physical gates. Fresh RC/fullwaves remain mandatory after physical acceptance. Mainchip39243328773 remains separate and live lastcheck; full serialPHY and final timing remain OPEN. Cloud-only.
