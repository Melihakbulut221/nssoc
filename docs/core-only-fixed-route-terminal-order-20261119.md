# Native FIXED route admission: terminal-order correction

Run 44437146454 at 0cc6fec82656d4f944804128ec19f03ce09035b5 failed before DRT. Artifact 14489660928 SHA256 11216a6cf97655348273008fe58c084e5e2396411550f151c8bb9e5bb7c77251 and all 21 manifest outputs verified.

Native decoder admission passed for all 102965 fixed nets, with metadata-only negative and encoded-FIXED positive controls. The FLOORPLAN importer reverses terminal list order; apb_timeout was the first exact-text mismatch. This is not permission to waive route changes.

The comparison now sorts only the initial terminal tuples, retaining duplicate multiplicity; every suffix token including geometry, vias, status and properties remains exact after the explicitly authorized FIXED/ROUTED substitution. Controls reject pin replacement, duplicate terminals and coordinate changes. Final route identity, original strict post-restoration DEF preservation and visible geometry checks remain enabled. No setup/hold closure is claimed. The clock v1 run 44435678929 was cancelled because its incremental importer was proven to skip NETS; it must not be reused as a valid experiment.
