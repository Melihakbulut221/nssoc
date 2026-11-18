# Core-only routed annotation diagnosis

Prepared; not yet executed against current routed ODB/SPEF. `scripts/audit_core_only_route_annotation.py` adapts the existing native diagnosis without the old design's hard-coded cell/net/SPEF counts. Each input has its own SHA-256; the extraction producer provides the authenticated route ODB, newly extracted nominal SPEF, and each corner's fresh standalone STA log.

The audit demands exactly one complete native unannotated-driver section, rejects duplicates/count mismatch/partial annotation, and resolves SPEF name-map IDs to actual OpenDB nets with exact writer-name checks. Every reported driver must exist with a valid direction. Categories distinguish disconnected drivers, nets without sinks, loaded nets absent from SPEF, and loaded nets present in SPEF but unannotated. All terminal lists are retained. Non-finite/negative D_NET capacitance is rejected.

No category is automatically waived. Zero loaded unannotated drivers would still not establish exhaustive timing constraints, correct RC magnitude, all-pin annotation, transistor connectivity, or signoff. Name-resolution assumptions intentionally fail on an unexpected writer format; they must be reviewed against actual output rather than relaxed by fuzzy matching. Diagnostic completion remains accepted=false and annotation_qualified=false.

The extraction runner now invokes the diagnosis after preserving all three native STA results. If the diagnosis fails, native timing/SPEF outputs remain uploaded and the job fails rather than silently accepting incomplete evidence. No local execution; full native execution awaits detailed routing and extraction. The old legacy audit and its acceptance boundary remain unchanged.
