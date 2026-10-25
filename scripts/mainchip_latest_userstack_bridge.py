#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate latest40120760532 file bridge; old40095811631 admission is immutable."""
import copy,hashlib,json,os,re,shutil
from pathlib import Path
import mainchip_latest_stack_admission as latest
from mainchip_userstack_identity import file_sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/mainchip-userstack-native-methods.json'
REQUIRED_INPUTS=json.loads("{\"scripts/cloud_mainchip_process_checkpoint.py\":\"b1ec1b367a17ae4bdc07683f9aa8a12628dd3c5430e441c179a94c54984cbc63\",\"scripts/compare_cloud_routed_endpoints.py\":\"15ead8483a372a713a4d68aa36e00a7ee05b5c9528c6ece4f5b4bd2d5c20ad42\",\"scripts/run_cloud_tx_layout_repair.py\":\"312391426bd8505b6d6d32fdc5ffec7a76ddfc83b2f4d72543a40d6332e28a3f\",\"scripts/cloud_chunked_results.py\":\"fe414dcd92c233554a82a2151232bab8803e6ec7863df3872fbde009d3905816\",\"scripts/publish_cloud_results.py\":\"a5cd154c1a7e3f838f5880e6cabef115245d696485c9eda2bd0451da8e1e1296\",\"docs/evidence/mainchip-portable-runtime-pass-20261020.json\":\"165629f8ec5b3ff99b9b9c01464b7fb129fb991ee9c5287e19de614c36e62e18\",\"docs/evidence/mainchip-cross-runner-native-checkpoint-pass-20261021.json\":\"751718384fa5ccb4036cfdbf69543e7742e73f3ede41ad7f7954e93a11f92822\",\"scripts/cloud_mainchip_route12_drt.py\":\"00ea591918771c60522a657e954b07b3a7d826dbb0b7fd70749aee49a3a81583\",\"docs/evidence/mainchip-route12-global-pass-20261023.json\":\"b1f5ba79b842b4a4dc2667b6a5eea58e75df897376f373cec20ab6d0390b2729\",\"scripts/cloud_mainchip_route12_drt_continuation.py\":\"08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee\",\"scripts/mainchip-route12-drt-methods.json\":\"eb71f5f616bed3b17e5cbeea8ae657c874b8b174653caf349d388dc8d94db010\",\"cloud-mainchip-route12-drt-runtime/input/result.json\":\"21e8f082931a30e8ae074d34843c828502a80e0719b778e6a8686a04fc976bc2\",\"cloud-mainchip-route12-drt-runtime/input/native-image.tar\":\"c8448ddce6e02b2f23ddd84245a71ae43c2b4b8537c5e1bdaf80fc4ef8882f9d\",\"cloud-mainchip-route12-drt-runtime/input/runtime-inventory.json\":\"f0dd493a1f5106da8a86bf0de6821d6ddbeed25050717c5706225c3d4fdfdbfa\",\"cloud-mainchip-route12-drt-runtime/global/fixed-clock.json\":\"a72f0e7f03405f5c61961b14b721c822f25df143ce67546cf3e93c7db4b210e5\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/fresh_fanout_native.tcl\":\"dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/fresh-fanout-global.odb\":\"2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/fresh-fanout.guide\":\"54ae78b49f70b05e007edc151c67c64a7eed4fd9a9ce0aed6d7898bb3286dcde\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/_env.tcl\":\"255d39b6b296466fae51428718fd9fdd5019594fdf6d1c2cbdd116ac52e8c8f0\",\"cloud-mainchip-route12-drt-runtime/global/run/1-nssoc-repairfreshglobal/config.json\":\"c6dfea371e243881a4ae20499da8726980c83224ea31e1b4e5fe7bb44cbccaaa\",\"cloud-mainchip-route12-drt-runtime/global/candidate-state.json\":\"647d7347c0676ac2d08112164b6917b5c45185067c2deef808e404f7434518ba\",\"cloud-mainchip-route12-drt-runtime/global/geometry/result.json\":\"3f0141703d3531e11a2f7e7c1fc7d66a1fdc133723f473005aeeede216b84083\",\"cloud-mainchip-route12-drt-runtime/global/trial-config.json\":\"b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f\",\"cloud-mainchip-route12-drt-runtime/global/result.json\":\"0c7f6a86849d32ae853726ab448da0e4c2f71373956220c95c434657247e9d60\",\"cloud-mainchip-route12-drt-runtime/flow-config/trial-config.json\":\"b86cade4259c9e0a650c0950882b6a9e08d15e3ebade31d31a001b507279832f\",\"cloud-mainchip-route12-drt-runtime/work/route.tcl\":\"11457b60c2c81c6c64ab44272a14394190255548fe31394497990ffa4e8d0085\",\"cloud-mainchip-route12-drt-runtime/work/before-guide-read.odb\":\"2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a\"}")
ORIGINAL_REQUIRED=copy.deepcopy(REQUIRED_INPUTS)
STAGED=None
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert file_sha(ROOT/p)==h,p
    assert m['latest_capsule_run']==latest.RUN and m['latest_capsule_source']==latest.HEAD
    assert m['normal_continuation_accepted']is False and m['route_segment_s']==600
    return m
def activate_required_inputs():
    m=methods()
    for p,h in m['protected'].items():
        if p in REQUIRED_INPUTS:assert REQUIRED_INPUTS[p]==h
        REQUIRED_INPUTS[p]=h
    return m
def rejected_receipt():
    global STAGED
    assert STAGED is None
    m=activate_required_inputs()
    assert m['native_process_restore_authorized']is True and m['native_attachment_authorized']is True
    import compare_cloud_routed_endpoints as reports
    old_out=reports.OUT
    target=old_out/'latest-admitted-files'
    try:proof=latest.restore_files_only(target)
    finally:reports.OUT=old_out
    outer=latest.source_report((latest.BASIS/'mainchip-observed-native-result.json').read_bytes())
    inner=proof['inner_report']
    assert 'sources_unchanged'not in inner and 'active_drt_cross_runner_progress_proven'not in inner
    STAGED=dict(path=target,proof=proof,outer=outer,inner=copy.deepcopy(inner))
    return dict(group=latest.GROUP,run=latest.RUN,summary_sha256=latest.SUMMARY,
        parts_sha256=latest.PARTS,source_head=latest.HEAD,report=inner,
        exact_inner_sha256=latest.INNER,normal_continuation_accepted=False)
def restore_failed_capsule(pin,target,old_names):
    global STAGED
    assert STAGED is not None
    assert pin['run']==latest.RUN and pin['source_head']==latest.HEAD
    assert pin['summary_sha256']==latest.SUMMARY and pin['parts_sha256']==latest.PARTS
    assert pin['exact_inner_sha256']==latest.INNER and pin['report']==STAGED['inner']
    expected=sorted(n for n in STAGED['outer']['outputs']if n.startswith(('work/','checkpoints/')))
    assert sorted(old_names)==expected and len(expected)==36
    target=Path(target);assert not target.exists()and target.parent==STAGED['path'].parent
    admitted=latest.validate_restored(STAGED['outer'],STAGED['path'])
    assert admitted['inner_report']==pin['report']
    STAGED['path'].rename(target)
    second=latest.validate_restored(STAGED['outer'],target);assert second['inner_report']==pin['report']
    proof=dict(latest_file_admission=STAGED['proof'],revalidated_after_same_parent_rename=True,
        latest_run=latest.RUN,latest_inner_sha256=latest.INNER,old400958_admission_unchanged=True,
        normal_continuation_accepted=False,native_process_restored=False)
    STAGED=None
    return second['inner_report'],proof
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
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    activate_required_inputs()
    return validate_current_rows(callback(),phase,previous)
