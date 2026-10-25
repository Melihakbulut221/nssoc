#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_small_v24_mim_sources import check as prior
    from check_cdr_input_access_v26_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-input-access-v26-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-mim-parent-capture-pass-20261021.json').read_text())
    assert pin['run']==39532836299 and pin['source_head']=='aa9069fe2dff75eea63a2a845851ef2367cb9f12'
    assert pin['summary_sha256']=='dc8d837daa706d973287704cea244e09eea21fbf71a4a54a3625964951f66149'
    assert pin['parts_sha256']=='ca6a7b33578a5df0da45bd7f27b74962aba3111e872811494a784df3451a6075'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert got['R']==17674 and got['C']==12694 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-input-access-v26-'+stage+'-pass-20261021.json')).read_text())
        assert b['run']==39532277767 and b['source_head']=='9453973642ebd7a330a7f07e9bafd98924b59d89'
        assert all(b[k]==p[k] for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-binding-pass-20261021.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    producer=runpy.run_path(str(ROOT/'scripts/cloud_cdr_input_access_v26_mim_stage.py'),run_name='handoff_preflight')
    generated=producer['receipt_path']('mim-parent-audit')
    consumer=ROOT/'scripts/cloud_cdr_input_access_v26_mim_composition.py'
    literals={n.value for n in ast.walk(ast.parse(consumer.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
    assert str(generated.relative_to(ROOT))in literals
    assert generated==ROOT/'docs/evidence/cdr-input-access-v26-mim-parent-audit-pass-20261021.json'
    print('PASS_V26_EXACT_FRESH17674R12694C_SEVEN_MIM_AND_PRODUCER_CONSUMER_HANDOFF')
if __name__=='__main__':check()
