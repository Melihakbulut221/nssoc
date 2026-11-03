# Gate resistance composition after current contact binding

Current accepted physical41710162510 feeds wire41712243960 and
metalRC41713023974. The200 actual intrinsic gate electrodes are deliberately
separate from the200 contact metal points. Complete published polygon
analysis records50 electrodes with contacts on one end and150 with contacts
on both ends; see the full per-device evidence JSON.

The official [NXP/CEA-Leti PSP103.7 manual](https://www.leti-cea.fr/cea-tech/leti/pspsupport/Documents/psp103p7_summary.pdf)
sections2.5.6 and3.4, equation3.283, describes gate resistance using RGO,
RSHG, RINT, RVPOLY, NGCON and geometry corrections. Thus removing only RGO
and RSHG is not in itself proof that all compact-model gate resistance has
been removed. RINT and RVPOLY describe different contributions. The
equation's geometry mode also matters. This is reference guidance; the
actual pinned OSDI version and native readbacks must be verified.

Frozen wrapper evidence from model diagnostic41695546092 hardcodesNGCON=2.
Native AC41696724132 measured QS rgo/rshg0 and RF rgo40/rshg3 with SWNQS5;
that input impedance includes NQS and is not a directly measured resistor.
Do not subtract QS/RF real impedance as a standalone physical gate R.
Do not add external poly sheet resistance without resolving overlap with
the model and physical access/contact coverage.

Required next evidence: actual model version, all gate-resistance parameter
readbacks, geometry-specific contact assignment, explicit access/poly/contact
network and a validated method for coupling its distributed electrode to
the intrinsic RF model. Keep original model/runtime and compare diagnostic
changes explicitly. Full loaded electrical gates and serialPHY qualification
remain required; the metal-only RC pass does not satisfy them.
