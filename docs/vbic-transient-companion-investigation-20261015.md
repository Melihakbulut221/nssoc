# Native VBIC transient companion investigation

The original coupled startup mismatch survives charge and nonlinear-accuracy tightening. Source inspection identified a more specific candidate in ngspice47's [VBIC transient loader](https://github.com/imr/ngspice/blob/a80f6e3e95d51534905b1f23410a951802666656/src/spicelib/devices/vbic/vbicload.c). Its exact SHA256 is `ae2fca22ca7178bce26f31b4e433307945cafa9d8661d55007eed8fc096ff866`.

At lines884-887, native integration returns the Qbcx companion conductance `G=geq`, and the code stores the integrated charge current as `cbcx`. At lines1095-1100 it adds G to the BI/CX matrix but directly stamps -cbcx/+cbcx into the right hand side. By comparison, the adjacent overlap-capacitor branches explicitly subtract G times their linearization voltage before stamping the equivalent current.

For a branch with current I(V), Newton linearization at V0 is `I(V0) + G*(V-V0)`. Thus the right-hand-side companion current is `I(V0)-G*V0`; omitting the subtraction adds an artificial G*V0 residual. Since G contains the integration coefficient, this is a plausible source of timestep-dependent bias. Polarity also requires the model type when mapping normalized VBIC voltages/currents to external terminals.

The proposed one-expression diagnostic correction is:

```c
cbcx = model->VBICtype * (*(ckt->CKTstate0 + here->VBICcqbcx) - gbcx * Vbcx);
```

This is a hypothesis until the native experiments demonstrate the effect. It changes no IHP model parameter, device geometry, source or acceptance window. Other possible transient Jacobian issues are outside this isolated patch.

Hosted run38793936101 builds exact upstream commit `a80f6e3e95d51534905b1f23410a951802666656`, records compiler/configuration/source, measures the pristine binary, applies only this expression, and rebuilds with identical flags. Both are compared to the exact packaged binary used by the existing evidence. Synthetic NPN and PNP models use constant nonzero bias at1ps/0.5ps steps. Their DC currents should persist in transient analysis; QCO=0 matched controls remove the implicated charge while preserving other parameters. All native failures, decks, model readbacks and binaries are retained. A successful workflow is not itself a successful counterexample or fix.

Before any adoption, results must demonstrate the matched controls, original failure, corrected behavior and packaged/pristine agreement. Then the exact frozen coupled circuit must be reproduced with the pristine runtime and tested with the patched one, followed by full34ns/all-original-vector timestep comparisons, bit/device checks, independent PVT and physical validation. Synthetic constant-bias success alone establishes neither PCIe PHY completion nor chip timing closure.
