# Native Metal3 width rejection and real geometry repair
Run39333599063/sourceffe993f6cd2c8ba2ef0bbc09a72dfed3c6eadaf6 generated the exact twelve-conductor metal overlay but failed native DRC: eight M3.a markers,560categories evaluated. Rejected GDSd52b624e4c243a61352b8a630cc598c43a628192162f95346f96ad5d82cb56d9 and full native reports remain in its release. No LVS or electrical acceptance is inferred.

The pinned IHP metaln deck checks minimum Metal3 width0.20um. Source: https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/beol/5_17_metaln.drc

Foreign-metal clipping can leave thin pieces in the proposed enlargement. Apply a100nm inward/outward geometric opening to that proposal, intersect with the proposal to avoid new growth, then add only its difference from the unchanged original conductor. Retain every original polygon and all previous native geometry-union/fault checks. Record the removed proposal area. Neither the PDK deck nor the200nm width gate changes. Full native DRC/LVS must rerun and pass before extraction.
