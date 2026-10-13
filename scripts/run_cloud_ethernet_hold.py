#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Paired full-chip GMII hold ECO screening with real native identity delays."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from read_opensta_phase_slacks import parse_phases

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-ethernet-hold'
URL='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/newer-postcts-cloud-38317996877-1.tar.gz'
SHA='f8270a24dbd199e1ab9c3fc33ab670ceb81629c1d7220f0f2f4642b6828b318c'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def execute(command,label,env=None,success=True):
    path=OUT/(label+'.log')
    with path.open('w') as stream:
        code=subprocess.call([str(x) for x in command],env=env,stdout=stream,stderr=subprocess.STDOUT)
    text=path.read_text(errors='replace')
    if success and (code or re.search(r'(?m)^(Error:|\[ERROR)',text)):
        raise RuntimeError((label,code,text[-8000:]))
    return code,text


def tcl(text,label):
    path=OUT/(label+'.tcl');path.write_text(text)
    return execute([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',path],label)[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--depth',type=int,choices=[1,2],required=True)
    args=parser.parse_args();OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',depth=args.depth,adopted=False,scope='Ten GMII output-port identity delay chains only. All original instances and power geometry unchanged. Same3corner all-clock STA and real Liberty logic proof. Placement estimates only; new routing/PEX/DRC/LVS required before adoption; CPU/PCIe hold and setup/fullPHY remain open.')
    try:
        packed=OUT/'source.tar.gz'
        subprocess.run(['curl','--fail','--location','--retry','4',URL,'-o',str(packed)],check=True)
        assert sha(packed)==SHA
        with tarfile.open(packed) as archive:archive.extractall(OUT/'source',filter='data')
        packed.unlink();source=OUT/'source/cloud-newer-postcts'
        old=json.loads((source/'result.json').read_text());script_path=source/'reproduced-postcts.tcl'
        assert sha(script_path)==old['failure_outputs']['reproduced-postcts.tcl']
        script=script_path.read_text()
        odb_paths=[p for p in old['source_inputs'] if p.endswith('/inputs/postcts.odb')]
        assert len(odb_paths)==1 and odb_paths[0] in script
        prefix=odb_paths[0].removesuffix('/inputs/postcts.odb')
        script=script.replace(prefix,str(source))
        for path,digest in old['source_inputs'].items():
            assert path.startswith(prefix+'/') and sha(source/path[len(prefix)+1:])==digest
        original=parse_phases((source/'reproduced-postcts.log').read_text(),'CORNER')
        baseline=tcl(script+f'\nwrite_verilog {{{OUT/"baseline.v"}}}\n','baseline')
        result['baseline']=parse_phases(baseline,'CORNER')
        assert result['baseline']==original
        env=dict(os.environ,NSSOC_HOLD_DEPTH=str(args.depth),NSSOC_HOLD_MODE='prepare')
        helper=ROOT/'scripts/prepare_cloud_ethernet_hold.py'
        execute([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',helper],'prepare',env)
        tcl(f'read_db {{{OUT/"proposed.odb"}}}\nset_thread_count 2\ndetailed_placement -max_displacement {{30 15}}\ncheck_placement -verbose\nwrite_db {{{OUT/"placed.odb"}}}\n','legalize')
        execute([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',helper],'audit',dict(env,NSSOC_HOLD_MODE='audit'))
        result['geometry']=json.loads((OUT/'geometry-audit.json').read_text())
        candidate=script.replace(str(source/'inputs/postcts.odb'),str(OUT/'candidate.odb'))
        result['candidate']=parse_phases(tcl(candidate+f'\nwrite_verilog {{{OUT/"candidate.v"}}}\n','candidate'),'CORNER')
        assert result['candidate'].keys()==result['baseline'].keys()
        libs=[p for p in source.rglob('*.lib') if '_typ_' in p.name]
        standard=next(p for p in libs if 'stdcell' in p.name)
        command=[os.environ['CLOUD_APPIMAGE'],'python3',ROOT/'hw/soc/flow/check_eco_logic.py',OUT/'baseline.v',OUT/'candidate.v','--liberty',standard,'--output',OUT/'logic']
        for lib in libs:
            if lib!=standard:command+=['--macro-liberty',lib]
        execute(command,'logic')
        result['logic']=json.loads((OUT/'logic/result.json').read_text());assert result['logic']['status']=='PASS within scope'
        bad=(OUT/'candidate.v').read_text();pattern=r'sg13g2_dlygate4sd3_1\s+nssoc_eth_hold_0_0\s*\([^;]+;'
        match=re.search(pattern,bad);assert match
        inverted=re.sub(r'\.X\s*\(','.Y(',match[0].replace('sg13g2_dlygate4sd3_1','sg13g2_inv_1'))
        (OUT/'inverted.v').write_text(bad[:match.start()]+inverted+bad[match.end():])
        negative=[str(x) for x in command];negative[negative.index(str(OUT/'candidate.v'))]=str(OUT/'inverted.v');negative[negative.index(str(OUT/'logic'))]=str(OUT/'logic-negative')
        code,log=execute(negative,'logic-negative',success=False)
        assert code!=0 and 'Non-buffer instance added or removed' in log
        result['inversion_control']='EXPECTED_FUNCTIONAL_CHANGE_REJECTED'
        result['all_group_nonregressing_estimate']=all(result['candidate'][c]['groups'][g]['worst_slack_ns']>=r['worst_slack_ns']-1e-6 for c,row in result['baseline'].items() for g,r in row['groups'].items())
        result['no_new_violation_or_worsened_existing_negative_group']=all(
            result['candidate'][c]['groups'][g]['worst_slack_ns'] >= (0 if r['worst_slack_ns']>=0 else r['worst_slack_ns']-1e-6)
            for c,row in result['baseline'].items() for g,r in row['groups'].items())
        result['all_corner_gmii_output_hold_nonnegative']=all(
            result['candidate'][c+'_min']['groups']['eth_gtx']['worst_slack_ns']>=0
            for c in ('slow','typical','fast'))
        result['status']='COMPLETE_NATIVE_GMII_HOLD_ECO_ESTIMATE_NOT_SIGNOFF'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
