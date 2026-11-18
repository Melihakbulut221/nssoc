# Native diode internal-state and derivative diagnosis

Sources inspected via Debian's published ngspice47 source:
https://sources.debian.org/src/ngspice/47%2Bds-1~bpo13%2B1/src/spicelib/devices/dio/dioload.c/
https://sources.debian.org/src/ngspice/47%2Bds-1~bpo13%2B1/src/spicelib/devices/dio/dio.c/
Upstream SourceForge browser access displayed a security verification page; no attempt to bypass it. Debian provides the relevant packaged source independently.

The inspected forward recombination term is Iraw times G,where G=((1-v/P)^2+.005)^(M/2). Its derivative requires Gprime=-M*(1-v/P)*((1-v/P)^2+.005)^(M/2-1)/P, and product rule Irawprime*G+Iraw*Gprime. The source sequence appears to omit1/P in Gprime and uses already-scaled Iraw*G in the second product. This is a mathematical discrepancy hypothesis,not yet the demonstrated cause of the failing transient.

A cloud complex-step check independently differentiates the current expression across54 illustrative points and compares both formulas. It does not alter the simulator or PDK. Native runs add only recorded instance quantities from the published diode table:vd,id,gd,cd(capacitance),charge,capcur. Increase printed digits to15 without changing numerical tolerances. Record partial last states before rejecting the same transient abort. Internal voltage near a branch boundary may distinguish derivative error,branch discontinuity or other cause.

No candidate simulator patch or production waiver is applied. The full pad remains failing; exact original model parameters and circuit stimulus remain unchanged in the native diode reproducer. Main core route44337630426 remains independently active.
