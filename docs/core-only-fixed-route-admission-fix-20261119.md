# Fixed-route admission correction

Run 44434590011/head 6990e4c933bc871fd3b02bdc1f468df25dd38232 failed at the post-route clk_i preservation assertion. Artifact 14489057646 SHA256 7900bbdaec121ea500c0a95231bec7953c7991450be134efed9e31a006a5d33a and all 27 outputs were verified. The exported pre-route clk_i was still ROUTED, with zero FIXED clauses. The previous normalized geometry check was insufficient to prove fixation.

Pinned OpenROAD dcf36133 src/odb/src/defin/definReader.cpp registers NETS callbacks only for DEFAULT or FLOORPLAN mode; INCREMENTAL does not import NETS. Replace read_def -incremental with read_def -floorplan_initialize for sparse NETS-only patches. Require FIXED in the native exported record, forbid residual ROUTED clauses, and independently decode each expected net's first path wire type, which is what DRT uses. A native encoder fixture verifies that changing dbNet flags alone is rejected and encoding FIXED is accepted. Restored ROUTED types are checked after routing too. All original connectivity, geometry and DRC guards remain.

Clock experiment 44435678929 carried the same confirmed importer bug and was deliberately cancelled; cancellation is due to evidence, not slowness. Apply this correction there only after native fixation admission is proven. Neither rejected attempt is timing or production evidence.
