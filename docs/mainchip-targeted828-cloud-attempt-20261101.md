# Targeted 828-net routing experiment

[Workflow 41266854050](https://github.com/Melihakbulut221/nssoc/actions/runs/41266854050) was dispatched once at source `8b7404c7340ef5ebc4a70e36dfa30a96d07013d9`. Its first observed active job was source-controls (124731344945). A workflow launch does not establish that OpenROAD has started or completed detailed routing.

The independent output reservation is release 430325810, tag `cloud-results-41266854050-1-mainchip-bulk-postdrt-antenna`. Root verified an empty release and exact lightweight source tag at 2026-11-01 02:51:33.571225 UTC. The complete six-file reservation proof is `9fc3f246f602f2bcdc62e5d66b88daa49eedba67`.

Before this run, exact-source activation controls in 41266573990 passed: 15 scope, 10 host, 15 stale-wire/clock, 162 bulk integration and 165 saved-diode controls. Complete 83-file proof: `a0575b9b64be82ec4f0e3a43fe836584275504bc`. Disabled integration source 49bc2439 also passed in 41266077522, with full 83-file proof `656b09e82346968445a61684eb96ca77215eaf85`.

The initial source run 41265812656 failed one test because it counted source occurrences in Python's interned constant table. The corrected fixture counts the three AST occurrences and retains compiled-constant equality. Production code did not change. Its full 60-file failure proof `c661f253b998427b1f72ef0e3379e74eaf8f5cb0` remains available; skipped later suites are not claimed as passes.

The separate routing scope includes 608 original diode-bearing nets and 220 authenticated counterparts. All 1,351 diode attachments and 1,691 protected nets remain intact. Exact fixed-ODB and full-snapshot hashes must match before mutation. The original physical connectivity algorithm checks all 828 nets in both modes. Complete source, supervision, clock, DRC, antenna, restoration and failure-publication gates remain enabled.

Next: follow this same workflow and preserve its full terminal result. Do not change the active native branch or launch a duplicate. No routed-layout, final setup/hold or full-PHY acceptance is claimed. Native data and execution remain exclusively on GitHub.
