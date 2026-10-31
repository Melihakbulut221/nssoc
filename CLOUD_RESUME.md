# Cloud continuation — checkpoint v188

Updated: 2026-10-31T19:00:50.054740+00:00

Latest user policy is cloud-only. All tests, simulations, CAD and native/numerical processing run on GitHub. Local source/API derived text coordination is RAM only. Never acquire native archives, models, ODB/GDS, raw waves or native-frame gzip locally, even in RAM. Workspace and project temporary prefixes are empty; no local CAD process. Unrelated files and original user review attachments are preserved.

## Concrete current findings

Original mainchip routing [41211382427](https://github.com/Melihakbulut221/nssoc/actions/runs/41211382427) failed the10GiB process-group RSS guard: observed10747904KiB, hostavailable4418208KiB. Its container hardlimit is12GiB, swap0,2CPUs; hostavailability is not cgroupheadroom. SIGTERM after10000.845s. Iteration14 ended527violations, including414Metal2shorts;iteration15 stopped40percent with524. All1691clock/fixednets remainexact aftercleanup. No route-partial or routed-fixed ODB was saved.

Full97file38,496,343B readonly terminalproof imported from6e0c8999c122fea4306e7c0630f47f4cd351d7ae. Saved stale-wire-cleared.odb is212855093B SHA15dff6b392f043891aff5508709ded3de825d6abc55cc7f7bf24bc7532134fbc; it is prerouteinput, notiteration15progress. A successor reroutesfromstart without repeating provenpreparation wherevalid.

mainchip_next_timing_audit owns narrowly selected iteration5/10DRC reports:239492B total, sourceb2bfc90a090b6b051a087e3c121bd3f8ef9e6d01 on codex/mainchip-drt-report-readback, sourcecontrols41231946798. Root reviewed exacttwo-path whitelist, full735memberverification,9prior+3newfixtures. Oneactualreadonlydispatch is conditional oncontrols/fullproof andindependentempty exactsource publicrelease; root mustreservewhenrunhandle arrives. No reroute yet; localize dominantM2shorts first.

Exactengine dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 supports periteration ODB snapshots through DRTsnapshot1 (FlexDR.cpp1998–2004). Directwrite is non-atomic and omits algorithmsearchstate. Anyfuturecheckpoint needs cloudread_db andoriginalphysical/clock/topologygates. Bound64ODBstorage/publication andbothhost/cgroupmemory; no acceptance relaxation.

CDR actualgeometry [41230358164](https://github.com/Melihakbulut221/nssoc/actions/runs/41230358164) succeeded. Source31a4e84d3733d97977b6f7a11a31504d2e1dc8d7,release430116249;107file21,138,564B terminalproof+5filereservationproof imported. All2991inputmembers authenticated,17selected. Real500devices/1446terminals/113components/238nets/25ports,26anchorframejoins and8existingfullmetalrails verified. Original electricalrejection remains.

fresh_rc_next_audit prepares8Via2+8Metal3 parallelaccess branches atT003..006/T032..035:190nmVia2,400nmM3,17.6umcenter-to-existingupperrail. ExactfullGDSforeignownership/clearance/endpointenclosures will be checked before fullnativeDRC/deep+flatLVS/freshRC/unchangedwavegates. ExistingM1/M2straps remainunchanged. No geometrymutation or expectedR/VCEimprovement has been accepted.

## Single remaining original matrix case

VI-only source38d9bf389a5b95731a87f4b78c071589aea09417 passed root/peerproductionreview, but controls41231403918 failed an old globalprintfaultfixture beforeitsintended uploadfailure. Full30filefailureproof isimported. Test-onlycorrectedsource980fac27251290c94d5499f80daf21fd97d8cccc runscontrols41231827950; productionbodies unchanged.

The newVIpublisher writes storagejournal before inventory; originalfrozenpublisher is untouched. Activation additionallyneeds durablefullprerequisiteJSON/log emission, reviewedexactsource/owncontrols/fullproof. Onlyoneactualvi_bias_off transient isauthorized conditionally; nominal_early ispreparationonly. RealnewSHA/run, VI-firstthenpreparation independentemptyreleases. Never spoof GITHUB_SHA or rerun ninecompletedcases. loaded_admission_review owns thispath.

## Retained qualification and open acceptance

Rootv187 integrated nineexacttrainingfiles after actual110positiveRTL/6compiledmutants/4hierarchies/28cases;41existingdependencies matched. Candidateworkflow notcopied; no inferredrootruntimequalification. FullnormativeTS/EQ/LTSSM/state/seed/lanehandoff, physicalCDC andsoc_topserialhookup remainopen.

PLL existingcompact36pair readback shows clockpathdelay/negativeexcursion failure. Staticcurrentclockdriver/placement inspection is recorded in the immutable receipt; no causalproof or sizingchange. CurrentOP40549236303/release425766455 is a futurecloudreadonly RC/load input, notlocalpayload.

FullserialPHY, serialmainchipintegration, finalroute/setup/hold, RCmin/max andproductionapproval remainfalse. Preservefrozenanaloglimits andSTA20/4/8/8ns+5percent,3PVT,zero setup/hold/slew/cap/fanout. Routedviewexport remainsdisableduntilactualcandidate/engine/LEF/Libertybound.

Monitorv188: 484handles,every8hours,automatic_native_dispatch=false. EarlierHTTP502 issue notclaimedfixed. Allcommits [skip ci],nonforceCAS; scopedGittrees only.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable receipt: docs/evidence/cloud-collector-recipes-20261029/actual-route-rss-and-eight-access-geometry-v188.json
