# Cloud continuation — checkpoint v230

Updated: 2026-11-01T09:01:34.122118+00:00
Everything executes on GitHub. The latest explicit cloud-only instruction overrides the old local-work wording in the goal. Local workspace stays empty; source/API-derived text coordination is RAM only. No local native archive/model/SPICE/ODB/GDS/raw waves.

1. PD650 simulation41288195752 is TERMINAL ELECTRICAL REJECTION. Engine0,1037.382s,no diagnostics,sources unchanged; all device gates and VI pass, all A/B/C/D/X/Y data stages and phase fail. Full115proof6fdf10cd1683b920950104e7edb6206865eab78e; native release430445706. See docs/cdr-mos-parallel-loaded-simulation.md. Do not restart or call it live. Domain-corrected units remain required; do not use original out-of-range wideMOS to claim improvement.

2. Original mainchip41270471645 is TERMINAL NATIVE ROUTE TIMEOUT. Actual14400.811145697s/return-15/elapsed_limit. Full23proofde4e92bc723d6885c3c800aa5c9676f7495f9a4a. Actual cloud archive readout41290408993/full19proofe19b8a246accee5125c14291b6effd46b94249ad proves last complete iteration26=129violations, interrupted27at40%. No optimized ODB checkpoint was written because64-iteration call was killed before post-call saves and snapshots=0. Known original/cleared seed ODBs remain;1691 protected clock/fixed records restored exactly. See docs/mainchip-828-routing-timeout.md.

3. Implement an explicitly bounded router stage with actual DB save/restore before another long route dispatch. Keep828owners/1351diodes/1691protectedrecords and original final DRC/antenna/connectivity/STA criteria. Do not rerun64 with same failure behavior. Read full router stdout/Tcl in readout proof; full native archives stay on GitHub.

4. Four native MOS unit layout generator/checker is implemented. Widths8/9/8.890/8.885um,L.3um,ng1, real finite tap and independent2device reference. Sourcee3839b66d23c4cd678e4cf917c3b458495f4ac96, controls41290550100/full16proofdb034bcabe0c028b6d7c34151efb44f3a5da2c56. Native41290670037/release430461761 is TERMINAL SUCCESS FOR FOUR UNITS ONLY: all20 stages passed, four DRC560zero, eight deep/flat2deviceLVS passes with no extraction diagnostics, all native W/L/AS/AD/PS/PD exact, all8 negative controls rejected. Source/runtime unchanged. Full119proof6e9362d5c95e1c2b2fca62d9c71aec8ac4e099e4. Do not rerun qualification; use these actual units for the200-unit layout integration.

5. Preserve unit failures:41289980511/44d1ded... failed before geometry due Python3.10; bothhosts nowexplicitPython3.12. Full7proof365a16cda10b4ce909c81d8b88aa995272dda043.41290340331/f196319... generated4layouts and8um passed560DRCzero/deepLVS2devicesMatch; parameter inspector failed callable-idAPI. Full36proof9c6133755ff5424125b2014566ba76ff0ad39694/native430459347. New inspector uses normalized parameter names/accessors. Do not claimall4qualified from8umonly.

6. Unit qualification then actual200-unit/50-origin placement, original450nonMOS preservation, mixed20private-resistor changes, fullindependentDRC/LVS and freshRC/rebinding. Isolated unit pass is not fullPD650 layout or serialPHY pass. Native PD650 electrical rejection still needs valid-domain waveform-led drive/load repair.

7. Original gates unchanged: UI125ps,sampler100mV/37.5ps,XOR100mV/75ps;HBTminVCE.4/maxabsVCE1.6/maxabsVBE1/strictIc-emitter<3mA;MOS<=1.32V/activeVDS>=0/nonnegativeunitcurrents;16stage instantaneous-sum>=.5mA;7MIM<=1.6V;phase30mV;PLL62.5ps. FinalSTA20/4/8/8ns+5%,3PVT,zero setup/hold/transition/cap.

8. Actual CDR/PLL/SERDES, fulltraining/LTSSM/lanemapping/descrambler/TX andserialsoc_topownership remain open. Packet-interface route does not prove serialintegration. Authorized spec access request already pending; do not repeat.

9. Cleanup follow-upd84da6f... archived6historicalPCIehelper+6Icarusscratchfiles before deletion, removed disposableYosysRAMcache and emptyAppImagemountdir. Sharedapps/userfilespreserved. Continue sourcecoordinationRAMonly, alltests/CAD/analysisGitHubonly.

Inventory 631 runs. Eight-hour monitor remains read-only automatic_native_dispatch:false. This turn PROGRESS: actual terminal failures preserved and diagnosed, physical-unit implementation/fixes tested, all20 native physical-unit stages passed. FullPHY, serial-integratedroute, finalsetup/hold, productionapproval OPEN.
