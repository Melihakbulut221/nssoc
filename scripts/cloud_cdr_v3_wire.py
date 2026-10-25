#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Original XOR data/device gates on the actual native54 full-wire physical model."""
import argparse,hashlib,importlib.util,json,os,shutil
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'
GENERATED_SHA='d30ebc0bcb4ded90050b9f07e78a4a69eb0bcc60e9ed0ccbd584237aa046860a'
ADAPTATIONS=[{'before': "assert public==['sub','ap','an','bp','bn','iref','sp','sn','on','op','avss','avdd']", 'after': "assert len(public)==11 and set(public)=={'dp','dn','ep','en','qp','qn','avdd','avss','sub','iref','wire_cref'}", 'count': 1}, {'before': "mapping=dict(zip(public,['0','dp','dn','dn','dp','iref','ep','en',*output,'0','avdd']))", 'after': "mapping=dict(dp='dp',dn='dn',ep='ep',en='en',qp=output[0],qn=output[1],avdd='avdd',avss='0',sub='0',iref='iref',wire_cref='0')", 'count': 1}, {'before': "'xgate.xcore.'", 'after': "'xgate.'", 'count': 2}, {'before': 'f\'.include "{COMPONENT}"\',f\'.include "{WRAPPER}"\',', 'after': 'f\'.include "{COMPONENT}"\',', 'count': 1}, {'before': "f'XGATE dp dn ep en {output[0]} {output[1]} avdd 0 0 iref {TOP}'", 'after': "'XGATE '+' '.join(mapping[p] for p in public)+' '+TOP", 'count': 1}, {'before': 'PASS_NATIVE_XOR_PRIMITIVE_ONLY_NOT_CDR_OR_LAYOUT', 'after': 'PASS_NATIVE_FULL_WIRE_XOR_PRIMITIVE_NOT_CDR_OR_PHY', 'count': 1}, {'before': 'REJECTED_NATIVE_XOR_PRIMITIVE', 'after': 'REJECTED_NATIVE_FULL_WIRE_XOR_PRIMITIVE', 'count': 1}, {'before': 'Original54-device mux connected as XOR, external ideal current bias and driven differential inputs through10ohm sources,50fF per output. 256symbols/8GT/s. Schematic primitive only; no physical input level conversion, samplers, recovered clock, complete PVT, noise/jitter/BER, interconnect or chip integration.', 'after': 'Actual54-device XOR parent with4020R/2641C from native physical layout. External ideal current bias and inputs through10ohm sources,50fF per output;256symbols8GT/s. Explicit wire_cref=0; finite27contacts but no substrate spreading/RFqualification, physical common-mode conversion, samplers, recoveredclock, fullPVT/noise/jitter/BER or mainchip integration.', 'count': 1}]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['nominal','hot_low','cold_high','swap_output'],required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    stage=ROOT/('cloud-cdr-v3-wire-source-'+args.case);stage.mkdir(exist_ok=False);reports.OUT=stage
    out=ROOT/('cloud-cdr-v3-wire-'+args.case);generated=None;proof=None;model_validated=False
    try:
        pinpath=ROOT/'docs/evidence/cdr-v3-composition-pass-20261017.json';pin=json.loads(pinpath.read_text())
        prior,proof=reports.restore_report('cdr-v3-composition',pin['run'],pin['summary_sha256'],pin['parts_sha256'],stage/'model',list(pin['outputs']))
        assert prior['status']==pin['status']and prior['sources_unchanged']and prior['composition']['counts']==dict(devices=54,R=4020,C=2641)
        assert prior['native_binding']==pin['native_binding']and prior['controls']==pin['controls']and len(prior['controls']['controls'])==6
        assert all(sha(stage/'model'/n)==h for n,h in pin['outputs'].items())
        model=stage/'model/xor54-wire.spice';assert sha(model)=='4186649aeb8f1cced89bd62b3fba2b7bf1d6e7ee7cccc3b37ad5252d165f71b7'
        rows=[l.lower().split()for l in model.read_text().splitlines()if l and not l.startswith('*')]
        assert rows[0][0]=='.subckt'and rows[0][1]=='nssoc_cdr_xor54_wire_v3'
        assert sum(f[0].startswith('x')for f in rows)==54
        assert sum('npn13g2'in f for f in rows)==19 and sum('ptap1'in f for f in rows)==27
        assert sum(f[0].startswith('r')for f in rows)==4020 and sum(f[0].startswith('c')for f in rows)==2641
        model_validated=True
        base=ROOT/'scripts/cloud_cdr_xor.py';assert sha(base)==BASE_SHA;text=base.read_text()
        for edit in ADAPTATIONS:
            assert text.count(edit['before'])==edit['count'];text=text.replace(edit['before'],edit['after'])
        assert hashlib.sha256(text.encode()).hexdigest()==GENERATED_SHA
        generated=ROOT/'scripts/_cloud_cdr_v3_wire_native.py';assert not generated.exists();generated.write_text(text)
        spec=importlib.util.spec_from_file_location('actual_cdr_wire_native',generated);trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)
        trial.COMPONENT=model;trial.WRAPPER=model;trial.COMPONENT_SHA=sha(model);trial.WRAPPER_SHA=sha(model)
        trial.TOP='nssoc_cdr_xor54_wire_v3';trial.OUTPUT_STEM='cloud-cdr-v3-wire'
        trial.EXTRA_INPUTS=[Path(__file__),base,pinpath,stage/'model/model/binding96/binding01.json',stage/'model/model/wire96/composition-controls98.json']
        trial.main()
        assert all(sha(stage/'model'/n)==h for n,h in pin['outputs'].items())
    finally:
        out.mkdir(parents=True,exist_ok=True);p=out/'result.json'
        result=json.loads(p.read_text())if p.exists()else dict(status='FAIL_MODEL_RESTORE_OR_PREPARATION',accepted=False,full_phy_accepted=False)
        result.update(source_head=os.environ['GITHUB_SHA'],physical_model_source=proof,model_has_native54_devices=model_validated,
            expected_wire_counts=dict(R=4020,C=2641),original_controller_sha256=BASE_SHA,adapted_controller_sha256=GENERATED_SHA,
            native_controller_adaptations=ADAPTATIONS,full_phy_accepted=False,cdr_accepted=False,qualified_pex=False,
            explicit_boundaries='Different2.0/1.3V input commonmodes;10ohm externaldrivers;500uA idealbias;50fF/output;wire_cref tied0;finite27contacts with no substrate spreading or RFqualification. Component test only.')
        shutil.copytree(stage,out/'physical-source')
        if generated is not None:shutil.copyfile(generated,out/'native-controller.py')
        result['outputs']={str(q.relative_to(out)):sha(q)for q in out.rglob('*')if q.is_file()and q!=p}
        p.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
