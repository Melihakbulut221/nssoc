# Short-branch physical hold repair

The exact146 candidate still has90hold endpoints and global setup failures. Source38895551929 traces each physical gate input on a fast short path and measures its max path to every reachable endpoint at slow/typical/fast corners.88inputs have positive setup in all three corners; two do not and remain untouched in this experiment.

Insert one positive delay cell per measured input branch, retaining every existing cell location/master and every other connection, power wire, NDR and external pin. Seven branches with less than1ns minimum setup headroom use sd1;81use sd3. These are explicit sizing hypotheses, not a claim that timing fits. The new candidate has234cumulative added cells:88new plus146parent cells.

The workflow must pass exact source/geometry guards, actual legalization, full logic proof with an inversion rejection control, selected-net global guides, full-chip detailed routing, fresh nominal extraction and the original three cell corners without changing SDC. Preserve all failed results. After it finishes, independently remeasure every endpoint and geometry/antenna/annotation on its exact published hashes before adopting any improvement. Full timing, qualifiedRC, complete serialPHY and production approval remain open.
