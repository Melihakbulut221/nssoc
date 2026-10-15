#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Complete native setup/hold endpoint census on immutable actual routed RC.

This selects physical hold-repair inputs; no estimated RC or timing acceptance.
"""
import csv,hashlib,io,json,math,os,re,subprocess,sys,tarfile
from pathlib import Path
from audit_cloud_route_annotation import BASE,SUMMARY_SHA,ARCHIVE_SHA
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-routed-endpoints';SOURCE=ROOT/'cloud-routed-extraction'
HELPER_SHA='5514527288fd387ee42d2bfa8dc52b39abe1da16a106e82d4684cb5422bba6e6'
HEADERS=['corner','delay','endpoint','rise_seconds','fall_seconds','worst_seconds']

def number(raw):
    if raw=='UNCONSTRAINED':return None
    value=float(raw);assert math.isfinite(value) and abs(value)<1e20
    return value

def parse_table(text):
    reader=csv.DictReader(io.StringIO(text),delimiter='\t');assert reader.fieldnames==HEADERS
    rows={}
    for row in reader:
        assert None not in row and None not in row.values()
        key=tuple(row[n] for n in ('corner','delay','endpoint'))
        assert all(key) and key[1] in ('min','max') and key not in rows
        values=[number(row[n]) for n in ('rise_seconds','fall_seconds','worst_seconds')]
        finite=[v for v in values[:2] if v is not None]
        assert values[2]==(min(finite) if finite else None)
        rows[key]=values
    assert rows;return rows

def controls():
    header='\t'.join(HEADERS)+'\n';line='fast\tmin\ta/D\t-1e-10\tUNCONSTRAINED\t-1e-10\n'
    assert parse_table(header+line)[('fast','min','a/D')][2]==-1e-10
    faults=[header+line+line,header+line.replace('-1e-10','nan'),header+line.replace('min','bad'),header+line.rsplit('\t',1)[0]+'\t0\n',header+line.rstrip('\n').rsplit('\t',1)[0]+'\n']
    for bad in faults:
        try:parse_table(bad)
        except (AssertionError,ValueError):continue
        raise AssertionError('Malformed endpoint evidence accepted')
    return dict(valid=1,invalid_rejected=len(faults))

def native_topology():
    import odb
    db=odb.dbDatabase.create();odb.read_db(db,str(SOURCE/'source/routed.odb'));block=db.getChip().getBlock()
    rows=json.loads((OUT/'negative-hold-targets.json').read_text());details=[]
    for row in rows:
        name=row['endpoint'];port=block.findBTerm(name)
        if port:term=port;kind='boundary';master=None
        else:
            inst,pin=name.rsplit('/',1);cell=block.findInst(inst);assert cell,name
            term=cell.findITerm(pin);assert term,name
            kind='instance';master=cell.getMaster().getName()
        net=term.getNet();assert net,('Unconnected constrained endpoint',name)
        terms=[dict(name=t.getInst().getName()+'/'+t.getMTerm().getName(),kind='instance',io=str(t.getIoType()),master=t.getInst().getMaster().getName(),location=list(t.getInst().getLocation())) for t in net.getITerms()]
        terms += [dict(name=t.getName(),kind='boundary',io=str(t.getIoType())) for t in net.getBTerms()]
        drivers=[t for t in terms if t['io'] in (('OUTPUT','INOUT') if t['kind']=='instance' else ('INPUT','INOUT'))]
        wire=net.getWire();rule=net.getNonDefaultRule()
        details.append(dict(**row,kind=kind,master=master,pin_direction=str(term.getIoType()),net=net.getName(),net_type=str(net.getSigType()),ndr=rule.getName() if rule else None,drivers=drivers,terminals=terms,wire_length_dbu=wire.getLength() if wire else None))
    (OUT/'hold-target-topology.json').write_text(json.dumps(details,indent=2)+'\n')
    print('SOURCE_BOUND_HOLD_TOPOLOGY',len(details),flush=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source_run=38809759501,final_timing_complete=False,scope='Complete native endpoint census and all three cell-corner rise/fall min/max slacks on original extracted nominalRC. Hold targets retain setup failures/unconstrained cases. No delay-cell prediction, candidate adoption or qualified RC/signoff.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args,label,env=None):
        with (OUT/(label+'.log')).open('w') as stream:
            child=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env)
            for line in child.stdout:stream.write(line);stream.flush();print('['+label+'] '+line,end='',flush=True)
            code=child.wait()
        text=(OUT/(label+'.log')).read_text(errors='replace')
        assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,code)
        return text
    save()
    try:
        result['controls']=controls()
        helper=ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl';assert sha(helper)==HELPER_SHA
        fetch(BASE+'.summary.json',SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'source.tar.gz';fetch(BASE+'.tar.gz.part0000',ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086
        assert not SOURCE.exists()
        with tarfile.open(packed) as archive:
            for member in archive:
                p=Path(member.name);assert not p.is_absolute() and '..'not in p.parts and p.parts[0]=='cloud-routed-extraction'
                assert member.isfile() or member.isdir();archive.extract(member,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==SUMMARY_SHA
        for n,digest in old['outputs'].items():assert sha(SOURCE/n)==digest,n
        for n,digest in old['protected_inputs'].items():assert sha(Path(n))==digest,n
        original=(SOURCE/'actual-routed-sta.tcl').read_text()
        script=OUT/'endpoint-census.tcl'
        script.write_text(original+f'\nsource {{{helper}}}\nset nssoc_endpoint_out {{{OUT}}}\nsource {{{ROOT/"hw/soc/pnr/routed_endpoint_census.tcl"}}}\n')
        log=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(script)],'native-endpoint-census')
        phases=parse_phases(log,'CORNER')
        for p,row in old['nominal_rc_cell_corner_phases'].items():
            assert phases[p]['groups']==row['groups'],('Original routed timing reproduction changed',p)
        record=json.loads((OUT/'native-census.json').read_text());rows=parse_table((OUT/'endpoint-slacks.tsv').read_text())
        assert set(record['corners'])=={'slow','typical','fast'}
        endpoints=record['endpoints'];assert len(endpoints)==record['engine_endpoint_count'] and len(set(endpoints))==len(endpoints)>0
        assert set(rows)=={(c,d,n) for c in record['corners'] for d in ('min','max') for n in endpoints}
        summaries={};targets=[]
        for c in record['corners']:
            for d in ('min','max'):
                values=[rows[(c,d,n)][2] for n in endpoints];finite=[v for v in values if v is not None];assert finite
                minimum=min(finite);reported=old['nominal_rc_cell_corner_phases'][c+'_'+d]['worst_slack_ns']
                assert abs(minimum/record['native_time_unit_seconds']-reported)<=1e-6,(c,d,minimum,reported)
                assert record['native_wns_seconds'][c+'_'+d]==minimum
                summaries[c+'_'+d]=dict(constrained=len(finite),unconstrained=len(values)-len(finite),negative=sum(v<0 for v in finite),worst_seconds=minimum,negative_sum_seconds=math.fsum(v for v in finite if v<0))
        for n in endpoints:
            hold={c:rows[(c,'min',n)][2] for c in record['corners']};setup={c:rows[(c,'max',n)][2] for c in record['corners']}
            finite=[v for v in hold.values() if v is not None]
            if finite and min(finite)<0:
                setup_values=[v for v in setup.values() if v is not None]
                targets.append(dict(endpoint=n,hold_seconds=hold,setup_seconds=setup,worst_hold_seconds=min(finite),worst_setup_seconds=min(setup_values) if setup_values else None,setup_constrained_all_corners=len(setup_values)==len(record['corners'])))
        targets.sort(key=lambda r:(r['worst_hold_seconds'],r['endpoint']))
        assert len(targets)==record['negative_endpoint_count']['min']
        (OUT/'negative-hold-targets.json').write_text(json.dumps(targets,indent=2)+'\n')
        result.update(endpoint_count=len(endpoints),endpoint_corner_delay_rows=len(rows),summary=summaries,negative_hold_endpoints=len(targets));save()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(Path(__file__).resolve())],'native-target-topology',dict(os.environ,NSSOC_ROUTED_ENDPOINT_NATIVE='1'))
        topology=json.loads((OUT/'hold-target-topology.json').read_text());assert len(topology)==len(targets)
        result['hold_target_categories']=dict(positive_setup_all_corners=sum(r['setup_constrained_all_corners'] and r['worst_setup_seconds']>0 for r in targets),existing_setup_violation=sum(r['worst_setup_seconds'] is not None and r['worst_setup_seconds']<0 for r in targets),incomplete_setup_constraints=sum(not r['setup_constrained_all_corners'] for r in targets),boundary=sum(r['kind']=='boundary' for r in topology),multiple_or_missing_driver=sum(len(r['drivers'])!=1 for r in topology))
        assert all(sha(SOURCE/n)==v for n,v in old['outputs'].items())
        assert all(sha(Path(n))==v for n,v in old['protected_inputs'].items())
        result.update(status='COMPLETE_ACTUAL_ROUTED_ENDPOINT_CENSUS_NOT_TIMING_ACCEPTANCE',source_unchanged=True,original_routed_timing_reproduced=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':
    if os.environ.get('NSSOC_ROUTED_ENDPOINT_NATIVE')=='1':native_topology()
    else:main()
