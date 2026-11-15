# Native HBT emitter-domain correction

Supply-referenced bias candidate43715256618/head1f868237e8bd04110fa9a03b5918db70b8ef01b0 still failed at68.2973ps on xtn; derived14161932806 SHA256cbf7d732319f77a0c8d244180da9010a7106812f615541cd95b371d6f70d3549 independently authenticated. The bias-source hypothesis did not cure startup.

Inspection of IHP sg13g2_hbt_mod.lib identified a concrete invalid model extrapolation: regular npn13G2 declares NX1..10, but this experimental topology used12 and16. Csub=2.30e-14-1.50e-15*Nx becomes -1e-15F for16. This is invalid device use, not evidence of a process-model defect. Source: https://github.com/IHP-GmbH/IHP-Open-PDK/blob/main/ihp-sg13g2/libs.tech/ngspice/models/sg13g2_hbt_mod.lib . The cloud executor verifies the domain and formula in the actual authenticated frozen model before simulation; current upstream contents alone do not authenticate the runtime.

Each Nx12 instance becomes three separate Nx4 devices; each Nx16 becomes four Nx4 devices. Nx1 reference unchanged. Aggregate emitter count preserved but parasitics and independent thermal nodes differ: new electrical measurements required. Thirty native devices each receive OFF readback and full saved V/ic envelope; no capacitance clipping, model editing or thermal disabling. Supply-referenced Rref3200 retained. All source/load/solver/time contracts preserved. Preflight rejects Nx outside1..10 and nonpositive modeled substrate capacitance.

This remains an unqualified topology experiment. It must pass standalone native runs then realistic passive geometry, full loaded650 circuit, PVT, PEX and main-chip integration. Startup convergence alone does not accept device SOA or PHY performance.
