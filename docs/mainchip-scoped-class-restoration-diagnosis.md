# Saved route class restoration diagnosis

The saved routed DEF was compared on GitHub in run41302468053/source7e465ee49cb69783919e14ba17fa3f6dd76c3f09 after26 independent source controls. The complete751995332byte native archive and all728member hashes/censuses authenticated. No CAD or routing was rerun.

All143820nets were present in the same order. The original antenna plan has608owners/1351diodes; the separately validated routing scope adds220counterparts, retaining1691protected clock/fixed records. Of143212 selected original-class records,142878remainFIXED,114remainunwired and exactly220changedFIXED->ROUTED. Exactly these220counterparts changed normalized geometry. Zero normalized changes outside counterparts, zero connection-prefix changes and identical bytes outsideNETS.

This is an ownership-consumer bug: targeted clear deliberately reclassifies the220counterparts toROUTED, but inherited restore_plan still requires every originally non-antenna selected record to beFIXED. The fix must retain the220currentROUTED geometries while restoring all other temporary classes through the original function. Original classes, route ownership and diode ownership must remain separate. Do not rewrite the608-owner antenna plan to828.

Next implementation must validate complete scope/plan digests, original/current counterpart classROUTED, the complete unchanged selected geometry outside routing scope and all connection identities. Native OpenROAD import/readback and the original restored-audit,1691clock,route delta,two connectivity modes,diode,power,DRC/antenna and final timing gates remain required. Source planning alone cannot close those gates. The scoped restoration fix and original native audit adapter are now implemented on sourcebe65a271b066faeffee86237fa879f5f96b70273. Independent controls41304921000 passed34 core cases and2361 original source pins. Native run41305082558 is pending actual result; no physical or timing closure is claimed.

Use producer41292673925/release430474717 rawODB SHA256b87a2d43fe33dd8ca99f0faa2bdf38337ae30d6c5b72a337472919ac57f64e63. Its397routerDRC remain open. Preserve the result instead of rerouting828nets blindly. ODB geometry is not proof of optimizer-state continuation.

Full per-record catalogs remain in release430540422, with asset digests authenticated against complete-output-index.json. Safe text evidence and exact source are in docs/evidence/route-class-native-terminal-41302468053. The91.8MB all-selected catalog was kept on cloud. Failed fixture/readout attempts41301583231/41301914645 are preserved separately.
