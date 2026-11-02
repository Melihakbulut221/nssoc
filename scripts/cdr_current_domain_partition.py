#!/usr/bin/env python3
"""Partition actual current-parent MOS into explicit model-range units; no resistor tuning."""
import argparse,copy,hashlib,json,os,subprocess
from pathlib import Path
from decimal import Decimal
import mos_model_domain_audit as prior
ROOT=Path(__file__).resolve().parents[1]
MAP='docs/evidence/cdr-current-domain-parent-map.json'
METHOD='scripts/cdr-current-domain-partition-methods.json'
FLAGS=dict(full_phy_accepted=False,physical_acceptance=False,final_timing_complete=False,
           matching_layout_verified=False,fresh_RC_for_modified_devices=False)
need=prior.require
def enc(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def join_current(contract,mapping):
    records=contract['device_records'];pairs=mapping['pairs']
    need(len(records)==len(pairs)==500,'Complete original500 mapping')
    expected={p['layout']['id']:p for p in pairs}
    need(len(expected)==500 and all(p['status']=='Match'for p in pairs),'All500 actual matched identities')
    need({r['native_id']for r in records}==set(expected)and len({r['instance']for r in records})==500,'Unique exact original identities')
    joined=[]
    for r in records:
        p=expected[r['native_id']]
        need(r['instance']==p['loaded_instance']and r['model']==p['layout']['model']==p['schematic']['model'],'Exact actual primitive identity')
        need(r['parameters']==p['loaded_parameters'],'Exact actual original parameters')
        rt={t['terminal']:t for t in r['terminals']};pt=p['layout']['terminals']
        need(len(rt)==len(r['terminals'])and set(rt)==set(pt),'Complete unique native terminals')
        for k,t in rt.items():
            need(t['native_cluster']==pt[k]['cluster']and t['native_net']==pt[k]['name'],'Exact current native terminal owner')
        if r['model']=='sg13_lv_nmos':
            need([t['terminal']for t in r['terminals']]==['D','G','S','B'],'MOS ordered terminals')
            need(r['parameters']['ng']==r['parameters']['m']=='1','Actual parent single-finger MOS')
            joined.append(dict(native_id=r['native_id'],simulation=r))
    need(len(joined)==50,'All50 original MOS')
    need(sum(r['model']=='rppd'for r in records)==98,'All98 original resistors')
    return joined
def derive(text,contract,mapping):
    joined=join_current(contract,mapping)
    plan=prior.make_plan(joined)
    need(sum(len(p['units'])for p in plan)==200,'Exact current50-to200 partition')
    candidate,expanded,deltas=prior.rewrite_parallel(text,contract,plan,joined)
    updated=copy.deepcopy(contract);updated['counts']['devices']=650;updated['device_records']=[]
    for item in expanded:
        r=copy.deepcopy(item['device'])
        if item['candidate_instance']!=item['device'].get('instance'):
            raise ValueError('Explicit expanded instance identity')
        if item['source_native_id']in {p['native_id']for p in plan}:
            r['native_id']=item['candidate_instance'];r['source_native_id']=item['source_native_id']
        updated['device_records'].append(r)
    need(len(updated['device_records'])==len({r['native_id']for r in updated['device_records']})==650,'All650 unique proposed devices')
    old_other=[r for r in contract['device_records']if r['model']!='sg13_lv_nmos']
    new_other=[r for r in updated['device_records']if r['model']!='sg13_lv_nmos']
    need(old_other==new_other and len(old_other)==450,'Every450 original non-MOS record unchanged')
    need({k:v for k,v in updated['counts'].items()if k!='devices'}=={k:v for k,v in contract['counts'].items()if k!='devices'},'Original wire RC counts unchanged')
    widths=[str(prior.scalar(u['parameters']['w'])/Decimal('1e-6'))for p in plan for u in p['units']]
    summary=dict(status='PROPOSED_CURRENT_PARENT_50_TO200_MOS_ONLY_NOT_NATIVE_ACCEPTANCE',
      original_devices=500,candidate_devices=650,original_mos=50,candidate_mos=200,
      actual_parent_wide_mos=sum(prior.scalar(j['simulation']['parameters']['w'])>Decimal('10e-6')for j in joined),
      unit_width_min_um=str(min(map(Decimal,widths))),unit_width_max_um=str(max(map(Decimal,widths))),
      original_model_sha256=digest(text.encode()),candidate_model_sha256=digest(candidate.encode()),
      original_contract_sha256=digest(enc(contract)),candidate_contract_sha256=digest(enc(updated)),
      all450_other_devices_unchanged=True,all98_resistors_unchanged=True,all_parent_wire_RC_unchanged=True,
      original_model_exact_reversal=True,new_junction_perimeters_explicit=True,**FLAGS)
    return dict(baseline_text=text,baseline_contract=contract,text=candidate,contract=updated,
                plan=plan,joined=joined,deltas=deltas,summary=summary)
def fixture(mapping):
    records=[]
    for p in mapping['pairs']:
        names=['D','G','S','B']if p['layout']['model']=='sg13_lv_nmos'else sorted(p['layout']['terminals'])
        terms=[dict(terminal=k,node='n'+str(p['layout']['terminals'][k]['cluster']),
                    native_cluster=p['layout']['terminals'][k]['cluster'],
                    native_net=p['layout']['terminals'][k]['name'])for k in names]
        records.append(dict(native_id=p['layout']['id'],instance=p['loaded_instance'],
                            model=p['layout']['model'],parameters=copy.deepcopy(p['loaded_parameters']),terminals=terms))
    comp=dict(device_records=records,counts=dict(devices=500,R=1,C=1),interface=['synthetic_only'])
    text='* SYNTHETIC full500 renderer control; not a physical netlist\n'
    text+='\n'.join(' '.join([r['instance'],*[t['node']for t in r['terminals']],r['model'],
                              *[k+'='+v for k,v in sorted(r['parameters'].items())]])for r in records)
    return text+'\nR_SENTINEL n1 n2 7\nC_SENTINEL n2 n3 3f\n.end\n',comp
def controls():
    e=os.environ
    need(e.get('GITHUB_ACTIONS')=='true'and e.get('RUNNER_ENVIRONMENT')=='github-hosted','Hosted source controls')
    need(e['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'and e['GITHUB_REF']=='refs/heads/codex/cdr-current-domain-partition','Exact branch')
    need(e['GITHUB_EVENT_NAME']=='workflow_dispatch'and e['GITHUB_RUN_ATTEMPT']=='1','First manual run')
    need(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==e['GITHUB_SHA'],'Actual source checkout')
    method=json.loads((ROOT/METHOD).read_bytes())
    for p,want in method['files'].items():
        b=(ROOT/p).read_bytes();need(dict(bytes=len(b),sha256=digest(b))==want,'Protected source '+p)
    mapping=json.loads((ROOT/MAP).read_bytes())
    text,contract=fixture(mapping);state=derive(text,contract,mapping)
    need('R_SENTINEL n1 n2 7\nC_SENTINEL n2 n3 3f\n.end\n'in state['text'],'All unrelated synthetic RC sentinel bytes')
    need(state['summary']['actual_parent_wide_mos']==42,'Actual current model-domain census')
    renderer=prior.renderer_controls(contract,state['plan'],state['joined'])
    rejected=[]
    def reject(label,call):
        try:call()
        except (ValueError,KeyError,AssertionError):rejected.append(label)
        else:raise ValueError('Accepted '+label)
    selected=next(i for i,r in enumerate(contract['device_records'])if r['model']=='sg13_lv_nmos')
    for label in ('missing-record','duplicate-record','changed-model','changed-width','changed-ng','changed-owner','changed-native-net','duplicate-terminal','changed-instance'):
        bad=copy.deepcopy(contract)
        r=bad['device_records'][selected]
        if label=='missing-record':bad['device_records'].pop()
        elif label=='duplicate-record':bad['device_records'][-1]=copy.deepcopy(r)
        elif label=='changed-model':r['model']='wrong'
        elif label=='changed-width':r['parameters']['w']='48u'
        elif label=='changed-ng':r['parameters']['ng']='4'
        elif label=='changed-owner':r['terminals'][0]['native_cluster']+=10000
        elif label=='changed-native-net':r['terminals'][0]['native_net']='wrong'
        elif label=='duplicate-terminal':r['terminals'][1]=copy.deepcopy(r['terminals'][0])
        else:r['instance']='XD9999'
        reject(label,lambda:join_current(bad,mapping))
    for label in ('missing-origin','out-of-range-unit','changed-unit-length','changed-unit-terminal','stale-junction-perimeter','metadata-fingers','duplicate-unit'):
        plan=copy.deepcopy(state['plan']);u=plan[0]['units'][0]
        if label=='missing-origin':plan.pop()
        elif label=='out-of-range-unit':u['parameters']['w']='54u'
        elif label=='changed-unit-length':u['parameters']['l']='0.5u'
        elif label=='changed-unit-terminal':u['terminals'][0]['node']='wrong'
        elif label=='stale-junction-perimeter':u['parameters']['pd']='999u'
        elif label=='metadata-fingers':u['parameters']['ng']='4'
        else:plan[1]['units'][0]['instance']=u['instance']
        reject(label,lambda:prior.validate_plan(plan,state['joined']))
    # Preserve total W and all junction formulae: this can only be refused
    # by the per-unit model-domain predicate, not the width-sum safeguard.
    balanced=copy.deepcopy(state['plan'])
    target=next(p for p in balanced if p['original_parameters']['w']=='36u')
    need(len(target['units'])==4 and all(prior.scalar(u['parameters']['w'])==Decimal('9e-6')for u in target['units']),'Exact balanced-domain fixture')
    for unit,width in zip(target['units'][:2],(Decimal('11'),Decimal('7'))):
        q=unit['parameters'];q.update(w=str(width)+'u',ad=str(width*Decimal('.34'))+'p',
          **{'as':str(width*Decimal('.34'))+'p'},pd=str(2*(width+Decimal('.34')))+'u',ps=str(2*(width+Decimal('.34')))+'u')
    need(sum(prior.scalar(u['parameters']['w'])for u in target['units'])==Decimal('36e-6'),'Balanced corrupted width sum remains36um')
    try:prior.validate_plan(balanced,state['joined'])
    except ValueError as error:
        need(str(error)=='unit width model domain','Domain fault must reach the exact domain predicate')
        rejected.append('balanced-out-of-domain-unit-with-valid-total-width-and-junctions')
    else:raise ValueError('Accepted balanced out-of-domain primitive')
    need(len(rejected)==17 and len(renderer['refused'])==7,'All24 source fault cases')
    # All inherited helper input/source objects remain immutable.
    need((ROOT/MAP).read_bytes()==enc(mapping),'Exact canonical input mapping bytes')
    return dict(status='PASS_CURRENT_MOS_ONLY_PARTITION_SOURCE_CONTROLS',source=e['GITHUB_SHA'],
        run=int(e['GITHUB_RUN_ID']),synthetic_fixture_only=True,native_acquired=False,
        actual_native_binding_executed=False,transient_executed=False,source_faults=rejected,
        renderer_controls=renderer,proposal=state['summary'],plan=state['plan'],**FLAGS)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--controls',action='store_true',required=True)
    parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    result=controls();a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'result.json').write_bytes(enc(result))
    print(json.dumps(dict(status=result['status'],source_faults=24,original_mos=50,proposed_units=200,native_executed=False)))
if __name__=='__main__':main()
