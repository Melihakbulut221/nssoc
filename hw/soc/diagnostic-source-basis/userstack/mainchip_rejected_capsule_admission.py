#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Admit one rejected capsule for observation only; never create a continuation."""
import ast, copy, hashlib, json, os, re, shutil, stat, subprocess, tempfile, zipfile
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc/'
METHOD='scripts/mainchip-rejected-capsule-admission-methods.json'
CONTROLLER='scripts/cloud_mainchip_route12_drt_continuation.py'
CONTROLLER_SHA='08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee'
RUN=40095811631
HEAD='4d85722e05fbda8440c6577d7d7baa18a642485b'
PUB_RUN=40115867400
PUB_HEAD='79477d53f7568266da6796c47748de96c4558273'
RELEASE=422874927
TAG='cloud-results-40115867400-1-mainchip-route12-recovery-publication'
ZIP_ID=672870034
REPORT_ID=672872769
INVENTORY_ID=672869901
ASSETS=json.loads("{\"672869901\":{\"name\":\"member-inventory.json\",\"bytes\":14944,\"sha256\":\"d0ac4a8dfebab1d8c2f9336291f5863b171ae8fa28bab70ad8fc461c27fea6d4\"},\"672870034\":{\"name\":\"original-artifact-12564886005.zip\",\"bytes\":1560640815,\"sha256\":\"6231b9523ba15bcabac5e65b166648523a742c146321c7806ff97d01e6272e56\"},\"672871178\":{\"name\":\"original-job.log\",\"bytes\":130528,\"sha256\":\"95782e475057e65b6d3ef165d7d26c36f269fe04981cb984e0279b1c3607ed19\"},\"672871331\":{\"name\":\"original-evidence-000-actual-native-executable.log\",\"bytes\":81,\"sha256\":\"8112817dcef80d96cc72ffee6d72da4f5b6644d82ebc7bfc9fb90bdd3ef44e54\"},\"672871943\":{\"name\":\"original-evidence-038-result.json\",\"bytes\":59041,\"sha256\":\"18c84b299063bdaf327582641f57c76c4a00091b1590116a63f920ec50aca9e6\"},\"672872769\":{\"name\":\"original-evidence-051-result.json\",\"bytes\":59346,\"sha256\":\"6ec1c82be84c28a04cd3e9afd87dd776ff138368d45f6dc6e1cb96579d4c2595\"},\"672872838\":{\"name\":\"original-evidence-053-boots.log\",\"bytes\":18,\"sha256\":\"d6517f61034b9578e0ffe62cf86a12ca3a675a8281fa6ed80f9c4e4fcfd40d48\"},\"672872982\":{\"name\":\"original-evidence-063-native.log\",\"bytes\":90392,\"sha256\":\"bcfc275fba12aaae1879727ebf90a8fdc9d9833dbd9aa23dd131619498d0f41e\"},\"672873044\":{\"name\":\"original-evidence-064-route.tcl\",\"bytes\":1840,\"sha256\":\"11457b60c2c81c6c64ab44272a14394190255548fe31394497990ffa4e8d0085\"},\"672873325\":{\"name\":\"publication-repair.json\",\"bytes\":30965,\"sha256\":\"a27b334f9f0e6205ecb32107b8f5b67ccd0bd3c620645fca5ecd6f9ea4c3023f\"}}")
REPORT_CORE=json.loads("{\"status\":\"FAIL_OR_ERROR\",\"source_head\":\"4d85722e05fbda8440c6577d7d7baa18a642485b\",\"stage\":\"cross\",\"route_complete\":false,\"final_timing_complete\":false,\"full_phy_accepted\":false,\"image_id\":\"sha256:113cc2e5500e0152a2137336ae092c7caeccb5f8b95b17874fd649d097b8daf8\",\"job\":\"continuation\",\"run_id\":40095811631,\"runtime_source\":{\"run\":39494338440,\"summary_sha256\":\"21e8f082931a30e8ae074d34843c828502a80e0719b778e6a8686a04fc976bc2\",\"manifest_sha256\":\"dccdda0edea5954b3284d87636d055cce1157f1a0e4d20b962f30b7476979856\",\"restore\":{\"archive\":{\"parts\":1,\"bytes\":826825972,\"sha256\":\"b748abf9ecccc446606ecc49629de8ffef95e7c46b473a3bc83fa2cb301590e9\",\"all_parts_and_combined_bytes_verified\":true},\"selected_files\":{\"result.json\":{\"sha256\":\"21e8f082931a30e8ae074d34843c828502a80e0719b778e6a8686a04fc976bc2\",\"bytes\":8290},\"native-image.tar\":{\"sha256\":\"c8448ddce6e02b2f23ddd84245a71ae43c2b4b8537c5e1bdaf80fc4ef8882f9d\",\"bytes\":2665922048},\"runtime-inventory.json\":{\"sha256\":\"f0dd493a1f5106da8a86bf0de6821d6ddbeed25050717c5706225c3d4fdfdbfa\",\"bytes\":6246138}},\"full_archive_verified_before_extraction\":true}},\"loaded_process_portability_source\":{\"run\":39497563699,\"summary_sha256\":\"3cc769d226c0550bb1c394d9da99495add690a11a36c2f49fe58394bd511be04\",\"parts_sha256\":\"81e6f35494abb8e5af1c909813a146a1b2729e185bc4ba6b6a8b3e4f754e3ea3\"},\"global_source\":{\"run\":39910632183,\"summary_sha256\":\"0c7f6a86849d32ae853726ab448da0e4c2f71373956220c95c434657247e9d60\",\"manifest_sha256\":\"2d68e459ee27865ffb566aa252a2a11c760e13391704396c0126d9e1748f65bd\",\"restore\":{\"archive\":{\"parts\":1,\"bytes\":189620091,\"sha256\":\"a32a7de0d563e41f113957c59b734925edea0f7b438ce0b3c44aff571653f44a\",\"all_parts_and_combined_bytes_verified\":true},\"selected_files\":{\"fixed-clock.json\":{\"sha256\":\"a72f0e7f03405f5c61961b14b721c822f25df143ce67546cf3e93c7db4b210e5\",\"bytes\":20307},\"run/1-nssoc-repairfreshglobal/fresh_fanout_native.tcl\":{\"sha256\":\"dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e\",\"bytes\":8655},\"run/1-nssoc-repairfreshglobal/fresh-fanout-global.odb\":{\"sha256\":\"2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a\",\"bytes\":145147935},\"run/1-nssoc-repairfreshglobal/fresh-fanout.guide\":{\"sha256\":\"54ae78b49f70b05e007edc151c67c64a7eed4fd9a9ce0aed6d7898bb3286dcde\",\"bytes\":48436883},\"run/1-nssoc-repairfreshglobal/_env.tcl\":{\"sha256\":\"255d39b6b296466fae51428718fd9fdd5019594fdf6d1c2cbdd116ac52e8c8f0\",\"bytes\":19023},\"run/1-nssoc-repairfreshglobal/config.json\":{\"sha256\":\"c6dfea371e243881a4ae20499da8726980c83224ea31e1b4e5fe7bb44cbccaaa\",\"bytes\":23275},\"candidate-state.json\":{\"sha256\":\"647d7347c0676ac2d08112164b6917b5c45185067c2deef808e404f7434518ba\",\"bytes\":668},\"geometry/result.json\":{\"sha256\":\"3f0141703d3531e11a2f7e7c1fc7d66a1fdc133723f473005aeeede216b84083\",\"bytes\":605},\"trial-config.json\":{\"sha256\":\"b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f\",\"bytes\":10001},\"result.json\":{\"sha256\":\"0c7f6a86849d32ae853726ab448da0e4c2f71373956220c95c434657247e9d60\",\"bytes\":2994023}},\"full_archive_verified_before_extraction\":true}},\"global_candidate_instance_count\":153130,\"global_odb_sha256\":\"2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a\",\"global_guides_sha256\":\"54ae78b49f70b05e007edc151c67c64a7eed4fd9a9ce0aed6d7898bb3286dcde\",\"candidate_netlist_sha256\":\"3c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd\",\"source_sdc_sha256\":\"19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597\",\"original_native_settings\":{\"DESIGN_NAME\":\"soc_top\",\"DRT_THREADS\":\"2\",\"DRT_OPT_ITERS\":\"64\",\"DRT_SAVE_SNAPSHOTS\":\"0\",\"DRT_SAVE_DRC_REPORT_ITERS\":\"5\",\"DRT_ANTENNA_REPAIR_ITERS\":\"1\",\"DIODE_CELL\":\"sg13g2_antennanp/A\"},\"retained_timing_contract\":{\"clock_periods_ns\":[20,4,8,8],\"derating_percent\":5,\"new_native_sta_run_required\":true,\"step_configuration_sha256\":\"c6dfea371e243881a4ae20499da8726980c83224ea31e1b4e5fe7bb44cbccaaa\",\"full_flow_configuration_sha256\":\"b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f\"},\"cpuset\":\"0,1\",\"route_script\":{\"sha256\":\"11457b60c2c81c6c64ab44272a14394190255548fe31394497990ffa4e8d0085\",\"original_sha256\":\"dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e\",\"exact_native_drt_setup\":\"set_thread_count $::env(DRT_THREADS)\\n\\nset drc_report_iter_step_arg \\\"\\\"\\nif { $::env(DRT_SAVE_SNAPSHOTS) } {\\n    set_debug_level DRT snapshot 1\\n    set drc_report_iter_step_arg \\\"-drc_report_iter_step 1\\\"\\n    detailed_route_debug -snapshot_dir \\\"$::env(STEP_DIR)\\\"\\n}\\nif { [info exists ::env(DRT_SAVE_DRC_REPORT_ITERS)] } {\\n    set drc_report_iter_step_arg \\\"-drc_report_iter_step $::env(DRT_SAVE_DRC_REPORT_ITERS)\\\"\\n}\\n\\n\",\"exact_native_drt_arguments\":\"set drt_args [list]\\nlappend drt_args -droute_end_iter $::env(DRT_OPT_ITERS)\\nlappend drt_args -or_seed 42\\nlappend drt_args -verbose 1\\nlappend drt_args {*}$drc_report_iter_step_arg\\n\",\"layers\":\"set_routing_layers -signal Metal2-TopMetal2 -clock Metal4-TopMetal2\",\"already_executed_global_route_replaced_by_hash_pinned_saved_global\":true,\"sta_before_global_route_provenance_only_no_new_timing_acceptance\":true},\"controller_sha256\":\"08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee\",\"previous_boot_id\":\"ef7a1b03-be40-4e3e-9a7a-1cca3036bcad\",\"boot_id\":\"f39f76a1-2be6-4dae-a21d-2451279b634f\",\"restored_native_process\":true,\"continuation_source_descriptor\":{\"run\":40085912519,\"attempt\":1,\"group\":\"mainchip-route12-drt-cross\",\"source_head\":\"2e4e19590e1f3a43620b1f1cb0a9a78153527a63\",\"controller_sha256\":\"08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee\",\"summary_sha256\":\"18c84b299063bdaf327582641f57c76c4a00091b1590116a63f920ec50aca9e6\",\"parts_sha256\":\"2fe94ae646ad096c6868e42d24dbaeed9f64946ea277e1e118502b15e231a5f6\"},\"restored_work_prefixes_verified\":{\"work/detailed-route.drc-40.rpt\":\"0a6d7cbd21554f9eafa41af1763d8c0d9f8a77f62ccf3578711b75c4df18cb37\",\"work/detailed-route.drc-5.rpt\":\"57b8e84bd58aa4353a94f542ba9f50621afbbf9f968ff10505c2482259bb6de4\",\"work/detailed-route.drc-15.rpt\":\"f6981fbe79477e3d8192613a393cc5389fc8576cf94813f6c40b631636282ad8\",\"work/detailed-route.drc-35.rpt\":\"d727de305983839fa910e28ef03ae189a7cef5579cb66379b06c5b1e36ecdbe6\",\"work/native.log\":\"bcfc275fba12aaae1879727ebf90a8fdc9d9833dbd9aa23dd131619498d0f41e\",\"work/detailed-route.drc-30.rpt\":\"83e01795a446cccb4d307946ea957c190509391f96bc9af066796793ebf47107\",\"work/detailed-route.drc-25.rpt\":\"7962785ae5e113a01861749e3757032e65e2311cc53d35386e73618dea5e486a\",\"work/detailed-route.drc-20.rpt\":\"b9b621d931d73bef80ee4450bbecc74ab1316a2ff6af2e5d02435705c20ad8a7\",\"work/detailed-route.drc-10.rpt\":\"38c7202a2a7207fe024c55a6ef2610c673f7e3c2638f7a784676789ed0e1fc7a\",\"work/inspect-environment.tcl\":\"e05f5db4806764796b03d29e899ef0c435641791eecfff0afa498fffed309c3b\",\"work/before-guide-read.odb\":\"2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a\",\"work/boots.log\":\"d6517f61034b9578e0ffe62cf86a12ca3a675a8281fa6ed80f9c4e4fcfd40d48\",\"work/route.tcl\":\"11457b60c2c81c6c64ab44272a14394190255548fe31394497990ffa4e8d0085\"},\"checkpointed_elf_sha256\":\"25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b\",\"checkpoint_images\":{\"cgroup.img\":\"e60493149a7f65df32dddb111652433b9329d6695e3b3d039144248a648fdab1\",\"tmpfs-dev-60.tar.gz.img\":\"6c1e1083b9196f20d5f54528e563c17dbfb7818cfa365d8639c643c3261858a3\",\"tmpfs-dev-58.tar.gz.img\":\"98ddb0c4969448692a13877036c3ef53fa354540f79f5a149156ee67c5582763\",\"fs-1.img\":\"7f4b0d7e95462d792ed60abad81b1ed9866f62b43a0f34a93b1686a627e877b7\",\"core-7.img\":\"66b83d3f7aea58778cdb9b8a931be0015dd2f156eb03189d5de676907dbdde53\",\"core-9.img\":\"ebbea0b5ac8f9e4590918f32facd43cafe700f439182c38b5a55bbed30feb1e5\",\"pagemap-1.img\":\"257298a1119dec3a9ba2eaae4c242612745fc3aaec49aee037bfecd1b5c0ee5b\",\"inventory.img\":\"bfe1374c19a168182cffb7ddc34277bd562dcbb6a92aa64475679dfc167ee129\",\"tmpfs-dev-57.tar.gz.img\":\"cffabac1bb168f99d94da29edf39f36e9ca12666dadaa7c6ff6ed835396b44c8\",\"files.img\":\"f39cc7d59cdc974b9a57b92dcb5b81390277f984fcc7c62ee576d9b007c50745\",\"fdinfo-2.img\":\"87c7027bc903f7eff0e5ab48443bd4dcd747d7f1624322054ab22906eaa689ca\",\"ids-1.img\":\"63a196c2e44563d89bd075e843724b684b2d7c01c360ea4b4ce5bade713444b8\",\"descriptors.json\":\"297597fc6cff151390a7f208d8312a8281228bdc7fddf25de15b0165809e8590\",\"pstree.img\":\"ae0b5a2862d6580bee1d7ab22b7dac4623ac529cc8a2a7d57bdd10458bf0c21e\",\"ipcns-var-10.img\":\"2c6811e94d6ee6661be7bbfbc5ba6fd86325e32599233fb8fe872e79b4047e22\",\"core-1.img\":\"24a38e7ee1e2ab62aeeb49f9ed11700b6393a2d8dabf19a05019ffd8ce2672b9\",\"utsns-11.img\":\"7155ae5d7bbf26829cc53b25ccf76708ee81e7dec52c350684bd5dccc8418e2e\",\"timens-12.img\":\"aabf42ac2756808184fdc19e270bc07979cd5a02bc5e02692880f4570748dc45\",\"mountpoints-13.img\":\"e532d3567f915466756db706b144a22c68bc29eb73dfa18448ede8679c3ffa07\",\"mm-1.img\":\"a07ef3a9516622d29378e642fe150cd7ceca1e7a6f0d36601391fc70ffc0ef2c\",\"core-8.img\":\"d5bd52efb510c45d192fa18f7d658a492c0a7c921e9fbe854730dabfa3536c80\",\"seccomp.img\":\"957296853c04f6368f4ba65b5e86dc74860fec6d7017e51428e65632052e88dd\",\"pages-1.img\":\"d3620f3b3429209f3bc284ce9f8bd1a7f6ba35ca9214254c42f2074eadbdb6f1\"},\"native_process_saved\":true,\"native_log\":{\"bytes\":90392,\"sha256\":\"bcfc275fba12aaae1879727ebf90a8fdc9d9833dbd9aa23dd131619498d0f41e\",\"single_entrypoint\":true,\"optimization_iterations\":[\"0\",\"1\",\"2\",\"3\",\"4\",\"5\",\"6\",\"7\",\"8\",\"9\",\"10\",\"11\",\"12\",\"13\",\"14\",\"15\",\"16\",\"17\",\"18\",\"19\",\"20\",\"21\",\"22\",\"23\",\"24\",\"25\",\"26\",\"27\",\"33\",\"34\",\"35\",\"41\",\"42\"],\"progress\":[{\"percent\":10,\"violations\":0},{\"percent\":20,\"violations\":0},{\"percent\":30,\"violations\":39720},{\"percent\":40,\"violations\":39720},{\"percent\":50,\"violations\":39720},{\"percent\":60,\"violations\":76946},{\"percent\":70,\"violations\":76946},{\"percent\":80,\"violations\":113485},{\"percent\":90,\"violations\":113485},{\"percent\":100,\"violations\":146604},{\"percent\":10,\"violations\":172654},{\"percent\":20,\"violations\":172654},{\"percent\":30,\"violations\":152090},{\"percent\":40,\"violations\":152090},{\"percent\":50,\"violations\":152090},{\"percent\":60,\"violations\":131425},{\"percent\":70,\"violations\":131425},{\"percent\":80,\"violations\":112623},{\"percent\":90,\"violations\":112623},{\"percent\":100,\"violations\":95329},{\"percent\":10,\"violations\":95333},{\"percent\":20,\"violations\":95333},{\"percent\":30,\"violations\":93212},{\"percent\":40,\"violations\":93212},{\"percent\":50,\"violations\":93212},{\"percent\":60,\"violations\":91657},{\"percent\":70,\"violations\":91657},{\"percent\":80,\"violations\":89025},{\"percent\":90,\"violations\":89025},{\"percent\":100,\"violations\":86907},{\"percent\":10,\"violations\":86913},{\"percent\":20,\"violations\":86913},{\"percent\":30,\"violations\":70236},{\"percent\":40,\"violations\":70236},{\"percent\":50,\"violations\":70236},{\"percent\":60,\"violations\":54242},{\"percent\":70,\"violations\":54242},{\"percent\":80,\"violations\":36977},{\"percent\":90,\"violations\":36977},{\"percent\":100,\"violations\":20646},{\"percent\":10,\"violations\":20662},{\"percent\":20,\"violations\":20662},{\"percent\":30,\"violations\":18529},{\"percent\":40,\"violations\":18529},{\"percent\":50,\"violations\":18529},{\"percent\":60,\"violations\":16015},{\"percent\":70,\"violations\":16015},{\"percent\":80,\"violations\":13800},{\"percent\":90,\"violations\":13800},{\"percent\":100,\"violations\":11901},{\"percent\":10,\"violations\":11905},{\"percent\":20,\"violations\":11905},{\"percent\":30,\"violations\":11211},{\"percent\":40,\"violations\":11211},{\"percent\":50,\"violations\":11211},{\"percent\":60,\"violations\":10197},{\"percent\":70,\"violations\":10197},{\"percent\":80,\"violations\":8935},{\"percent\":90,\"violations\":8935},{\"percent\":100,\"violations\":7787},{\"percent\":10,\"violations\":7787},{\"percent\":20,\"violations\":7787},{\"percent\":30,\"violations\":7349},{\"percent\":40,\"violations\":7349},{\"percent\":50,\"violations\":7349},{\"percent\":60,\"violations\":6396},{\"percent\":70,\"violations\":6396},{\"percent\":80,\"violations\":5944},{\"percent\":90,\"violations\":5944},{\"percent\":100,\"violations\":4917},{\"percent\":10,\"violations\":4917},{\"percent\":20,\"violations\":4917},{\"percent\":30,\"violations\":4748},{\"percent\":40,\"violations\":4748},{\"percent\":50,\"violations\":4748},{\"percent\":60,\"violations\":4681},{\"percent\":70,\"violations\":4681},{\"percent\":80,\"violations\":4457},{\"percent\":90,\"violations\":4457},{\"percent\":100,\"violations\":4328},{\"percent\":10,\"violations\":4328},{\"percent\":20,\"violations\":4328},{\"percent\":30,\"violations\":4228},{\"percent\":40,\"violations\":4228},{\"percent\":50,\"violations\":4228},{\"percent\":60,\"violations\":4043},{\"percent\":70,\"violations\":4043},{\"percent\":80,\"violations\":3788},{\"percent\":90,\"violations\":3788},{\"percent\":100,\"violations\":3605},{\"percent\":10,\"violations\":3605},{\"percent\":20,\"violations\":3605},{\"percent\":30,\"violations\":3410},{\"percent\":40,\"violations\":3410},{\"percent\":50,\"violations\":3410},{\"percent\":60,\"violations\":3121},{\"percent\":70,\"violations\":3121},{\"percent\":80,\"violations\":3013},{\"percent\":90,\"violations\":3013},{\"percent\":100,\"violations\":3007},{\"percent\":10,\"violations\":3007},{\"percent\":20,\"violations\":3007},{\"percent\":30,\"violations\":2634},{\"percent\":40,\"violations\":2634},{\"percent\":50,\"violations\":2634},{\"percent\":60,\"violations\":2096},{\"percent\":70,\"violations\":2096},{\"percent\":80,\"violations\":1942},{\"percent\":90,\"violations\":1942},{\"percent\":100,\"violations\":1713},{\"percent\":10,\"violations\":1713},{\"percent\":20,\"violations\":1713},{\"percent\":30,\"violations\":1280},{\"percent\":40,\"violations\":1280},{\"percent\":50,\"violations\":1280},{\"percent\":60,\"violations\":1216},{\"percent\":70,\"violations\":1216},{\"percent\":80,\"violations\":1104},{\"percent\":90,\"violations\":1104},{\"percent\":100,\"violations\":889},{\"percent\":10,\"violations\":889},{\"percent\":20,\"violations\":889},{\"percent\":30,\"violations\":842},{\"percent\":40,\"violations\":842},{\"percent\":50,\"violations\":842},{\"percent\":60,\"violations\":804},{\"percent\":70,\"violations\":804},{\"percent\":80,\"violations\":766},{\"percent\":90,\"violations\":766},{\"percent\":100,\"violations\":525},{\"percent\":10,\"violations\":525},{\"percent\":20,\"violations\":525},{\"percent\":30,\"violations\":514},{\"percent\":40,\"violations\":514},{\"percent\":50,\"violations\":514},{\"percent\":60,\"violations\":496},{\"percent\":70,\"violations\":496},{\"percent\":80,\"violations\":485},{\"percent\":90,\"violations\":485},{\"percent\":100,\"violations\":485},{\"percent\":10,\"violations\":485},{\"percent\":20,\"violations\":485},{\"percent\":30,\"violations\":469},{\"percent\":40,\"violations\":469},{\"percent\":50,\"violations\":469},{\"percent\":60,\"violations\":436},{\"percent\":70,\"violations\":436},{\"percent\":80,\"violations\":434},{\"percent\":90,\"violations\":434},{\"percent\":100,\"violations\":396},{\"percent\":10,\"violations\":396},{\"percent\":20,\"violations\":396},{\"percent\":30,\"violations\":337},{\"percent\":40,\"violations\":337},{\"percent\":50,\"violations\":337},{\"percent\":60,\"violations\":335},{\"percent\":70,\"violations\":335},{\"percent\":80,\"violations\":335},{\"percent\":90,\"violations\":335},{\"percent\":100,\"violations\":334},{\"percent\":10,\"violations\":334},{\"percent\":20,\"violations\":334},{\"percent\":30,\"violations\":333},{\"percent\":40,\"violations\":333},{\"percent\":50,\"violations\":333},{\"percent\":60,\"violations\":310},{\"percent\":70,\"violations\":310},{\"percent\":80,\"violations\":310},{\"percent\":90,\"violations\":310},{\"percent\":100,\"violations\":301},{\"percent\":10,\"violations\":301},{\"percent\":20,\"violations\":301},{\"percent\":30,\"violations\":1273},{\"percent\":40,\"violations\":1273},{\"percent\":50,\"violations\":1273},{\"percent\":60,\"violations\":2593},{\"percent\":70,\"violations\":2593},{\"percent\":80,\"violations\":3574},{\"percent\":90,\"violations\":3574},{\"percent\":100,\"violations\":5394},{\"percent\":10,\"violations\":5394},{\"percent\":20,\"violations\":5394},{\"percent\":30,\"violations\":5231},{\"percent\":40,\"violations\":5231},{\"percent\":50,\"violations\":5231},{\"percent\":60,\"violations\":2303},{\"percent\":70,\"violations\":2303},{\"percent\":80,\"violations\":2303},{\"percent\":90,\"violations\":2303},{\"percent\":100,\"violations\":399},{\"percent\":10,\"violations\":399},{\"percent\":20,\"violations\":399},{\"percent\":30,\"violations\":396},{\"percent\":40,\"violations\":396},{\"percent\":50,\"violations\":396},{\"percent\":60,\"violations\":336},{\"percent\":70,\"violations\":336},{\"percent\":80,\"violations\":336},{\"percent\":90,\"violations\":336},{\"percent\":100,\"violations\":265},{\"percent\":10,\"violations\":265},{\"percent\":20,\"violations\":265},{\"percent\":30,\"violations\":265},{\"percent\":40,\"violations\":265},{\"percent\":50,\"violations\":265},{\"percent\":60,\"violations\":239},{\"percent\":70,\"violations\":239},{\"percent\":80,\"violations\":239},{\"percent\":90,\"violations\":239},{\"percent\":100,\"violations\":222},{\"percent\":10,\"violations\":222},{\"percent\":20,\"violations\":222},{\"percent\":30,\"violations\":222},{\"percent\":40,\"violations\":222},{\"percent\":50,\"violations\":222},{\"percent\":60,\"violations\":174},{\"percent\":70,\"violations\":174},{\"percent\":80,\"violations\":167},{\"percent\":90,\"violations\":167},{\"percent\":100,\"violations\":161},{\"percent\":10,\"violations\":161},{\"percent\":20,\"violations\":161},{\"percent\":30,\"violations\":161},{\"percent\":40,\"violations\":161},{\"percent\":50,\"violations\":161},{\"percent\":60,\"violations\":155},{\"percent\":70,\"violations\":155},{\"percent\":80,\"violations\":154},{\"percent\":90,\"violations\":154},{\"percent\":100,\"violations\":154},{\"percent\":10,\"violations\":154},{\"percent\":20,\"violations\":154},{\"percent\":30,\"violations\":154},{\"percent\":40,\"violations\":154},{\"percent\":50,\"violations\":154},{\"percent\":60,\"violations\":154},{\"percent\":70,\"violations\":154},{\"percent\":80,\"violations\":154},{\"percent\":90,\"violations\":154},{\"percent\":100,\"violations\":154},{\"percent\":10,\"violations\":154},{\"percent\":20,\"violations\":154},{\"percent\":30,\"violations\":154},{\"percent\":40,\"violations\":154},{\"percent\":50,\"violations\":154},{\"percent\":60,\"violations\":154},{\"percent\":70,\"violations\":154},{\"percent\":80,\"violations\":154},{\"percent\":90,\"violations\":154},{\"percent\":100,\"violations\":154},{\"percent\":10,\"violations\":154},{\"percent\":20,\"violations\":1086},{\"percent\":30,\"violations\":1086},{\"percent\":40,\"violations\":1086},{\"percent\":50,\"violations\":1412},{\"percent\":60,\"violations\":1412},{\"percent\":70,\"violations\":2534},{\"percent\":80,\"violations\":2534},{\"percent\":90,\"violations\":2534},{\"percent\":100,\"violations\":4123},{\"percent\":10,\"violations\":4123},{\"percent\":20,\"violations\":4123},{\"percent\":30,\"violations\":4089},{\"percent\":40,\"violations\":4089},{\"percent\":50,\"violations\":4089},{\"percent\":60,\"violations\":2115},{\"percent\":70,\"violations\":2115},{\"percent\":80,\"violations\":2115},{\"percent\":90,\"violations\":2115},{\"percent\":100,\"violations\":220},{\"percent\":10,\"violations\":220},{\"percent\":20,\"violations\":220},{\"percent\":30,\"violations\":217},{\"percent\":40,\"violations\":217},{\"percent\":50,\"violations\":217},{\"percent\":60,\"violations\":128},{\"percent\":70,\"violations\":128},{\"percent\":80,\"violations\":128},{\"percent\":90,\"violations\":128},{\"percent\":100,\"violations\":82},{\"percent\":10,\"violations\":82},{\"percent\":20,\"violations\":82},{\"percent\":30,\"violations\":76},{\"percent\":40,\"violations\":76},{\"percent\":50,\"violations\":76},{\"percent\":60,\"violations\":76},{\"percent\":70,\"violations\":73},{\"percent\":80,\"violations\":73},{\"percent\":90,\"violations\":72},{\"percent\":100,\"violations\":72},{\"percent\":10,\"violations\":72},{\"percent\":20,\"violations\":72},{\"percent\":30,\"violations\":72},{\"percent\":40,\"violations\":72},{\"percent\":50,\"violations\":72},{\"percent\":60,\"violations\":72},{\"percent\":70,\"violations\":72},{\"percent\":80,\"violations\":50},{\"percent\":90,\"violations\":50},{\"percent\":100,\"violations\":50},{\"percent\":10,\"violations\":50},{\"percent\":20,\"violations\":50},{\"percent\":30,\"violations\":50},{\"percent\":40,\"violations\":50},{\"percent\":50,\"violations\":50},{\"percent\":60,\"violations\":50},{\"percent\":70,\"violations\":49},{\"percent\":80,\"violations\":49},{\"percent\":90,\"violations\":49},{\"percent\":100,\"violations\":47},{\"percent\":10,\"violations\":47},{\"percent\":20,\"violations\":47},{\"percent\":30,\"violations\":47},{\"percent\":40,\"violations\":47},{\"percent\":50,\"violations\":47},{\"percent\":60,\"violations\":47},{\"percent\":70,\"violations\":47},{\"percent\":80,\"violations\":47},{\"percent\":90,\"violations\":47},{\"percent\":100,\"violations\":47},{\"percent\":10,\"violations\":47},{\"percent\":20,\"violations\":47},{\"percent\":30,\"violations\":47},{\"percent\":40,\"violations\":47},{\"percent\":50,\"violations\":47},{\"percent\":60,\"violations\":47},{\"percent\":70,\"violations\":47},{\"percent\":80,\"violations\":29},{\"percent\":90,\"violations\":29},{\"percent\":100,\"violations\":27},{\"percent\":10,\"violations\":1601},{\"percent\":20,\"violations\":1601},{\"percent\":30,\"violations\":1601},{\"percent\":40,\"violations\":3233},{\"percent\":50,\"violations\":3233},{\"percent\":60,\"violations\":4496},{\"percent\":70,\"violations\":4850},{\"percent\":80,\"violations\":4850},{\"percent\":90,\"violations\":6385},{\"percent\":100,\"violations\":6385},{\"percent\":10,\"violations\":6385},{\"percent\":20,\"violations\":6385},{\"percent\":30,\"violations\":5540},{\"percent\":40,\"violations\":5540},{\"percent\":50,\"violations\":5540},{\"percent\":60,\"violations\":261},{\"percent\":70,\"violations\":261},{\"percent\":80,\"violations\":261},{\"percent\":90,\"violations\":261},{\"percent\":100,\"violations\":261},{\"percent\":10,\"violations\":261},{\"percent\":20,\"violations\":261},{\"percent\":30,\"violations\":259},{\"percent\":40,\"violations\":259},{\"percent\":50,\"violations\":259},{\"percent\":60,\"violations\":53},{\"percent\":70,\"violations\":53},{\"percent\":80,\"violations\":53},{\"percent\":90,\"violations\":53},{\"percent\":100,\"violations\":53},{\"percent\":10,\"violations\":53},{\"percent\":20,\"violations\":53},{\"percent\":30,\"violations\":53},{\"percent\":40,\"violations\":41},{\"percent\":50,\"violations\":41},{\"percent\":60,\"violations\":41},{\"percent\":70,\"violations\":20},{\"percent\":80,\"violations\":20},{\"percent\":100,\"violations\":19},{\"percent\":10,\"violations\":19},{\"percent\":30,\"violations\":19},{\"percent\":50,\"violations\":19},{\"percent\":60,\"violations\":19},{\"percent\":80,\"violations\":19},{\"percent\":100,\"violations\":19},{\"percent\":10,\"violations\":19},{\"percent\":30,\"violations\":19},{\"percent\":50,\"violations\":8},{\"percent\":60,\"violations\":8},{\"percent\":80,\"violations\":8},{\"percent\":100,\"violations\":8},{\"percent\":20,\"violations\":8},{\"percent\":50,\"violations\":8},{\"percent\":70,\"violations\":8},{\"percent\":100,\"violations\":8},{\"percent\":20,\"violations\":8},{\"percent\":50,\"violations\":8},{\"percent\":70,\"violations\":8},{\"percent\":100,\"violations\":8},{\"percent\":10,\"violations\":668},{\"percent\":20,\"violations\":668},{\"percent\":30,\"violations\":668},{\"percent\":40,\"violations\":1070},{\"percent\":50,\"violations\":1070},{\"percent\":60,\"violations\":1588},{\"percent\":70,\"violations\":1588},{\"percent\":80,\"violations\":1588},{\"percent\":90,\"violations\":3879},{\"percent\":100,\"violations\":3879},{\"percent\":10,\"violations\":3883},{\"percent\":20,\"violations\":3883},{\"percent\":30,\"violations\":3313},{\"percent\":40,\"violations\":3313},{\"percent\":50,\"violations\":3313}],\"completed_violation_counts\":[172654,95333,86913,20662,11905,7787,4917,4328,3605,3007,1713,889,525,485,396,334,301,5394,399,265,222,161,154,154,154,4123,220,82,72,50,47,47,27,6385,261,53,19,19,8,8,8,3883]},\"error\":\"AssertionError('No observable native DRT progress after cross-runner restore')\",\"traceback\":\"Traceback (most recent call last):\\n  File \\\"/home/runner/work/nssoc/nssoc/scripts/cloud_mainchip_route12_drt_continuation.py\\\", line 352, in main\\n    assert len(raw)>len(prefix),'No observable native DRT progress after cross-runner restore'\\n           ^^^^^^^^^^^^^^^^^^^^\\nAssertionError: No observable native DRT progress after cross-runner restore\\n\"}")
REQUIRED_INPUTS=json.loads("{\"scripts/cloud_mainchip_process_checkpoint.py\":\"b1ec1b367a17ae4bdc07683f9aa8a12628dd3c5430e441c179a94c54984cbc63\",\"scripts/compare_cloud_routed_endpoints.py\":\"15ead8483a372a713a4d68aa36e00a7ee05b5c9528c6ece4f5b4bd2d5c20ad42\",\"scripts/run_cloud_tx_layout_repair.py\":\"312391426bd8505b6d6d32fdc5ffec7a76ddfc83b2f4d72543a40d6332e28a3f\",\"scripts/cloud_chunked_results.py\":\"fe414dcd92c233554a82a2151232bab8803e6ec7863df3872fbde009d3905816\",\"scripts/publish_cloud_results.py\":\"a5cd154c1a7e3f838f5880e6cabef115245d696485c9eda2bd0451da8e1e1296\",\"docs/evidence/mainchip-portable-runtime-pass-20261020.json\":\"165629f8ec5b3ff99b9b9c01464b7fb129fb991ee9c5287e19de614c36e62e18\",\"docs/evidence/mainchip-cross-runner-native-checkpoint-pass-20261021.json\":\"751718384fa5ccb4036cfdbf69543e7742e73f3ede41ad7f7954e93a11f92822\",\"scripts/cloud_mainchip_route12_drt.py\":\"00ea591918771c60522a657e954b07b3a7d826dbb0b7fd70749aee49a3a81583\",\"docs/evidence/mainchip-route12-global-pass-20261023.json\":\"b1f5ba79b842b4a4dc2667b6a5eea58e75df897376f373cec20ab6d0390b2729\",\"scripts/cloud_mainchip_route12_drt_continuation.py\":\"08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee\",\"scripts/mainchip-route12-drt-methods.json\":\"eb71f5f616bed3b17e5cbeea8ae657c874b8b174653caf349d388dc8d94db010\",\"cloud-mainchip-route12-drt-runtime/input/result.json\":\"21e8f082931a30e8ae074d34843c828502a80e0719b778e6a8686a04fc976bc2\",\"cloud-mainchip-route12-drt-runtime/input/native-image.tar\":\"c8448ddce6e02b2f23ddd84245a71ae43c2b4b8537c5e1bdaf80fc4ef8882f9d\",\"cloud-mainchip-route12-drt-runtime/input/runtime-inventory.json\":\"f0dd493a1f5106da8a86bf0de6821d6ddbeed25050717c5706225c3d4fdfdbfa\",\"cloud-mainchip-route12-drt-runtime/global/fixed-clock.json\":\"a72f0e7f03405f5c61961b14b721c822f25df143ce67546cf3e93c7db4b210e5\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/fresh_fanout_native.tcl\":\"dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/fresh-fanout-global.odb\":\"2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/fresh-fanout.guide\":\"54ae78b49f70b05e007edc151c67c64a7eed4fd9a9ce0aed6d7898bb3286dcde\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/_env.tcl\":\"255d39b6b296466fae51428718fd9fdd5019594fdf6d1c2cbdd116ac52e8c8f0\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/config.json\":\"c6dfea371e243881a4ae20499da8726980c83224ea31e1b4e5fe7bb44cbccaaa\",\"cloud-mainchip-route12-drt-runtime/global/candidate-state.json\":\"647d7347c0676ac2d08112164b6917b5c45185067c2deef808e404f7434518ba\",\"cloud-mainchip-route12-drt-runtime/global/geometry/result.json\":\"3f0141703d3531e11a2f7e7c1fc7d66a1fdc133723f473005aeeede216b84083\",\"cloud-mainchip-route12-drt-runtime/global/trial-config.json\":\"b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f\",\"cloud-mainchip-route12-drt-runtime/global/result.json\":\"0c7f6a86849d32ae853726ab448da0e4c2f71373956220c95c434657247e9d60\",\"cloud-mainchip-route12-drt-runtime/flow-config/trial-config.json\":\"b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f\",\"cloud-mainchip-route12-drt-runtime/work/route.tcl\":\"11457b60c2c81c6c64ab44272a14394190255548fe31394497990ffa4e8d0085\",\"cloud-mainchip-route12-drt-runtime/work/before-guide-read.odb\":\"2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a\"}")
MISSING_HISTORICAL=('sources_unchanged','active_drt_cross_runner_progress_proven','continuation','next_action')
def digest(b):return hashlib.sha256(b).hexdigest()

def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def consume(inp,target,size,sha):
    h=hashlib.sha256();n=0
    with target.open('xb')as out:
        for b in iter(lambda:inp.read(1048576),b''):
            n+=len(b);assert n<=size,'Archive overrun'
            h.update(b);out.write(b)
    assert n==size and h.hexdigest()==sha,'Truncated or corrupt archive'
    assert target.stat().st_size==size and file_sha(target)==sha
    return dict(bytes=n,sha256=h.hexdigest(),complete_stream_verified=True)

def index(z,count):
    files={};dirs=set()
    for i in z.infolist():
        n=i.filename
        assert n and '\\'not in n and ':'not in n and all(ord(c)>=32 and ord(c)!=127 for c in n)
        p=PurePosixPath(n);assert not p.is_absolute()and '..'not in p.parts
        canonical=str(p)
        assert canonical not in ('','.','/')and n==canonical+('/'if i.is_dir()else'')
        assert not(i.flag_bits&1),'Encrypted archive member'
        kind=stat.S_IFMT(i.external_attr>>16)
        if i.is_dir():
            assert kind in(0,stat.S_IFDIR)and canonical not in dirs
            dirs.add(canonical);continue
        assert kind in(0,stat.S_IFREG),'Archive links or special files are forbidden'
        assert n not in files and i.compress_type in(zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
        assert 0<=i.file_size<=128*1024**3
        files[n]=i
    assert len(files)==count and not(set(files)&dirs)
    assert sum(i.file_size for i in files.values())<=128*1024**3
    for name in set(files)|dirs:
        assert not any(str(p)in files for p in PurePosixPath(name).parents if str(p)!='.')
    return files

def hosted():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Cloud runner only'
    assert os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    assert int(os.environ['GITHUB_RUN_ID'])not in(RUN,PUB_RUN)
def api(path):
    return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['diagnostic_only']is True and m['normal_continuation_allowed']is False
    for n,h in m['protected'].items():assert file_sha(ROOT/n)==h,n
    assert file_sha(ROOT/CONTROLLER)==CONTROLLER_SHA
    return m
def asset_valid(meta,aid):
    expected=ASSETS[str(aid)]
    assert meta['id']==aid and meta['name']==expected['name']
    assert meta['size']==expected['bytes'] and meta['digest']=='sha256:'+expected['sha256']
    assert meta['state']=='uploaded'
def raw_valid(raw,aid):
    expected=ASSETS[str(aid)]
    assert len(raw)==expected['bytes'] and digest(raw)==expected['sha256'],aid
def small_asset(aid):
    assert ASSETS[str(aid)]['bytes']<=1024*1024
    asset_valid(api('releases/assets/'+str(aid)),aid)
    raw=subprocess.check_output(['gh','api','--allow-escape-sequences',REPO+'releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
    raw_valid(raw,aid)
    return raw
def identities(run,job,pub,jobs,release,tag):
    assert (run['id'],run['head_sha'],run['run_attempt'],run['status'],run['conclusion'])==(RUN,HEAD,1,'completed','failure')
    assert run['head_branch']=='codex/complete-open-work'and run['event']=='workflow_dispatch'
    assert run['path']=='.github/workflows/mainchip-route12-drt-continuation-cloud.yml'
    assert (job['id'],job['run_id'],job['head_sha'],job['run_attempt'],job['status'],job['conclusion'],job['name'])==(120877858005,RUN,HEAD,1,'completed','failure','continuation')
    assert (pub['id'],pub['head_sha'],pub['run_attempt'],pub['status'],pub['conclusion'])==(PUB_RUN,PUB_HEAD,1,'completed','success')
    assert pub['event']=='workflow_dispatch'and pub['path']=='.github/workflows/mainchip-route12-recovery-publication-cloud.yml'
    expected={120936900265:'controls',120937819252:'publication'}
    assert {j['id']:j['name']for j in jobs}==expected
    for j in jobs:
        assert (j['run_id'],j['head_sha'],j['run_attempt'],j['status'],j['conclusion'])==(PUB_RUN,PUB_HEAD,1,'completed','success')
    assert (release['id'],release['tag_name'],release['target_commitish'])==(RELEASE,TAG,PUB_HEAD)
    assert release['draft']is False and release['prerelease']is True
    assert tag['object']==dict(sha=PUB_HEAD,type='commit',url=tag['object']['url'])
    assert tag['ref']=='refs/tags/'+TAG
    assets={a['id']:a for a in release['assets']}
    assert len(assets)==len(release['assets'])
    for aid in ASSETS:asset_valid(assets[int(aid)],int(aid))
def semantic_report(report,inventory,parent):
    # Exact field values are independently frozen from the authenticated failure.
    for k,v in REPORT_CORE.items():assert report[k]==v,('Changed rejected receipt field',k)
    assert all(k not in report for k in MISSING_HISTORICAL),'Invented historical acceptance/proof'
    assert report['segment_elapsed_s']==7208.332329252
    assert len(report['controls'])==4 and all(x['rejected']is True for x in report['controls'])
    assert len(inventory)==65 and len(report['outputs'])==63
    assert set(inventory)==set(report['outputs'])|{'result.json','criu-build.log'}
    for n,h in report['outputs'].items():assert inventory[n]['sha256']==h,n
    assert inventory['result.json']['sha256']==ASSETS[str(REPORT_ID)]['sha256']
    images={n.removeprefix('checkpoints/state/'):v['sha256']for n,v in inventory.items()if n.startswith('checkpoints/state/')}
    assert len(images)==23 and images==report['checkpoint_images']
    assert {n for n in images if n.startswith('core-')}=={'core-1.img','core-7.img','core-8.img','core-9.img'}
    assert {'pstree.img','mm-1.img','pagemap-1.img','pages-1.img','inventory.img','descriptors.json'}<=images.keys()
    assert inventory['checkpoints/state/pages-1.img']['bytes']==9550823424
    work={n:v['sha256']for n,v in inventory.items()if n.startswith('work/')}
    assert len(work)==13 and work==report['restored_work_prefixes_verified']
    assert parent['run_id']==40085912519 and parent['source_head']=='2e4e19590e1f3a43620b1f1cb0a9a78153527a63'
    assert parent['sources_unchanged']is True and parent['active_drt_cross_runner_progress_proven']is True
    assert parent['status']=='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF'
    assert report['previous_boot_id']==parent['boot_id'] and report['boot_id']!=parent['boot_id']
    assert report['route_script']==parent['route_script']and report['runtime_source']==parent['runtime_source']
    for n,h in work.items():assert parent['outputs'][n]==h,n
    assert report['criu_build']['source_commit']=='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
    assert report['criu_build']['binary_sha256']=='0f2c9f802f03b486d1b7dc752abf3e28a378bdadcb7609f6cbbaca5cb0953b13'
    assert report['criu_build']['version']=='Version: 4.2.1\nGitID: 9539417\n'
    assert parent['criu_build']['source_commit']==report['criu_build']['source_commit']
    for c in report['commands']:assert inventory[c['label']+'.log']['sha256']==c['log_sha256']
def publication_valid(p):
    assert p['status']=='PASS_REPUBLISHED_EXACT65_MEMBER_ARCHIVE_AND_EMPTY_INVENTORY_ROUTING_STILL_REJECTED'
    assert p['source_head']==PUB_HEAD and p['run_id']==str(PUB_RUN)
    for k in ('native_execution','native_process_restored','saved_process_validated','route_complete','continuation_accepted','final_timing_complete','full_phy_accepted'):assert p[k]is False,k
    assert len(p['publication_controls']['rejected'])==32 and len(p['original_transport_controls']['rejected'])==29 and len(p['release_controls']['rejected'])==17
    assert p['outer_restore']['files']==40 and p['outer_restore']['all_outer_CRC_and_member_hashes_verified']is True
    assert p['original_archive_proof']['original_inner_zip_byte_identical']is True
    assert p['original_archive_proof']['bytes']==ASSETS[str(ZIP_ID)]['bytes']
    assert p['original_archive_proof']['sha256']==ASSETS[str(ZIP_ID)]['sha256']
    assert len(p['publication_plan']['empty_files'])==9
def frozen_log_proof(raw,boots):
    source=(ROOT/CONTROLLER).read_text();assert digest(source.encode())==CONTROLLER_SHA
    tree=ast.parse(source)
    n=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='log_proof')
    ns=dict(re=re,digest=digest)
    exec(compile(ast.get_source_segment(source,n),'<frozen-original-log-proof>','exec'),ns)
    return ns['log_proof'](raw,boots)
def descriptor():
    return dict(schema='rejected-capsule-observation-only-v1',run=RUN,attempt=1,
        source_head=HEAD,original_result_sha256=ASSETS[str(REPORT_ID)]['sha256'],
        archive_asset_id=ZIP_ID,archive_bytes=ASSETS[str(ZIP_ID)]['bytes'],
        archive_sha256=ASSETS[str(ZIP_ID)]['sha256'],publication_run=PUB_RUN,
        publication_head=PUB_HEAD,release_id=RELEASE,diagnostic_only=True,
        saved_process_validated=False,normal_continuation_allowed=False,
        historical_missing_fields=list(MISSING_HISTORICAL))
def rejected_receipt():
    hosted();methods()
    run=api('actions/runs/'+str(RUN));job=api('actions/jobs/120877858005')
    pub=api('actions/runs/'+str(PUB_RUN));jobs=api('actions/runs/'+str(PUB_RUN)+'/jobs?filter=latest&per_page=100')['jobs']
    release=api('releases/'+str(RELEASE));tag=api('git/ref/tags/'+TAG)
    identities(run,job,pub,jobs,release,tag)
    raw={str(aid):small_asset(int(aid)) for aid in ASSETS if int(aid)!=ZIP_ID}
    report=json.loads(raw[str(REPORT_ID)]);inventory=json.loads(raw[str(INVENTORY_ID)])
    parent=json.loads(raw['672871943']);publication=json.loads(raw['672873325'])
    semantic_report(report,inventory,parent);publication_valid(publication)
    log=raw['672871178']
    assert b'line 352, in main'in log and b'AssertionError: No observable native DRT progress after cross-runner restore'in log
    assert b'HTTP 403: Resource not accessible by integration'in log
    assert frozen_log_proof(raw['672872982'],raw['672872838'])==report['native_log']
    assert raw['672871331'].decode().split()[0]==report['checkpointed_elf_sha256']
    assert digest(raw['672873044'])==report['route_script']['sha256']
    return dict(report=report,inventory=inventory,parent=parent,publication=publication,
        descriptor=descriptor(),raw_hex={k:v.hex()for k,v in raw.items()},
        metadata=dict(run=run,job=job,publication_run=pub,publication_jobs=jobs,release=release,tag=tag))
def validate_pin(pin):
    assert pin['descriptor']==descriptor()
    raw={k:bytes.fromhex(v)for k,v in pin['raw_hex'].items()}
    assert set(raw)==set(ASSETS)-{str(ZIP_ID)}
    for aid,b in raw.items():raw_valid(b,int(aid))
    for key,aid in [('report',REPORT_ID),('inventory',INVENTORY_ID),('parent',672871943),('publication',672873325)]:
        assert pin[key]==json.loads(raw[str(aid)])
    semantic_report(pin['report'],pin['inventory'],pin['parent']);publication_valid(pin['publication'])
    m=pin['metadata'];identities(m['run'],m['job'],m['publication_run'],m['publication_jobs'],m['release'],m['tag'])
    return raw
def download_zip(target):
    asset_valid(api('releases/assets/'+str(ZIP_ID)),ZIP_ID)
    p=subprocess.Popen(['gh','api','--allow-escape-sequences',REPO+'releases/assets/'+str(ZIP_ID),'-H','Accept: application/octet-stream'],stdout=subprocess.PIPE)
    try:proof=consume(p.stdout,target,ASSETS[str(ZIP_ID)]['bytes'],ASSETS[str(ZIP_ID)]['sha256'])
    except BaseException:
        p.stdout.close()
        if p.poll()is None:p.terminate()
        p.wait();raise
    else:
        p.stdout.close();assert p.wait()==0
    return proof
def scan_extract(z,expected,selected,target):
    # Exact65 production inventory is validated by caller; this primitive also
    # accepts tiny controls so the same streaming/CRC/path code can be exercised.
    files=index(z,len(expected));assert set(files)==set(expected)
    assert len(selected)==len(set(selected))and set(selected)<=set(files)
    for name,i in files.items():
        e=expected[name]
        assert (i.file_size,i.compress_size,i.CRC)==(e['bytes'],e['compressed_bytes'],e['crc32']),name
    target.mkdir(exist_ok=False);actual={}
    for name,i in sorted(files.items()):
        dest=target/name if name in selected else None
        if dest:
            dest.parent.mkdir(parents=True,exist_ok=True)
            assert not dest.exists()and not dest.is_symlink()
        h=hashlib.sha256();count=0;f=dest.open('xb')if dest else None
        try:
            with z.open(i,'r')as inp:
                for b in iter(lambda:inp.read(1048576),b''):
                    count+=len(b);assert count<=expected[name]['bytes']
                    h.update(b)
                    if f:f.write(b)
        finally:
            if f:f.close()
        assert count==expected[name]['bytes']and h.hexdigest()==expected[name]['sha256'],name
        actual[name]=dict(bytes=count,sha256=h.hexdigest(),crc32=i.CRC,compressed_bytes=i.compress_size)
        if dest:assert dest.stat().st_size==count and file_sha(dest)==h.hexdigest()
    assert {str(p.relative_to(target))for p in target.rglob('*')if p.is_file()}==set(selected)
    return actual
def selected_names(pin,old_names):
    expected=sorted(n for n in pin['inventory']if n.startswith(('work/','checkpoints/')))
    assert len(expected)==36
    assert isinstance(old_names,(list,tuple))and len(old_names)==36 and len(set(old_names))==36
    assert sorted(old_names)==expected
    return expected+['result.json']
def restore_failed_capsule(pin,target,old_names):
    hosted();methods();raw=validate_pin(pin);target=Path(target)
    assert target.is_absolute()and not target.exists()and not target.is_symlink()
    assert target.parent.is_dir()and target.parent.resolve()==target.parent
    selected=selected_names(pin,old_names)
    needed=ASSETS[str(ZIP_ID)]['bytes']+sum(pin['inventory'][n]['bytes']for n in selected)+1024**3
    assert shutil.disk_usage(target.parent).free>=needed
    with tempfile.TemporaryDirectory(prefix='rejected-route-capsule-',dir=target.parent)as td:
        temp=Path(td);archive=temp/'original.zip';transport=download_zip(archive)
        stage=temp/'verified'
        with zipfile.ZipFile(archive)as z:actual=scan_extract(z,pin['inventory'],selected,stage)
        assert (stage/'result.json').read_bytes()==raw[str(REPORT_ID)]
        assert frozen_log_proof((stage/'work/native.log').read_bytes(),(stage/'work/boots.log').read_bytes())==pin['report']['native_log']
        assert (stage/'work/route.tcl').read_bytes()==raw['672873044']
        semantic_report(pin['report'],actual,pin['parent'])
        assert not target.exists()and not target.is_symlink()
        stage.rename(target)
    return copy.deepcopy(pin['report']),dict(status='RESTORED_EXACT_REJECTED_BYTES_FOR_DIAGNOSTIC_ONLY',
        archive=transport,all65_members=actual,selected_files={n:actual[n]for n in selected},
        full_archive_verified_before_extraction=True,all65_CRC_and_SHA256_verified=True,
        original_report_unmodified=True,historical_missing_fields=list(MISSING_HISTORICAL),
        image_file_topology_and_bytes_exact=True,image_internal_state_validated=False,
        native_process_restored=False,saved_process_validated=False,normal_continuation_allowed=False,
        route_complete=False,final_timing_complete=False,full_phy_accepted=False)
def validate_current_rows(rows,phase,previous=None,required=None):
    assert phase in('before_restore','after_restore')
    assert isinstance(rows,dict)and rows
    required=REQUIRED_INPUTS if required is None else required
    seen={};copy_rows={}
    for label,row in rows.items():
        assert isinstance(label,str)and label and set(row)=={'path','expected_sha256','actual_sha256'}
        p=Path(row['path']);assert p.is_absolute()and p.resolve()==p and p.is_file()and not p.is_symlink()
        assert str(p)not in seen
        expected=row['expected_sha256'];assert re.fullmatch('[0-9a-f]{64}',expected)
        assert row['actual_sha256']==expected and file_sha(p)==expected
        seen[str(p)]=expected;copy_rows[label]=dict(row)
    for n,h in required.items():assert seen.get(str(ROOT/n))==h,('Missing authenticated current input',n)
    if previous is not None:
        assert phase=='after_restore'and previous['phase']=='before_restore'
        assert {k:(v['path'],v['expected_sha256'])for k,v in copy_rows.items()}=={k:(v['path'],v['expected_sha256'])for k,v in previous['files'].items()}
    return dict(phase=phase,files=copy_rows,independent_streamed_hashes_verified=True,
        historical_sources_unchanged_proven=False,normal_continuation_allowed=False)
def verify_current_inputs(callback,phase,previous=None):
    hosted();methods()
    return validate_current_rows(callback(),phase,previous)
