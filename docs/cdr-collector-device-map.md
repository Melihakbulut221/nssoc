# Loaded collector devices mapped through actual native LVS

The collector Via2 candidate passes physical DRC/LVS but its unchanged full loaded transient 41441047354 is electrically rejected. Native HBT IDs 61/62/115/116 have insufficient Vce. Driver IDs 54/56/106/108 and tail MOS IDs 3/4/5/6/32/33/34/35 need source-level identification before a circuit change.

Read the exact physical41435641296 flat LVS database (2760554 bytes, SHA256 9df6ea3e90bccaebe216834488154f680317934560ed99ad0b1a9be1ff22da37). Authenticate the complete existing physical release, all member bytes, existing audit and explicit deck verdict. Require all 500 native device pairs to match, a bijection of IDs, exact primitive census and critical models. Record both schematic and layout names, all parameters and terminal nets. Cross-check all 1446 actual loaded native terminal identities against freshRC41439516945 metadata and all 500 composition records. No assumption that native numeric IDs encode schematic names. Symmetric equivalent devices may be paired differently by LVS.

This is a read-only observation, not a rerun of extraction, electrical simulation, signoff or layout editing. Preserve original failed waves and all acceptance gates. Ten source-only negative controls reject partial census, wrong IDs, duplicates, model mismatch, missing source names and nonmatching status. Native data and execution stay on GitHub; outputs are derived JSON only.

API references: https://www.klayout.de/doc/code/class_LayoutVsSchematic.html and https://www.klayout.de/doc/code/class_NetlistCrossReference.html .


First attempt 41449736667 authenticated the complete physical capsule and reached native LVS device enumeration, then failed because Net has no id() API. Device IDs remain unchanged; net identity uses the documented cluster_id/name/expanded_name fields already used by the actual loaded-terminal binder. Remove only the redundant invalid Net.id call; all source controls, terminal comparisons, pair census and failures remain preserved.


Second attempt41450082352 read and bijectively validated all500 native LVS pairs, but failed the exact loaded1446terminal binding. Preserve complete observed native pairs and actual/expected terminal metadata before validation so any remaining mismatch is diagnosable. The original planes generator exports raw device-class names, whereas the mapping initially normalized them to lower case. Preserve raw native model spelling separately for the exact native-terminal comparison; normalized model names remain used only for the published primitive census and loaded-SPICE model matching. No terminal identity gate is removed.
