# Cloud continuation — checkpoint v225

Updated: 2026-11-01T07:27:36.375500+00:00

Latest user instruction: all work in cloud; leave no local project files. Overrides older local-work objective wording. Alltests/simulation/CAD/numericalanalysis onGitHub. Local source/API-derivedtext RAMonly; never acquire nativearchives/models/SPICE/ODB/GDS/rawwaves locally evenRAM. Workspace/projecttemporaryfiles empty/noCAD; unrelatedfilespreserved.

## Exact continuation

1. Observe SAME mainchip41270471645/source2b8931b9c8988fc5dbf497a7b561db579e39f64c/release430345631. Reverified in_progress in combined clear828/route step; no internal subphase inference, restart or source edits. Scope828owned nets/1351diodes/1691protectedrecords;14400s native route budget/360min job. Preserve full terminal native/derived evidence; verify DRC/antenna/connectivity, restored classes/clocks, final-measured.odb and separate unchanged finalSTA. Packet-interface SoC routing does not establish serial integration.

2. Mixed20 wave41284095439/source93fcfe9d9287e1ff9090e96e69000588f6c7eb66 is TERMINAL SUCCESS as diagnosis, not circuit acceptance; full35proofe62b19e3d08245b9993160e0bdc2db1468a1cef4.7frozen13event8transfer controls, complete500composition-digest preflight beforearchive, all109members verified, full124HBT/6stage1530delays/phaseVI reproduced. Do not rerun or call this active.

3. Mixed20 C/D same-time and clock-emitter diagnosis41284522943/source7e4277e5d0d6ab629541cf4f00905762fcb6459f is TERMINAL SUCCESS, full14proofdfa424f2d2bf58bf35adcef6bec6c8f9fb1d6604. At3.1ns slave input differencesC-139.170264mV/D-156.446528mV (inverting pair), outputsC-12.305347mV/D-18.856008mV expectedpositive. Four events/all124same-time identities/voltages/currents retain exactfailure evidence. No new native simulation or MOS same-time current evidence.

4. Next concrete candidate question: isolated C/D slave drive, not sharedreferencebias. Actualslave MOS idsD7..10 atcluster30 andC36..39 atcluster127, W36um/L.3um,ad/as12.24p,pd/ps72.68u,m1,ng1,rfmode0. MasterMOSD3..6(cluster38)/C32..35(cluster124), referencesD11/C40(W8), follower/bufferMOSD1/2/C30/31(W53.335) sharegate25/123 and must remainunchanged. MasterclockQ61/Q62minVCE.407017/.408186 andQ115/Q116.410240/.411376 close to.4floor. Evaluate scoped36->54um slave-width hypothesis on fast-outputAC24sourcee2e753c37fcff8b8fef85695208b8157a7399b57; not yet authored/qualified/dispatched. Derive consistent junctionarea/perimeter tokens from originalgeometry, qualify exact20? NO: this baseline retains24resistorchanges plus separatelydeclared8MOSgeometrychanges; countactualtokens explicitly. Preserve full500 model bytes/metadata exceptdeclared changes, sourcecontrols then independentemptyexactsource release before one native run. No changeexternalbias/stimulus/measurementgates. All sixstagefailuresincludingAremainrequired.

5. Do not treat the output-load experiment as accepted: native41282867236/full64proof740a55daac8798d2f3af976919609d5f7a2353c8 and actual18-control comparison41284059156/full15afd1a4f68e882c3124867e6eca2f34600b951875 prove rejection. Devices andVIpass, onlyBsampler passes, A/C/D/X/Y andphasefail. New current-drive nonlineartransients/sharedgatecap maydisturbmasterheadroom; originalnativegatesdecide.

6. Mixed20 diagnosticcrossing A->AD40/127,C->CD22/128,D->S0/S114/128 each; noambiguity. A->C0/127inside125ps with expectedsequenceindexlag1 and128targetcrossings; not byitselflostbits. B->D128/128median71.229229ps/expectedlag0. Keepallpreceding/followingevents and do notaddmediansfromdifferent matchedsubsets. Native sampledwrong-sign evidence remainsindependent.

7. Qualified mixed20 map41283407710/source1e5bd82f6587c5ac2f764a286802aa858922aaa8/full17proof63402c276101edeb97c23a8f855e1c2d289d6d39 passed16refusals/full500devices4928instances. Selected set20 excludes restored C/D175176212214. A/B191194202205 rppd$2$10 require fourprivatecells to preserve195196207208. Other selected definitions have no unselected physicalusers/conflicts. Ownership only: no native geometry/freshRC acceptance.

8. Keep original UI125ps, sampler100mV/37.5ps,XOR100mV/75ps, strictHBTIc/emitter<3mA,minVCE.4,maxabsVCE1.6,maxabsVBE1,PLL62.5ps. FinalSTA20/4/8/8ns+5%,3PVT,zero setup/hold/transition/cap violations. Every accepted intrinsic edit still requires independent schematic, native geometry retaining via2/M3 repairs,DRC/LVS,freshRC/all500rebinding,corners/closedloop/fullserialintegration.

9. Serialintegration remains open: soc_top external packet/link/training ports, shared front explicit recovered-clock/raw-bit testbench inputs. Actual CDR/PLL/SERDES, normative training/fullLTSSM/lane mapping/descrambler handoff,TX andsoc_top ownership remain; authorized spec access request already pending. See docs/pcie-serial-integration-boundary.md. Do not infer serialintegration frompacketroute.

10. Everything executes on GitHub; workspace/projecttemporary files empty/no localCAD. Source/API-derivedtext coordinationRAMonly, no nativearchives/models/SPICE/ODB/GDS/rawwaves locally evenRAM. Preserve unrelated files. Eight-hour monitor remainsread-only automatic_native_dispatch:false. Goal active/fullPHY/finaltiming/productionapproval OPEN.

## Newly preserved full evidence

- docs/evidence/cdr-sampler-candidate-wave-41284095439: immutablee62b19e3d08245b9993160e0bdc2db1468a1cef4;35files/9193966bytes;receiptSHA25659f2f95f3e43aa26dccb3fd6b438e12af54315109cb3383373e23c241bc39468.
- docs/evidence/cd-latch-diagnosis-41284522943: immutabledfa424f2d2bf58bf35adcef6bec6c8f9fb1d6604;14files/7296162bytes;receiptSHA25647b1c0f63a6cc4f520102a074d623e09e1dec819493f47e03fc2ed836d507f29.

See docs/cdr-mixed20-wave-diagnosis.md, docs/cdr-mixed20-cd-latch-diagnosis.md and docs/cdr-cd-output-load-restore.md. Priorrootv224d16d530856f915106cc4e2af62e0bb59d3b56dbe retains106files of fullnative/comparison/map proofs. All earlier failed experiments and fullnative archives remain onGitHub.

Inventory614runs. Eight-hour monitor read-only automatic_native_dispatch:false. GoalturnPROGRESS: completewave/current/topologyevidence changesnextcircuitexperiment. FullserialPHY,serial-integratedroutedmainchip,finalsetup/hold/productionapproval OPEN. Do not markcomplete.
