# CDR measured supply resistor geometry

The previous native supply graph review found substantial local AVDD/AVSS paths after the parent AVDD bypass. This follow-up binds the exact measured resistor names, endpoints and values to the same native extraction and layout. It must not replace the full-wave data failures with a geometrical pass.

The job restores the immutable MIM-aware capture39275348623 and composition39276003536. It compares every native resistance edge/value to the exported wire network, checks the original946port coordinate quantizations, and uses the original wire L2N database to probe representative node coordinates on actual metal layers.

Magic's rnode last field is a placeholder0 in [ResPrint.c](https://github.com/RTimothyEdwards/magic/blob/master/resis/ResPrint.c). It cannot be interpreted as a layer. The [native extraction format](https://opencircuitdesign.com/~tim/programs/magic/manpages/ext_manpage.html) describes the node point as a geometrical reference. Thus a resistor endpoint pair is not a reconstructed conductor polygon, a unique layer, effective resistance or measured branch current. The output records every co-located layer/owner witness and any unresolved point. Original retained nodes obtain their coordinates from their actual native node records.

Priority resistors are R15966,R13797,R13791,R14027,R12487,R14125, plus the largest measured supply-path edges and shared wire-graph bridges. The result guides a subsequent physical repair; DRC/LVS, freshRC and unchanged loaded data/phase/device gates remain mandatory.

All restoration, geometry reading and validation run on GitHub Actions; no local CAD or archive extraction.
