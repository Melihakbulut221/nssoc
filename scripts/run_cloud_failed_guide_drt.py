#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnose actual full-chip detailed routing of preserved failed global guides.

Never changes or passes the original failed global/NDR gate. Never signoff.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from route_cloud_newer_postcts import sha,fetch,native_ndr_screen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-failed-guide-drt'

def guide_index(text):
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    i=0;result={}
    while i<len(lines):
        name=lines[i];assert name not in ('(',')') and name not in result,'Duplicate/invalid guide net'
        i+=1;assert i<len(lines) and lines[i]=='(';i+=1;count=0
        while i<len(lines) and lines[i]!=')':
            parts=lines[i].split();assert len(parts)==5
            coords=[int(v) for v in parts[:4]]
            assert coords[0]<coords[2] and coords[1]<coords[3]
            assert parts[4] in ('Metal1','Metal2','Metal3','Metal4','Metal5','TopMetal1','TopMetal2')
            count+=1;i+=1
        assert i<len(lines) and count>0,'Incomplete/empty guide block'
        result[name]=count;i+=1
    assert result,'No guides'
    return result

def controls():
    good='net1\n(\n0 0 10 10 Metal2\n)\n'
    assert guide_index(good)=={'net1':1}
    bad=[good+good,good.replace('10 10 Metal2','0 10 Metal2'),good.replace('Metal2','unknown'),good[:-2],'net1\n(\n)\n','']
    for text in bad:
        try:guide_index(text)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('Invalid guide accepted')
    return dict(positive=1,negative=len(bad),accepted=False)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING_DIAGNOSTIC',accepted=False,source_run=38448901835,
        source_head=os.environ['GITHUB_SHA'],original_global_route_passed=False,
        full_serial_phy_complete=False,final_timing_complete=False,
        scope='Full113791-instance packet-interface mainchip DRT diagnostic from exact preserved132-overflow guides. No global-routing gate waiver, placement/netlist/SDC/PDK/NDR change, or final acceptance. Requires independent connectivity, geometric NDR, DRC/LVS, antenna, qualified extraction and original all-corner timing before adoption.')
    def save():
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label,env=None):
        with (OUT/(label+'.log')).open('w') as stream:
            p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env)
            for line in p.stdout:
                stream.write(line);stream.flush();print('['+label+'] '+line,end='',flush=True)
            rc=p.wait()
        text=(OUT/(label+'.log')).read_text(errors='replace')
        assert rc==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,rc,text[-3000:])
        return text
    def tcl(text,label):
        path=OUT/(label+'.tcl');path.write_text(text)
        return run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(path)],label)
    def audit(mode):
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_cloud_failed_guide_drt.py')],
            'audit-'+mode,dict(os.environ,NSSOC_DRT_OUT=str(OUT),NSSOC_DRT_MODE=mode))
        row=json.loads((OUT/('audit-'+mode+'.json')).read_text())
        result['audit_'+mode]={k:v for k,v in row.items() if k not in ('source','measured')}
        result['audit_'+mode]['counts']={k:row['measured'][k] for k in ('instance_count','net_count','guide_rectangles','wired_net_count')}
        result['audit_'+mode]['ndr_net_count']=len(row['measured']['ndr_nets'])
        result['audit_'+mode]['missing_guides_count']=len(row['measured']['multi_terminal_nets_without_guides'])
        save()
    save()
    try:
        result['controls']=controls()
        spec=json.loads((ROOT/'docs/evidence/cloud-seed13-buffers-route-failure-20261014.json').read_text())
        assert spec['run']==38448901835 and spec['native_final_overflow']['total']==132 and not spec['adopted']
        assert spec['status']=='FAILED_NATIVE_GLOBAL_ROUTE_CONGESTION'
        packed=OUT/'source.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        inputs=OUT/'inputs';inputs.mkdir();protected={}
        names=['relocated-placement.odb','failed-global.odb','failed-route.guide','global-route.log','global-route.tcl','congestion.rpt']
        with tarfile.open(packed) as archive:
            for name in names:
                raw=archive.extractfile('cloud-newer-postcts/'+name).read()
                assert hashlib.sha256(raw).hexdigest()==spec['failure_outputs'][name]
                (inputs/name).write_bytes(raw);protected[name]=spec['failure_outputs'][name]
        packed.unlink()
        result['original_failure']=dict(receipt=spec['receipt'],native_final_overflow=spec['native_final_overflow'],
            effective_ndr_screen=native_ndr_screen((inputs/'global-route.log').read_text()),protected_inputs=protected)
        guide=guide_index((inputs/'failed-route.guide').read_text())
        (OUT/'guide-index.json').write_text(json.dumps(guide,indent=2)+'\n')
        result['guide_net_count']=len(guide);result['guide_rectangle_count']=sum(guide.values());save()
        audit('before')
        prefix=f'read_db {{{inputs/"failed-global.odb"}}}\nset_thread_count 2\n'
        tcl(prefix+f'read_guides {{{inputs/"failed-route.guide"}}}\nwrite_db {{{OUT/"guides-loaded.odb"}}}\n','load-guides')
        audit('guides')
        result['status']='NATIVE_INVARIANTS_VERIFIED_DETAILED_ROUTE_RUNNING_DIAGNOSTIC';save()
        text=tcl(f'read_db {{{OUT/"guides-loaded.odb"}}}\nset_thread_count 2\ncheck_placement -verbose\n'
            +f'detailed_route -output_drc {{{OUT/"drc.rpt"}}} -output_guide_coverage {{{OUT/"guide-coverage.csv"}}} -drc_report_iter_step 1 -verbose 1\n'
            +'puts "NSSOC_NATIVE_DRT_DRVS [detailed_route_num_drvs]"\n'
            +f'write_db {{{OUT/"routed.odb"}}}\nwrite_def {{{OUT/"routed.def"}}}\n','detailed-route')
        match=re.findall(r'^NSSOC_NATIVE_DRT_DRVS (\d+)\s*$',text,re.M);assert len(match)==1
        result['native_drt_drvs']=int(match[0]);audit('after')
        assert all(sha(inputs/n)==d for n,d in protected.items())
        result['status']='COMPLETE_NATIVE_DETAILED_ROUTE_DIAGNOSTIC_REQUIRES_INDEPENDENT_SIGNOFF'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'}
        save()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true')
    if p.parse_args().controls_only:print(json.dumps(controls()))
    else:main()
