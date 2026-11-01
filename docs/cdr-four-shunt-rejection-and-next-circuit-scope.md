# Four-shunt experiment: rejected electrical result

The complete comparison at run41269888640 reuses the original predicates and all1530 bit delays. No changed circuit layout or RC extraction has been accepted.

The four changes XD0184/XD0185/XD0222/XD0223 (rppd L5um to7.4um, W4um) remove the four original minimum-active-VCE failures of XD0061/XD0062/XD0115/XD0116. They introduce maximum-alltime-absolute-VCE failures on XD0059/XD0060/XD0111/XD0112. Their candidate maxima are1.6696198328798038,1.678477097073657,1.6700167822317786 and1.6764582999128037V against unchanged1.6V maximum.

All four sampler and both XOR data gates remain false. The candidate phase output0.014657771643623032V is below0.03V. The VI mean signed current44.340536296606034uA is below50uA. **VI output voltage0.012567925939183744V passes its0.005V minimum**; it is not an upper-bound violation. Bias passes. VI phase still fails because current fails. Checkpointv211 prose incorrectly framed the voltage as above a limit; this corrects that interpretation without changing any measurement or gate.

The authenticated original physical composition shows:
- XD0059/XD0060 collectors are nodes$98/$99, exactly the nodes affected by shuntsXD0185/XD0184; their emitters share$66.
- XD0111/XD0112 collectors$651/$652 correspond to shuntsXD0223/XD0222; their emitters share$620.
- The former pair's bases$65/$67 are driven by emitter followersXD0069/XD0070 from nodes$286/$285. The latter bases$619/$621 are driven by XD0121/XD0124 from$450/$449.
- Upstream nodes$285/$286/$449/$450 have avdd pullupsXD0191/XD0194/XD0202/XD0205 (L2.6um,W32um). These also belong to the preceding sampler latch/output networks. Altering them affects data swing, common mode, settling and previous-stage stress together.
- The minimum-VCE clock steering pairs XD0061/XD0062/XD0115/XD0116 all have base cn. Their collector headroom is coupled to the input amplifier output common mode.

This is a coupled common-mode/headroom and data-settling problem, not a successful four-resistor repair. A further candidate must address both sides and retain every original device, six-stage data, phase and VI predicate. No intermediate shunt length is asserted to solve the problem; no new electrical candidate was dispatched during this checkpoint. Review complete wave-derived extrema and physical topology before a new constrained circuit experiment. Final acceptance still needs regenerated native layout, DRC/LVS, fresh RC, required corners and closed-loop integration.

Evidence: docs/evidence/cdr-four-shunt-comparison-41269888640, docs/evidence/cdr-four-shunt-terminal-41268684044, and docs/evidence/cdr-loaded-topology-terminal-41267705616.
