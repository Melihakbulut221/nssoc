# Physical wire resistance map
The three-case waveform diagnostic 41329721970 measured substantial supply and same-net terminal voltage differences. This job reads the original physical RC producer 41251732540 without changing model, devices or layout, authenticates every original archive member, and compares every resistor in its wire projection with its composed model through the original node mapping.

It solves one-ampere passive DC injections between eleven actual physical-anchor pairs. Kirchhoff residual, energy conservation and synthetic series/parallel/triangle plus reverse-direction checks qualify the calculation. The highest unit-injection energy contributions identify sensitive network edges. These are not operational currents, physical resistor footprints, a proven cause of waveform failures or a new PEX signoff. Endpoint native references and same-conductor ownership are preserved for subsequent geometry inspection.

Magic node coordinates refer to points inside named nodes and must be interpreted with the file scale, as documented in the [official EXT format](https://opencircuitdesign.com/magic/manpages/ext_manpage.html). They do not establish the footprint of a resistance segment.

All acquisition and numerical calculation run on GitHub. Original native inputs remain in release430243359. Source, controls, failures and derived reports are retained. Full PHY, layout closure and final timing remain unaccepted.

The first cloud run41331408334 passed14 controls and found all11 effective resistances, but parsed only EXT node records and left most internal coordinates empty. Preserve that limitation. The successor explicitly reads rnode records, whose numeric type field is not a material identifier; this is confirmed by [Magic ResPrintExtNode source](https://github.com/RTimothyEdwards/magic/blob/master/resis/ResPrint.c). Five added controls cover parsing and bad coordinates/scales. Every ranked edge endpoint must now have a native rnode record. Terminal offsets from original physical anchors are reported, not silently normalized. Units are scaled from centimicrons to the original 1nm DBU.

Original numerical graph, 14 resistance controls, source archive pins, all eleven target pairs, Kirchhoff/energy tolerances and acceptance flags are unchanged.


## Latest result: original extracted wire bottlenecks and native coordinates mapped

Actual cloud run41331408334/source352b68e4d6a0f6fabbb18b850fff264e24fa0121 passed14 controls and mapped eleven physical-anchor pairs on the original RC graph. Its first coordinate reader handled EXT node records but omitted rnode records; most internal coordinate references were empty. Preserve this limitation and do not treat that first pass as complete geometry mapping. Proof0a1833238c5884607e6e2a703db8d0322b005886 at docs/evidence/wire-path-map-terminal-41331408334 contains all17 files (receipt3234ec6216d594cd6d2a5cf7605991c020df158516b141da3588da119a855e62).

Successor run41331683449/sourcef09bea650a2180b14efa651f3d648f9fdc3ba77e passed19 controls, including five additional coordinate parsing/refusal checks, and authenticated all3091 original native capsule members on GitHub. All24360 wire resistor cards match the original composed model through its exact node map. Every ranked edge endpoint now has actual rnode coordinates. Rnode numeric type is deliberately not interpreted as a metal. All original numerical calculations, original physical anchors and original source archive remain unchanged. Proof9676c2b87b2fcfc32a6e5981e78827883827506f at docs/evidence/wire-path-map-terminal-41331683449 contains17 files (receipt1d63cbd22390592f5be549d1c97012e88bb24cd76357f0f6c6fc28d77b01964e).

Measured effective resistance on original passive wire network:
- A series output T227_rppd_2 to shunt top T228_rppd_1:54.24519999999601ohm.
- A series output to buffer base T123_B:67.84909999998533ohm.
- A shunt top to buffer base:72.99409999998234ohm.
- C series output to shunt top:54.24519999999601ohm.
- D series output to shunt top:54.06919999999009ohm.
- AVDD to T124_C:42.62048764263007ohm.
- AVSS to T126_E/T129_E:21.13319100251308/21.18774570249786ohm.
- AVSS to shunt228/235/239:22.131607769626264/22.31409945376873/22.186162469739923ohm.

Important original edge identities:
A path R13592=24.5501ohm T273_mim_btm.n1--T227_rppd_2;
R13591=25.5151ohm T273_mim_btm.n2--T228_rppd_1;
R13590=4.18ohm between those internal nodes;
R13589=43.299ohm T123_B--T273_mim_btm.n1.
AVDD R18797=33.4312ohm P_avdd.n1103--T124_C and R18796=8.46587ohm P_avdd.n1102--P_avdd.n1103.
Ground126 R21114=13.5088ohm P_avss.n1959--T126_E and R21110=6.16703ohm P_avss.n1956--P_avss.n1960.
These are electrical network sensitivities to one-ampere DC test injections, not operating-current estimates, AC transfer, physical resistor footprints, proven sole causation or PEX signoff. Kirchhoff residual and energy conservation passed. Original limits/acceptance remain unchanged.

Native coordinates are supplied with scale1000/1/0.5; coordinate values are in centimicrons after applying lscale. GDS uses0.001um DBU. Actual terminal coordinates match for A series/shunt/base and supply124; ground126 retains native -2nm y offset, not silently normalized. For A, original physical anchors T227_rppd_2=[1024100,2059690],T228_rppd_1=[1084100,2055530],T123_B=[1084525,2305300]DBU, native cluster139/component66. Native rnodes T273_mim_btm.n1=[204120,439962] and n2=[215520,439962] in EXT coordinates. Full eleven-pair report retains all endpoint coordinate records and unit-injection energy contributions.

Next PHY action: on GitHub acquire the exact original GDS and wire L2N from original RC archive41251732540/release430243359 using scripts/cdr-wire-path-map-inputs.json atf09bea650a2180b14efa651f3d648f9fdc3ba77e. The native members include binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds and mim/precise/wire/native05/wires.l2n (plus matching wires.gds). Map actual owned conductor shapes, identify legal direct or wider signal/supply access and generate a reversible physical candidate with foreign-metal/via clearance checks. Frozen scripts/cdr_current_via2_m3_access_candidate.py at9bf12d1e496f7d9192582175ab2fa714e3e8d41b demonstrates authentic LayoutToNetlist layer/owned-net/GDS-union checks; its old eight-drain targets and authority cannot be reused as new geometry. Then full DRC/LVS, fresh RC and loaded-wave validation. Width2/Nx8 electrical device-geometry trials are not regenerated accepted layouts; do not pretend this wire-only diagnosis closes that gap. No arbitrary R scaling or gate weakening.

Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 is still active; use existing handle, no duplicate dispatch. Its terminal results require actual-pin/class restoration/connectivity qualification, DRC/antenna, matching154480-instance netlist, fresh RC and unchanged final STA.

All work remains cloud-only. Local workspace/task temp empty; no local CAD or native payload acquisition. Eight-hour monitor read-only inventory now693; prior HTTP502 live monitor failure remains recorded. Full serial PHY, physical routing closure and final setup/hold remain open.
