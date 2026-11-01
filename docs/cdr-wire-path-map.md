# Physical wire resistance map
The three-case waveform diagnostic 41329721970 measured substantial supply and same-net terminal voltage differences. This job reads the original physical RC producer 41251732540 without changing model, devices or layout, authenticates every original archive member, and compares every resistor in its wire projection with its composed model through the original node mapping.

It solves one-ampere passive DC injections between eleven actual physical-anchor pairs. Kirchhoff residual, energy conservation and synthetic series/parallel/triangle plus reverse-direction checks qualify the calculation. The highest unit-injection energy contributions identify sensitive network edges. These are not operational currents, physical resistor footprints, a proven cause of waveform failures or a new PEX signoff. Endpoint native references and same-conductor ownership are preserved for subsequent geometry inspection.

Magic node coordinates refer to points inside named nodes and must be interpreted with the file scale, as documented in the [official EXT format](https://opencircuitdesign.com/magic/manpages/ext_manpage.html). They do not establish the footprint of a resistance segment.

All acquisition and numerical calculation run on GitHub. Original native inputs remain in release430243359. Source, controls, failures and derived reports are retained. Full PHY, layout closure and final timing remain unaccepted.

The first cloud run41331408334 passed14 controls and found all11 effective resistances, but parsed only EXT node records and left most internal coordinates empty. Preserve that limitation. The successor explicitly reads rnode records, whose numeric type field is not a material identifier; this is confirmed by [Magic ResPrintExtNode source](https://github.com/RTimothyEdwards/magic/blob/master/resis/ResPrint.c). Five added controls cover parsing and bad coordinates/scales. Every ranked edge endpoint must now have a native rnode record. Terminal offsets from original physical anchors are reported, not silently normalized. Units are scaled from centimicrons to the original 1nm DBU.

Original numerical graph, 14 resistance controls, source archive pins, all eleven target pairs, Kirchhoff/energy tolerances and acceptance flags are unchanged.
