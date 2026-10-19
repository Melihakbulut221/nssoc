#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Trace unchanged sampler emitter/clock/tail networks through real native terminal evidence."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-folded-v11-stage-comparison'
def unique_group(groups,device,terminal):
    found=[g for g in groups if any(t['device'].lower()==device.lower()and t['terminal']==terminal for t in g['terminals'])]
    assert len(found)==1,('Missing or ambiguous actual terminal group',device,terminal,len(found))
    return found[0]
def key(g):return g['native_cluster'],g['native_net']
def brief(g):
    return {k:g[k]for k in ('native_cluster','native_net','logical_net','R_count','C_incident_count','sum_wire_R_ohm','incident_wire_C_f','internal_wire_C_f','cref_wire_C_f','terminals')}|dict(largest_shortest_resistor_paths=g.get('largest_shortest_resistor_paths',[]))
def controls():
    g=dict(terminals=[dict(device='XD1',terminal='E')])
    assert unique_group([g],'xd1','E')is g
    rejected=[]
    for label,gs in [('missing',[]),('duplicate',[g,g]),('wrong_terminal',[dict(terminals=[dict(device='XD1',terminal='B')])])]:
        try:unique_group(gs,'xd1','E')
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    return dict(case_insensitive_native_device=True,rejected=rejected)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,closed_loop=False,scope='Read-only comparison of native stage connectivity, wire R/C and original terminal voltage observations. No new waveform, physical edit, inferred effective RC delay, clock/phase fitting or changed electrical gate.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=controls()
        pins=json.loads((ROOT/'docs/evidence/cdr-folded-v11-stage-comparison-input-20261019.json').read_text())
        r['sources']={};observed={};preserved={}
        names=['wire-network-review.json','fixed-sampling-review.json','terminal-voltage-review.json']
        for label,pin in pins.items():
            dst=OUT/label
            source,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],dst,names)
            assert source==pin['report']and source['sources_unchanged']and source['accepted']is False
            r['sources'][label]=proof
            wire=json.loads((dst/names[0]).read_text());sampling=json.loads((dst/names[1]).read_text())['samples'];volt=json.loads((dst/names[2]).read_text())
            groups=wire['conductors'];assert len(groups)==111
            assert len({key(g)for g in groups})==111
            assert wire['native_counts']==dict(R=15482,C=11590 if label.startswith('folded') else 11527)
            stages={}
            for tag,s in sampling.items():
                assert tag in 'abcd';stages[tag]={}
                for stage in ('master','slave'):
                    devices=s[stage+'_input_devices'];assert len(devices)==2
                    de=unique_group(groups,devices[0],'E')
                    assert key(unique_group(groups,devices[1],'E'))==key(de)
                    selectors=[t for t in de['terminals']if t['model']=='npn13g2'and t['terminal']=='C']
                    assert selectors and len({t['device'].lower()for t in selectors})==len(selectors)
                    tail=unique_group(groups,selectors[0]['device'],'E')
                    assert all(key(unique_group(groups,t['device'],'E'))==key(tail)for t in selectors)
                    mos=[t for t in tail['terminals']if t['model']=='sg13_lv_nmos'and t['terminal']=='D'];assert mos
                    rails={t['device']:dict(drain_voltage=volt[t['device'].lower()+':D']['voltage'],source_voltage=volt[t['device'].lower()+':S']['voltage'])for t in mos}
                    clock_bases=[unique_group(groups,t['device'],'B')for t in selectors]
                    assert all(g['logical_net']in ('cp','cn')for g in clock_bases)
                    for d in devices:assert d.lower()+':E'in volt
                    stages[tag][stage]=dict(input_devices=devices,input_emitter_network=brief(de),selector_devices=[t['device']for t in selectors],selector_base_networks=[brief(g)for g in {key(g):g for g in clock_bases}.values()],clock_tail_network=brief(tail),native_mos_tails=rails,input_emitter_voltages={d:volt[d.lower()+':E']['voltage']for d in devices})
            observed[label]=dict(stages=stages,original_fixed_sampling=source['fixed_sampling_phase_review'],original_failed_hbt=source['failed_hbt_terminal_review'])
            for n in names:assert sha(dst/n)==source['outputs'][n];preserved[str(dst/n)]=source['outputs'][n]
            save()
        differences={}
        for case in ('early','late'):
            old=observed['original_'+case];new=observed['folded_'+case];changes={}
            for tag in 'abcd':
                changes[tag]={}
                for stage in ('master','slave'):
                    a=old['stages'][tag][stage];b=new['stages'][tag][stage]
                    assert len(a['selector_devices'])==len(b['selector_devices'])
                    assert len(a['native_mos_tails'])==len(b['native_mos_tails'])
                    values={}
                    for net in ('input_emitter_network','clock_tail_network'):
                        values[net]={k:dict(before=a[net][k],after=b[net][k],delta=b[net][k]-a[net][k])for k in ('sum_wire_R_ohm','incident_wire_C_f','cref_wire_C_f')}
                    changes[tag][stage]=values
            differences[case]=changes
        assert all(sha(p)==v for p,v in preserved.items())
        r.update(status='COMPLETE_NATIVE_SAMPLER_STAGE_NETWORK_COMPARISON_NOT_ACCEPTANCE',native_stages=observed,differences=differences,sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_NATIVE_STAGE_COMPARISON',error=repr(e));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
