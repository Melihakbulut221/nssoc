# Next: actual gate network, intrinsic models and full metal composition

Status: proposed implementation below is NOT executed or qualified. Current native evidence is intrinsic partition41717942914 and actual poly/contact network41721107217. Full PHY, full PEX, loaded electrical and final timing remain unaccepted.

## Exact inputs and completed prerequisites

The actual GDS is SHA256c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c. Current wire41712243960 binds650 devices/2046 terminals/200 actual gate contacts. Current metalRC41713023974 contains28619R/18469C, all1428 distinct physical points and all13 raw corruption controls.

Partition41717942914/source30392de6e292c690fe73f469c32c236a5ce51b1c/release433212710 preserves W/L/AS/AD/PS/PD and checks multiplicity1/N for N1/2/4/8/16 in160 native executions. All13696 terminal DC/AC comparisons pass. Separate RF model copy only zeros RGO/RSHG; RINT1.3025e-11, RVPOLY0 and NQS5 remain. The altered parameter file hash is dc3d592a1b2ee61074e4d3c473021b788e0d88a4a229c3ee2264e752fd61be9a. Do not alter width to create different physical MOS devices.

Mesh41721107217/source6fc562599fdc527bf95c0ef92332e87a4efd26e6/release433231218 has native/mesh-75/mesh.json and native/mesh-75/gate-poly-resistors.cir inside its complete native archive. It contains131310 cells,236268 sheet branches,1800 contact patches representing200 actual cuts, and exact rational per-device gate area weights. Do not download native archives locally. Selected derived reports are safe to inspect via artifact13272821367. The75nm uniform-injection gate averages differ by at most0.4297672% from150nm; this is not a general convergence certificate.

## Couple field nodes without ideal gate shorts or excessive nonlinear replicas

A direct MOS copy per75nm cell would create535..600 replicas per physical gate and make loaded simulation unnecessarily expensive. Instead evaluate N1/2/4/8/16 equal-area strips along actual gate width. Retain every physical R-network node. For each strip compute exact nonnegative overlap-area weights a_j over its mesh cells, with sum(a_j)=1, and use one unchanged-dimension intrinsic device with multiplicity1/N.

A candidate power-consistent port projection is:
- v_gate = sum(a_j * v_mesh_j).
- i_mesh_j = a_j * i_gate.
- Therefore sum(v_mesh_j * i_mesh_j) = v_gate * i_gate.

Implement a sensed intrinsic gate current, a weighted voltage source for the intrinsic gate voltage, and reciprocal current-controlled return sources at the physical cells. Keep all real contact nodes distinct. This is a numerical field/device coupling, not proof that a gate is equipotential. Verify current signs, KCL, instantaneous/AC power balance and equal-potential reproduction natively before use; then require strip-count and mesh refinement of the full loaded outputs. Cell/bin overlaps can use rational boundaries even when actual width is not divisible by N.

## Optional exact reduction of the linear resistor network

The linear network can be eliminated per physical poly group after the projection basis is fixed. Choose one actual metal contact as a reference coordinate, not a physical ground. Let L be the grounded conductance matrix and T map balanced physical/contact and projected-gate port currents to cell injections. The resistance-port matrix is Z = transpose(T) * inverse(L) * T. Factor sparse L rather than forming its inverse. Verify reciprocity, positive definiteness, port rank, native multiport responses and all actual contact bindings; never clip negative eigenvalues to force acceptance.

A noiseless controlled-source replacement would lose resistor thermal noise and is not sufficient for PHY jitter qualification. One candidate noise-preserving realization uses Y=inverse(Z), Cholesky Y=C*transpose(C), positive reference resistors and reciprocal ideal transformer pairs. With reference R0, use A=sqrt(R0)*transpose(C), branch voltage A*v and return current transpose(A)*i_R. This conserves power and gives ideal thermal current covariance4*k*T*Y. This proposal must be checked against the original native network for DC/AC and noise, including temperature/corner handling. No reduction or noise equivalence has been implemented yet.

## Integration and remaining acceptance

Current metal RC native paths are native/wire-stage/wire/rc03/wires.spice, pump_wires.res.ext and anchors08.json inside release433183824. Bind each GC label through the authenticated unique-anchor/native-port mapping; preserve native ground/mutual capacitances and all original13 corruption controls. Do not join contacts by schematic alias or collapse gate contacts to one point.

Use the actual650 LVS device IDs/source-order mapping. Do not expand the already650-device reference again. Preserve every original complete loaded stimulus and acceptance gate. Full gate extrinsic capacitance, MIM overlap,643 intrinsic body/well references and substrate scope remain open; diagnostic R-network success does not close them. Nominal7ohm/square and15ohm/contact still need narrow-gate/temperature/corner qualification.

Finally require full serial Gen3 x4 behavior, actual mainchip PCIe/Ethernet routed layout and final all-corner setup/hold. Continue polling the SAME mainchip route41699812301; do not restart merely because observation times out.
