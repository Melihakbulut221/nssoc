#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind actual deep setup paths to routed net names before architectural repair."""
import json,os,re,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-nine-size-setup-map'
ODB_SHA='72c2e2cd51be4f075b551b48ccd23a57bebf41d978a94b64f6a1164848662e87'
def data_rows(text):
    assert 'data arrival time'in text
    head=text.split('data arrival time')[0]
    lines=[l for l in head.splitlines()if re.search(r' [\^v] (\S+) \(([^()\n]+)\)\s*$',l)]
    parsed=[]
    for line in lines:
        m=re.search(r' [\^v] (\S+) \(([^()\n]+)\)\s*$',line)
        numbers=line[:m.start()].split();assert len(numbers)>=3
        parsed.append(dict(pin=m[1],master=m[2],slew_ns=float(numbers[-3]),increment_ns=float(numbers[-2]),arrival_ns=float(numbers[-1]),native_line=line))
    clocks=[i for i,r in enumerate(parsed)if r['pin'].endswith(('/CLK','/A_CLK','/B_CLK'))]
    if clocks:
        assert len(clocks)==1
        parsed=parsed[clocks[0]+1:]
    else:
        launch=re.match(r'Startpoint: (\S+) \(input port clocked by [^\n]+\)',text)
        assert launch and parsed[0]['pin']==launch[1]and parsed[0]['master']=='in'
    assert len(parsed)>1 and all(not r['pin'].endswith(('/CLK','/A_CLK','/B_CLK'))for r in parsed)
    return parsed

def native():
    import odb
    p=OUT/'parent/routed.odb';assert sha(p)==ODB_SHA
    db=odb.dbDatabase.create();odb.read_db(db,str(p));block=db.getChip().getBlock();assert len(block.getInsts())==114025 and len(block.getNets())==114097
    paths=json.loads((OUT/'path-requests.json').read_text());named={}
    def describe(t):return dict(instance=t.getInst().getName(),pin=t.getMTerm().getName(),master=t.getInst().getMaster().getName(),direction=str(t.getIoType()))
    for path in paths:
        for row in path['data_rows']:
            name=row['pin']
            if name in named:continue
            if '/'in name:
                instance,pin=name.rsplit('/',1);inst=block.findInst(instance);assert inst,('Missing native timing instance',instance)
                term=inst.findITerm(pin);assert term,('Missing exact native timing pin',name)
                assert inst.getMaster().getName()==row['master'];net=term.getNet();assert net
                entry=dict(kind='iterm',master=inst.getMaster().getName(),direction=str(term.getIoType()),location_dbu=list(inst.getLocation()))
            else:
                term=block.findBTerm(name);assert term,('Missing exact boundary pin',name)
                direction=str(term.getIoType());expected={'INPUT':'in','OUTPUT':'out','INOUT':'inout'}
                assert direction in expected and row['master']==expected[direction],(name,direction,row['master'])
                net=term.getNet();assert net;entry=dict(kind='bterm',direction=direction)
            entry.update(net=net.getName(),signal_type=str(net.getSigType()),connections=[describe(t)for t in net.getITerms()],boundary_terms=[t.getName()for t in net.getBTerms()]);named[name]=entry
    inventory={}
    for prefix in ['u_ibex.','u_bus.','g_core_req_reg.','u_bus.g_req_reg.','g_core_req_direct.']:
        inventory[prefix]=dict(instance_names=[i.getName()for i in block.getInsts()if i.getName().startswith(prefix)][:100],matching_instance_count=sum(i.getName().startswith(prefix)for i in block.getInsts()),net_names=[n.getName()for n in block.getNets()if n.getName().startswith(prefix)][:100],matching_net_count=sum(n.getName().startswith(prefix)for n in block.getNets()))
    assert sha(p)==ODB_SHA
    (OUT/'native-map.json').write_text(json.dumps(dict(pin_map=named,naming_inventory=inventory,odb_sha256=ODB_SHA,scope='Exact retained ODB names, no guessed RTL equivalence. Missing hierarchical names do not by themselves prove a parameter value.'),indent=2)+'\n')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,physical_candidate_modified=False,scope='Read-only exact nine-size routed ODB and already reproduced native setup paths. Recover routed signal names, gate count, large incremental stages, fanout and retained pipeline naming before selecting architecture/logic repair. No new STA, timing waiver or physical acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        trace,tp=reports.restore_report('nine-size-paths',38953044374,'5b5776d2f96e7d371a9d282ca372597b133681adc241958467be1b4447665376','ab63a373e201312bf0bdfc87f06ce0f6c8dceb404b50dee7ad788822ab162afd',OUT/'trace',('selected-paths.log',))
        assert trace['source_unchanged']and trace['all_endpoint_comparison_reproduced']
        parent,pp=reports.restore_report('route234-sized-eco',38930352215,'e3ff94103fe3d99e1dcdf889c1d01d741d6fd6d0a29092b20aea488dab89bbd4','fffba7e3f8b72286b19a9c9faec5d78eb155a8884ddccbb3c2bd5fd9240f13ae',OUT/'parent',('routed.odb',))
        assert parent['source_unchanged']and sha(OUT/'parent/routed.odb')==ODB_SHA
        chunks=re.split(r'(?m)^NSSOC_TARGET_(\d+_(?:slow|typical|fast)_(?:min|max)_(?:rise|fall))\n',trace['native_paths']);blocks=dict(zip(chunks[1::2],chunks[2::2],strict=True));paths=[]
        for c in ('slow','typical','fast'):
            for name in trace['ranked_setup'][c]:
                i=next(i for i,t in enumerate(trace['targets'])if t['endpoint']==name)
                for edge in ('rise','fall'):
                    key=f'{i}_{c}_max_{edge}';rows=data_rows(blocks[key]);assert rows[-1]['pin']==name
                    paths.append(dict(marker=key,endpoint=name,corner=c,edge=edge,slack_seconds=trace['targets'][i]['transition_slacks'][c+'_max'][['rise','fall'].index(edge)],data_rows=rows,data_cell_count=sum(r['master']not in ('in','out','inout')for r in rows),startpoint=blocks[key].splitlines()[0]))
        assert len(paths)==60;(OUT/'path-requests.json').write_text(json.dumps(paths,indent=2)+'\n');r.update(trace=tp,parent=pp,path_count=60);save()
        env=dict(os.environ,NSSOC_SETUP_MAP_NATIVE='1')
        with (OUT/'native-map.log').open('w')as f:code=subprocess.call([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(Path(__file__).resolve())],env=env,stdout=f,stderr=subprocess.STDOUT)
        text=(OUT/'native-map.log').read_text();assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(code,text[-4000:])
        mapping=json.loads((OUT/'native-map.json').read_text());r.update(native=mapping,paths=paths)
        assert all(sha(OUT/'parent'/p)==v['sha256']for p,v in pp['restore']['selected_files'].items())
        r.update(status='COMPLETE_EXACT_ROUTED_SETUP_PATH_TO_NET_MAP_NOT_REPAIR_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    if os.environ.get('NSSOC_SETUP_MAP_NATIVE')=='1':native()
    else:main()
