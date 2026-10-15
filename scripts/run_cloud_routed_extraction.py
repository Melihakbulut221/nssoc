#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual saved route nominal RC extraction and unchanged three-cell-corner STA.

The PDK supplies one nominal ruleset, not qualified RCmin/RCmax signoff.
"""
import hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
from run_cloud_routed_geometry import BASE,STEM,SUMMARY_SHA,ARCHIVE_SHA
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-routed-extraction'
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
RULES_SHA='ffda02d57a6ecb39b02268be9511d89ef072911f17bd2dcd095f3f3cbeb5a905'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_run=38788529905,source_head=os.environ['GITHUB_SHA'],final_timing_complete=False,full_serial_phy_complete=False,
        scope='Exact saved113791-instance route. Fresh native OpenRCX nominal RC; unchanged original physical SDC and slow/typical/fast cell libraries. One shared nominalRC is NOT RCmin/RCmax, foundry qualification, SRAM characterization, SI, fullPHY or production acceptance. Antenna651nets and original global132overflow remain separate.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def execute(text,label):
        script=OUT/(label+'.tcl');script.write_text(text)
        with (OUT/(label+'.log')).open('w') as log:
            p=subprocess.Popen([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(script)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in p.stdout:log.write(line);log.flush();print('['+label+'] '+line,end='',flush=True)
            code=p.wait()
        data=(OUT/(label+'.log')).read_text(errors='replace')
        assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',data),(label,code)
        result[label+'_warnings']=[v for v in data.splitlines() if '[WARNING' in v]
        return data
    save()
    try:
        source=OUT/'source';source.mkdir();fetch(BASE+STEM+'.summary.json',SUMMARY_SHA,source/'route-summary.json');route=json.loads((source/'route-summary.json').read_text())
        assert route['native_drt_drvs']==0 and route['audit_after']['counts']['instance_count']==113791
        packed=OUT/'route.tar.gz';fetch(BASE+STEM+'.tar.gz',ARCHIVE_SHA,packed)
        with tarfile.open(packed) as archive:
            for name in ('routed.odb','routed.def'):
                data=archive.extractfile('cloud-failed-guide-drt/'+name).read();assert hashlib.sha256(data).hexdigest()==route['outputs'][name];(source/name).write_bytes(data)
        packed.unlink()
        inputs=OUT/'inputs';inputs.mkdir();spec=json.loads((ROOT/'docs/evidence/cloud-newer-postcts-input-20261013.json').read_text())
        for group in spec['archives']:
            pin=group['archive'];packed=OUT/pin['name'];fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
            with tarfile.open(packed) as archive:
                for name,row in group['members'].items():
                    assert Path(name).name==name
                    data=archive.extractfile(row['path']).read();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];(inputs/name).write_bytes(data)
            packed.unlink()
        prior=json.loads((inputs/'prior-result.json').read_text());assert prior['status']=='COMPLETE_PLACEMENT_ESTIMATED_NOT_SIGNOFF' and prior['unchanged']
        libspec=json.loads((ROOT/'docs/evidence/cloud-routed-setup-input-20261012.json').read_text());packed=OUT/'libraries.tar.gz';fetch(libspec['archive_url'],libspec['sha256'],packed)
        libs=OUT/'libraries'
        with tarfile.open(packed) as archive:archive.extractall(libs,filter='data')
        packed.unlink();manifest=json.loads((libs/'manifest.json').read_text());assert all(sha(libs/n)==v['sha256'] for n,v in manifest['files'].items())
        replacements={};protected={str(source/'routed.odb'):sha(source/'routed.odb')}
        for old,digest in prior['inputs'].items():
            if old.endswith('.lib'):
                matches=[p for p in libs.rglob(Path(old).name) if sha(p)==digest];assert len(matches)==1;replacements[old]=str(matches[0]);protected[str(matches[0])]=digest
            elif old.endswith('.odb'):
                assert sha(inputs/'postcts.odb')==digest;replacements[old]=str(source/'routed.odb')
            elif old.endswith('.sdc'):
                assert sha(inputs/'physical.sdc')==digest;replacements[old]=str(inputs/'physical.sdc');protected[str(inputs/'physical.sdc')]=digest
        assert len(replacements)==11
        template=(inputs/'prior.tcl').read_text();assert sha(inputs/'prior.tcl')==prior['outputs']['screen.tcl']
        for old,new in replacements.items():assert template.count(old)==1;template=template.replace(old,new)
        prefix=template.split('set_wire_rc -signal')[0]
        assert prefix.count(str(source/'routed.odb'))==1 and prefix.count(str(inputs/'physical.sdc'))==1
        assert all(w not in prefix for w in ('read_spef','estimate_parasitics','extract_parasitics','/home/hasanmelih'))
        rules=source/'IHP_rcx_patterns.rules';fetch(f'https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{PDK}/ihp-sg13g2/libs.tech/librelane/IHP_rcx_patterns.rules',RULES_SHA,rules);protected[str(rules)]=RULES_SHA
        result['protected_inputs']=protected;result['rc_model']=dict(pdk_commit=PDK,sha256=RULES_SHA,nominal_only=True,foundry_qualified=False,method='Same librelane3.0.5 native OpenRCX flags: define_process_corner index0; extract_parasitics -lef_res. Original archived routing database LEF properties retained.');save()
        spef=OUT/'actual-route.nominal.spef'
        execute(f'read_db {{{source/"routed.odb"}}}\nset_thread_count 2\ndefine_process_corner -ext_model_index 0 nominal\nextract_parasitics -ext_model_file {{{rules}}} -lef_res\nwrite_spef {{{spef}}}\nwrite_db {{{OUT/"extracted.odb"}}}\n','nominal-extraction')
        assert spef.stat().st_size>1000
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from audit_estimated_spef import audit
        integrity=audit(spef,allow_coupling=True);result['spef_integrity']=integrity;result['spef_sha256']=sha(spef);save()
        assert integrity['status'].startswith('PASS'), 'SPEF integrity failed; do not consume for STA'
        lines=[prefix,'set_propagated_clock [all_clocks]']
        for corner in ('slow','typical','fast'):lines.append(f'read_spef -corner {corner} {{{spef}}}')
        lines += ['report_parasitic_annotation -report_unannotated']
        for corner in ('slow','typical','fast'):
            for delay in ('max','min'):
                lines += [f'puts CORNER_{corner}_{delay}',f'report_checks -corner {corner} -path_delay {delay} -group_path_count 30 -fields {{slew cap fanout}} -digits 6']
            lines += [f'puts ELECTRICAL_{corner}',f'report_check_types -corner {corner} -max_slew -max_capacitance -max_fanout -violators -digits 6']
        text=execute('\n'.join(lines)+'\n','actual-routed-sta');phases=parse_phases(text,'CORNER')
        assert set(phases)=={c+'_'+d for c in ('slow','typical','fast') for d in ('max','min')}
        result['nominal_rc_cell_corner_phases']=phases
        result['all_reported_group_slacks_nonnegative']=all(v['worst_slack_ns']>=0 for v in phases.values())
        assert all(sha(Path(p))==v for p,v in protected.items());result['protected_inputs_unchanged']=True
        result['status']='COMPLETE_ACTUAL_ROUTED_NOMINAL_RC_THREE_CELL_CORNER_STA_NOT_SIGNOFF'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':main()
