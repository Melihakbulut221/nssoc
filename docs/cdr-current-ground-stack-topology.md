# Native ground stack after refused continuous-M5 assumption

Generation41383764902/source73af4aa6900a5b16a21a522c6cc48732b754344e passed68source controls but correctly refused to generate the proposed ground strap: there is no continuous owned Metal5 strip at x994600nm spanning all16internal canonical ground anchors. No candidate GDS was produced. Preserve the failed proposal; do not remove its continuous-core predicate to force a pass.

This new read-only operation verifies all13actual conductor GDS/L2N layer unions and the complete avss component14. It reports owned polygon bounds/areas and actual canonical-anchor neighborhoods across M1/Via1/M2/Via2/M3/Via3/M4/Via4/M5/TopVia1/TopMetal1/TopVia2/TopMetal2. It makes no assumption that the inter-stage ground connection uses Metal5. The native physical input remains current four-path GDS1c7d5617 and its current wire L2N.

Use the resulting topology to design an actual same-net reinforcement with original spacing/enclosure guards; then full native DRC/LVS, canonical binding, fresh RC and loaded-wave predicates remain mandatory. No geometry mutation or electrical acceptance is claimed here.
