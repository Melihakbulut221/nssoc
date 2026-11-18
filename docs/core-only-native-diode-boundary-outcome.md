# Native diode failure exactly at branch boundary

Run44378831538/headf2a8884e4ae9e0e2154a801cf1f3bc2f27651e9f retained the same two failing release cases. Archive14462253095 SHA256540e361f817363a298b7ef791a5cb16a8a16ee2dfe5c473d1df6c220aca64c38 and all native output hashes verified.

For area-release,last native internal diode voltage=-0.1038560695350199V. The inspected ngspice branch criterion is v=-3*n*k*T/q. Using native constants k1.38064852e-23,q1.6021766208e-19,n1.009,T398.15K gives-0.103856069532807V;difference approximately-2.21pV. The failure is therefore numerically coincident with the forward/reverse evaluation boundary,not merely a late low-current condition. Reported transient gd includes integration contributions and is not interpreted as DC conductance.

The independent analytic/complex-step test passes54 illustrative points. The inspected published forward recombination derivative differs by up to36.38percent on that grid. These are illustrative formula checks,not a measured error percentage for the physical device. Native model and runtime were not patched. Both the derivative mismatch and branch-boundary behavior need targeted correction/validation; causality is still not fully proved.

Sources:
https://sources.debian.org/src/ngspice/47%2Bds-1~bpo13%2B1/src/spicelib/devices/dio/dioload.c/
https://sources.debian.org/src/ngspice/47%2Bds-1~bpo13%2B1/src/spicelib/devices/dio/dio.c/
https://sources.debian.org/src/ngspice/47%2Bds-1~bpo13%2B1/src/include/ngspice/const.h/

Next build an independently pinned ngspice47 baseline and a separately identified derivative correction candidate in the cloud; require baseline reproduction,finite-difference/complex-step Jacobian checks,boundary current/charge continuity,full native diode suite and original pad reruns. Do not silently replace the accepted simulator,alter diode parameters,omit protection,relax tolerances or mark timing closed. A fix remains experimental until those checks pass.

Main core detailed route44337630426 remains independently active. The staged extraction source is b75792d10e647522ecb6c554a35906708d718c57; dispatch only after exact detailed-route artifact admission. All production gates remain open.
