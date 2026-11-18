# Minimal branch identified: native antenna diode

Run44376802427/head3323a3d949a7aea69fada615143628a023b86ec8:
- n_pair: both original opposite-oriented HV NMOS devices together,without antenna diode: all six captures complete. Artifact14460009255 SHA256e9695fd9e2bdc587dcf8d33eba638382885b03c7f225ae4a59fce18a03a853e0.
- n_antenna: native dantenna alone under same driven gate ramp:0-turnoff fails21.3262ns; five controls complete. Native diagnostic identifies darea-instance d.xdut.xdgate.d1. Artifact14461746783 SHA25697128a182928b01f808f8cfa9000a3074670c1109725699a3c262009e993cdaf.

Every archive digest and declared output hash checked. Ten synthetic failure-propagation/readback cases passed per matrix job. Removing the diode is exclusively a diagnostic reduction and is not an acceptable product fix: antenna protection remains required.

Pinned inputs/models/diodes.lib defines dantenna as three native SPICE diode instances: D1 darea,area=(l*w)/1p;D2 dperim,area=(l+w)/0.5u;D3 dcorner,area=4. Here l0.64um,w0.48um. darea includes tnom27,is2.315e-19,n1.009,rs2.193e5,cj0=9.371e-16,m0.3036,vj0.696,tt7.009e-7. Do not edit these characterized values to force convergence. The error now implicates a native diode transient, not an OSDI transistor compilation, though the exact simulator/model defect remains unproven.

Next preserve a standalone darea/dantenna reproducer with no transistor dependencies and compare a qualified native simulator revision or supported algorithm against unchanged diode parameters. Record current/voltage through the actual diode,full duration and charge response; do not accept a changed model or omitted protection. If a runtime correction works, rerun full original pad/all cases/PVT and step convergence before any Liberty review.

Main route44337630426 remains active; preserve it, then admit detailed routing and dispatch staged actual-SPEF extraction. ExternalIO/package selection and full-chip production verification remain open. Latest workflow here is diagnostic only.
