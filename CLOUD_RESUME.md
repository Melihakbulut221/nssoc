# Cloud continuation — checkpoint v216

Updated: 2026-11-01T04:41:04.569529+00:00

Latest direct instruction: do everything in cloud and leave no local project files. This supersedes the older goal text saying local. Workspace and project temporary directories are empty; no local CAD process. All tests, numerical analysis, simulations and layout run on GitHub. Source/API-derived text coordination is RAM only. Never acquire native archives/models/SPICE/GDS/ODB/raw waves/native-frame gzip locally, including RAM. Preserve unrelated user files and attachments.

## Active mainchip job

[41270471645](https://github.com/Melihakbulut221/nssoc/actions/runs/41270471645), source `2b8931b9c8988fc5dbf497a7b561db579e39f64c`, branch `codex/mainchip-net459-diode-prune`, independently reserved release430345631/tagcloud-results-41270471645-1-mainchip-bulk-postdrt-antenna. Source controls passed, clear828/routing step active at last observation. This step name does not establish detailed router subphase. Do not duplicate or mutate native source while active. Scope828=608diodeowners+220counterparts,1351diodeattachments,1691protected records. Actual zeroDRC/antenna and finalSTA required separately.

Prior41266854050 failed on Python tuple versus persisted JSON list in unchanged snapshot masters. Corrected comparison loads complete persisted before/after snapshots, preserving strict invariants. Full prior failure735 emitted records retained; readback41269689818 passed all828 and reproduced representation mismatch. Source controls41270165333 passed.

## Actual sampler-load result: rejected

Native41272254964/source8a07e8f773d931f9cb7f4ac72e5520b68bb133be/release430356103/tagcloud-results-41272254964-1-cdr-sampler-load completed failure. Engine returned0 after863.308s; electrical gate rejected. Full63file proof `6cd6853e3f79613d066076871280f56fea7ee10d`, prefix `docs/evidence/cdr-sampler-load-terminal-41272254964`, retained and imported.

Coupled changes: XD0175/176/191/194/202/205/212/214 collector rppd L2.6->1.5um/W32; XD0184/185/222/223 shunts L5->7.4um/W4. Only12intrinsic lengths; baseline full500device wireRC retained, no regeneratedlayout orfreshPEX. Original1151vectors and workload/gates unchanged;13circuit/5archive source controls passed41272126724.

Actual comparison41273897568/source7c0c9766544dfe673421c42a48b18b600c565323 passed all10controls and full124HBT/1530bit comparison. B alone passes100mV37.5ps; A/C/D/X/Y fail. Candidate HBT failures XD0059/60/111/112 maxVCE andXD0061 minVCE. Phase10.026mV, VI31.984uA fail; VIvoltage9.031mV passes5mV. See docs/cdr-sampler-load-results.md. Never treat successful comparison as passing native PHY.

## Physical mapping prepared, no geometry changed

Read-only failed41273236353/sourceae6e4024bdfec0a5dbeb5e3a8f72ec4b1f2a86b7 retained. It failed nativeHBT spellingnpn13G2 versusnpn13g2.
Fixed41273410851/source8abbaf038172fa9a862733d35f2327adac1cac6a passed9controls/full500devices4928instances/12exacttargets. Only explicitmodelalias accepted; npn13G2l rejected. Full15file successproof58f623f796326427db8ed6f333b1e7128c66e66d, prefixdocs/evidence/cdr-sampler-layout-map-41273410851. Failurefull15proofb15aada9df6c1cf2802cfcc387edf49449f495ca alsoimported.
SharedcollectorPCells have untargetedusers; futurephysicaledit requires privatecellselectedinstances. Do not globally edit sharedcells.

## Retained earlier evidence

FreshRC41251732540 source9bf12d1e496f7d9192582175ab2fa714e3e8d41b release430243359; full454proof682ae5a848d5b578ddc27b47bfc3458578c7ce87. Canonicalview41243752186/source394b6e2c5e6fffbbc1a8d92fbdf41bd5d3a93356/release430197123; full186proofe7b9d3a152295b7f870ea2783c90f5c6116547a1. GDS42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876; flatLVS3e133656d97d0c191390365919187102d9e5f1c75361bf53120e48eea9001295. Allnativefilescloudonly.

Originalloaded41260582673/sourcecde6353e164d32feee5a3e56cc54b32a3001f736 rejected; full631proof53e39a2c43bfef518793da536a6bc423398d7262. Four-shuntonly41268684044/source6733a6916dec86ac84f7879285c3a7c8b495ab6c rejected; full61proof62535582b4a1ad13b005a68dfb2af7b62c66d4a4; comparison41269888640/full15proofaac575ff357328279cb7fad4d93a35416aa52261.

Clockdiagnosis41271280278/source45286428f2d9a5dfcf6781ef04f1bb61cd20def8 passed original fullwave reproduction; full31proofc3517dd428948ca15a949a422c35bb79535bc4cf. Localclock1.95–4.06ps is relative to alreadyloaded externalports, first externaledge~11psafter nominal. Do not redownload1GBnativewave for aggregating existingderived records. Topologyfull16proof3e45b11b44cfbc08f51334b1bb2d372384c3820b.

## Next actions

1. Observe SAME mainchip41270471645/source2b8931/release430345631. No duplicate native dispatch/source edits until terminal; active step alone is not proof of detailed_route phase.
2. At mainchip terminal preserve complete source/log/native release/derived evidence and independently check828owned signal connections,1351diodes,1691protected records, zeroDRC/antenna, finalSTA separately.
3. Use full actual sampler comparison41273897568 before next circuit repair. Candidate41272254964 rejected: B passes but A/C/D/X/Y and XD0059/60/61/111/112 fail. No layout acceptance or gate relaxation.
4. Prepare next measured headroom/common-mode and settling repair using existing exact topology and complete metrics. Qualify corruption controls, reserve exact-source empty native release, then dispatch once. Do not choose a load value solely by interpolation or relabel an exploratory baseline-RC screen physical.
5. Use map41273410851 for any future physical edit:12selected instances, complete500device4928instance checks; collector PCells shared with untargeted devices require private cells. No changedlayout exists for rejected sampler candidate.
6. All computation/simulation/CAD/tests in cloud. Never download native archives/models/SPICE/GDS/ODB/waves locally including RAM. Text source/API coordination RAM only. Keep workspace/tmp empty, preserve unrelated files.8h monitor read-onlyautomatic_native_dispatch:false.

Inventory 579 runs; eight-hour monitor remains read-only with automatic_native_dispatch:false. FullserialGen3x4PHY, routedmainchip, finalsetup/hold andproductionapproval remain OPEN. See previous durable v215 for full source qualification and recipe history.
