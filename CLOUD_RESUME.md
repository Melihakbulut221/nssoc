# Cloud continuation — checkpoint v220

Updated: 2026-11-01T05:58:20.764203+00:00

**Latest user instruction: cloud only; leave no local project files.** This overrides older goal wording saying local. Workspace/project temp are empty and no local CAD process is active. All tests, simulation, numerical/geometry analysis and layout run on GitHub. Local source/API-derived text coordination uses temporary RAM. Never acquire native archives/models/SPICE/ODB/GDS/raw waves/native-frame gzip locally, includingRAM. Preserve unrelated files.

## Active job

[Mainchip41270471645](https://github.com/Melihakbulut221/nssoc/actions/runs/41270471645), source2b8931b9c8988fc5dbf497a7b561db579e39f64c, branchcodex/mainchip-net459-diode-prune, independent release430345631/tagcloud-results-41270471645-1-mainchip-bulk-postdrt-antenna. Same actual job; no restart or source mutation. Last observed in combined clear828/routing step. Scope828=608diodeowners+220counterparts,1351diodes,1691protectedrecords. The step name does not prove internal detailed-router phase. Native route budget14400s and job360min leave separate restoration/publication work. Timing acceptance is separate.

## New terminal electrical evidence

Both q15 andq20 are now rejected, not active:
* q15 native41277054717/sourcee85179e6900c2be9d931a8b30549c99f47c7617d/release430382305. Engine0,682.744927s,devicespass. OnlyBpasses;A41.40625ps/65.427579mV, C/D/X/Yfail. Phase7.742293mV/VI25.505829uAfail;VI7.084018mVpasses5mV. Full64proof559d1879b2a461d2926279262695a9bd20efed83. Actualcomparison41278156089/source9525946fc408f2ada69b854466ae0b67d7d7cb6f/full15proofd221360bf0cadffddc80a0c7fcd06262fd0337dc.
* q20 native41277056212/sourceedc7c8d04659f73d024c45bbfa4936b977c90c32/release430382311. Engine0,742.773588s,devicespass,all6stagesfail. A43.59375ps/43.079583mV,B39.53125ps/78.027343mV. Phase10.126912mV/VI32.271976uAfail;VI9.024841mVpasses5mV. Full64proofa9b1c76d93d90fb57b8820f26b06ccccd1fcfebc. Actualcomparison41278276162/source869503434669eb2d885061cc8ca81b9c8eeef5ea/full15proof7298b1f50c9a24d5169874544ad3b20f2537f75b.

Both actual comparisons repeat13corruption refusals, complete16intrinsicbinding andalloriginalmetrics. Exact16resistor delta and fullsixstage table in docs/cdr-original-master-followup.md. Originalmaster loads2.6/W32, outputloads1.5 versus2.0/W32,4bufferpullups1/W8,4shunts3.4/W4. Nochangedlayout/freshRC. Increasingoutputloadlength improvedphase butregressedA/B; not a passing design direction.

## New operating-point evidence

* Prior24candidate diagnosis41277766243/source84d7f18fa89ac715ee242d17cd2dfdbeb51dce14/full29proof5fa4b869e7b10c5ceedd5265ec1ffc4561a8e1e9.
* q20 diagnosis41278288991/sourcebb6ab5d1aa4a9e4b796ba8db40069d9d4902da61/full29proofd0d1c4a8441ce8bb85997bd73e45eb87f66bd93e.

Each passed7frozen+13event controls, verifiedwhole109-membernativearchive onGitHub, reproduced124HBT/all6stages1530delays/phaseVI. Fullresult includesall124simultaneousHBTs at eachstage'sworst originalsample andworst-delaybitdeadline (12events). No simulator rerun/nativegeometrymutations. Derived/source/logproofs complete; nativepayload neverlocal. Both sourceworkflowhiddenfiles preserved andpipefail explicit.

See docs/cdr-sampler-operating-points.md for observedvoltages, distinctA/Cdivider networks andnextpathdiagnosis. R227/2293.6/W1,R228/23021.6/W1,MIM273/2743.6square feedAdata buffersQ123/125; R238/240,R239/241,MIM277/278 feedCdata buffersQ128/130. Aoutputs87/88nativeclustersfanout includesholdHBT87/88,data89/91,followerbases121/124. AllsixNx4; buffersNx2. Resizing is not implemented or qualified. PublicPDKNxrange aloneisnotphysical/reliabilitysignoff.

## Physical and retained evidence

Paired16map41277369515/source7bea91b0ec7a6a4fd9f8205a0cb3f5808a069a71/full16prooff89d371d49788e6e5bec240a65c242cafe22e7c8 passed11controls/all500devices4928instances. Outputs175/176/212/214 share rppd$2$11 with untouched177/178/215/216; outputs191/194/202/205 share rppd$2$10 with untouched195/196/207/208. Private targetedcellsrequired. No geometrychanged.
Previous24native41274791029/sourceeca0/release430370301 full64proof8d5acc3dd28028897d09b6adc46bfcdfae8392be, comparison41276473135/full15proof8431599645f7adf3efe96815df67550ceb689dae:devicespass/all6datafail. Previous12native41272254964/source8a07/release430356103 full63proof6cd6853e3f79613d066076871280f56fea7ee10d/comparison3107d34d22c8572989fc958cd35a252a6e543a38.
Originalfull631proof53e39a2c43bfef518793da536a6bc423398d7262; freshRC41251732540/full454proof682ae5a848d5b578ddc27b47bfc3458578c7ce87; canonicalview41243752186/full186proofe7b9d3a152295b7f870ea2783c90f5c6116547a1. Mainchip previousfailed41266854050/full17proof24e4a5c4ddd80cbdb6f6dfdbd6fc6a964b478e30, corrected savedJSON41269689818/full18proof80f894220ee2e206124bc4f64423e1da042d4942, qualifiedhost41270165333/full83proof504129e2e1c00576b2db10fa7ef1de6683f0fe19.
Priorrootv219:508f65673170a151076b2d59a8bb43e85ac34668. All previous evidence retained.

## Next actions

1. Mainchip SAME run41270471645/source2b8931b9c8988fc5dbf497a7b561db579e39f64c/release430345631 remains the actual routing job. Observe its terminal state without duplicate dispatch/source edits. Preserve complete emitted evidence and native output on GitHub; verify828ownednets1351diodes1691protectedrecords, actual DRC/antenna and finalSTA separately. Host route command budget14400s, job360min; active step does not identify detailed-router subphase.
2. q15 andq20 are now terminal electrical rejects with engine0, devicespass and original gates unchanged. Full64proofs559d1879b2a461d2926279262695a9bd20efed83/a9b1c76d93d90fb57b8820f26b06ccccd1fcfebc and actual15comparisonsd221360bf0cadffddc80a0c7fcd06262fd0337dc/7298b1f50c9a24d5169874544ad3b20f2537f75b are retained. Do not redispatch or accept either layout. q15 B onlypasses, q20 allsixfail; largeroutputloads regressA/B.
3. Read full operating-point results41277766243/source84d7f18fa89ac715ee242d17cd2dfdbeb51dce14/full29proof5fa4b869e7b10c5ceedd5265ec1ffc4561a8e1e9 and41278288991/sourcebb6ab5d1aa4a9e4b796ba8db40069d9d4902da61/full29proofd0d1c4a8441ce8bb85997bd73e45eb87f66bd93e. Sevenfrozen+13eventcontrols, alloriginalmetricsreproduced, all124HBTs at12common events. Inspect exact report not onlysummary.
4. Next quantify loaded transfer A/B/C->divider bases->AD/CD/S0/S1->XOR against actual failing deadlines in preserved waves. AQP/AQN R227/2293.6/W1 andR228/23021.6/W1 withMIM273/2743.6square feedQ123/125; CQP/CQN R238/240,R239/241,MIM277/278 feedQ128/130. Aoutputs alsohold87/88,data89/91,followerbases121/124 Nx4. Source/API-derived topology alreadyretained. Correlation is notproofcausalfix; no blindfurtheroutputloadincrease.
5. Only after this diagnosis qualify controlled intrinsic edits with complete500device bindings, alluntargeted modelbytes/gates/external150fF/50fF/10ohm loads frozen, exactsourcecontrols andindependentlyreserved release. Check pinnedmodel/PCell anddeviceoperating envelope before emitter sizing; publicnpn13G2Nx1..10alone isnotqualifiedchangedgeometry. Any passed circuit stillneedsowncomplete physicalmap, genuineauthoredreference, nativeDRC/LVS/freshRC/corners/closedloop/fullPHY.
6. Use paired16target map41277369515 when appropriate;8output resistorinstances require privatecells because8mastersuntargeted. Do notreuseitfornewHBT/cap/differenttargets. Preservecanonicalvia2/M3repairs and rebindall500afterextraction.
7. Allsimulation/tests/numerical/geometryanalysis staysonGitHub. Localworkspace/tmpempty, noCAD. Nativearchives/models/SPICE/ODB/GDS/rawwaves neverlocal evenRAM; source/API-derivedtexttemporaryRAMonly. Keep8hmonitorautomatic_native_dispatch:false. FullPHY/finaltiming/productionapproval remainopen.

Inventory597runs;8hmonitor automatic_native_dispatch:false. **Full serialGen3x4PHY, routedmainchip, finalsetup/hold andproductionapproval remainOPEN.** This checkpoint records completed experiments and changed next engineering action; it does not redefine the full objective.
