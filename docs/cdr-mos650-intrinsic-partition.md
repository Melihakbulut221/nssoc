# Equal-potential intrinsic gate partition before physical gate integration

The actual650 layout contains multi-contact gate strips whose200 intrinsic gates must connect to the200 real contact anchors through physical poly/contact resistance. Shorting each intrinsic gate to an arbitrary metal point is not acceptable. To represent a distributed electrode, this experiment first checks whether numerical portions of the unchanged compact device preserve its behavior when all electrode potentials are equal.

Every replica retains original physical W/L/AS/AD/PS/PD, ng1, rfmode1 and pre_layout0. For N=1,2,4,8,16 each replica has multiplicity1/N, with exact total1. The four actual current geometries and all200 native IDs come from the authenticated current wire41712243960. This is numerical quadrature of one intrinsic device, not a claim that multiple smaller physical MOS devices exist. No small-width substitute is used.

The frozen original RF model is compared with a separate copy in which only the RF NMOS RGO40/RSHG3 terms are zeroed. RINT/RVPOLY, NQS and every other parameter remain unchanged. The latter is a candidate for explicit physical gate resistance; this test does not qualify the resistance values, contact behavior or model overlap outside these two terms.

For each library, geometry and partition count, four independent native AC terminal excitations give a complete4x4 admittance matrix at17 frequencies from1MHz to10GHz. At Vg0.8/Vd0.6, each case measures all terminal currents; a separate DC grid covers Vg0..1.2 in0.1V steps and Vd0.1/0.6/1.1. There are160 native simulator executions. Every native MULT/NF/NGCON/RG/W/L is read back; the source model is never rewritten. Single-copy model readbacks verify RGO/RSHG/RINT/RVPOLY/SWNQS.

Predeclared numerical identity tolerances are relative1e-7 plus absolute1e-12A for DC currents, and relative1e-7 plus absolute1e-14S for complex admittance. These also bound terminal KCL residuals. They test weighted-model numerical equivalence and do not replace or relax the original complete circuit acceptance thresholds. All comparisons and violations are saved before rejection, along with full native outputs and every failure.

A pass is only the equal-potential prerequisite. Actual physical poly/contact network construction, nonuniform gate potentials, mesh refinement, full MIM/coupling/substrate scope, complete loaded transient and serial x4 qualification remain required. Mainchip route41699812301 and final all-corner setup/hold remain independent open requirements.
