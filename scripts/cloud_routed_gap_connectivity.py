#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resolve exact unconstrained timing pins against immutable routed native ODB."""
import json,os,subprocess,re
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-routed-gap-connectivity'
ODB_SHA='49a805c66e904b534dd846bcca58070feaeac77dfe1427f7937e89427b0085e8'

def native():
    import odb
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    source=OUT/'source/routed.odb';assert sha(source)==ODB_SHA
    inventory=json.loads((OUT/'inventory/result.json').read_text())
    db=odb.dbDatabase.create();odb.read_db(db,str(source));block=db.getChip().getBlock()
    assert len(block.getInsts())==114031 and len(block.getNets())==114103
    def resolve(pin):
        assert pin['kind']=='instance',pin
        inst=block.findInst(pin['instance']);assert inst is not None,('missing_instance',pin)
        term=inst.findITerm(pin['pin']);assert term is not None,('missing_pin',pin)
        assert inst.getName()==pin['instance'] and term.getMTerm().getName()==pin['pin']
        return inst,term
    def iterm(t):
        return dict(kind='instance',instance=t.getInst().getName(),pin=t.getMTerm().getName(),
                    direction=str(t.getIoType()),signal_type=str(t.getMTerm().getSigType()))
    def bterm(t):
        return dict(kind='boundary',port=t.getName(),direction=str(t.getIoType()),signal_type=str(t.getSigType()))
    nets={}
    def net_record(net):
        if net is None:return None
        name=net.getName()
        if name not in nets:
            ins=[iterm(t)for t in net.getITerms()];bs=[bterm(t)for t in net.getBTerms()]
            assert all(t['direction']in ('INPUT','OUTPUT','INOUT','FEEDTHRU')for t in ins+bs)
            # Bidirectional/feedthrough terminals are explicitly ambiguous.
            # Driver/load counts are connectivity facts, not timing exceptions.
            drivers=sum(t['direction']=='OUTPUT'for t in ins)+sum(t['direction']=='INPUT'for t in bs)
            loads=sum(t['direction']=='INPUT'for t in ins)+sum(t['direction']=='OUTPUT'for t in bs)
            ambiguous=sum(t['direction']in ('INOUT','FEEDTHRU')for t in ins+bs)
            nets[name]=dict(signal_type=str(net.getSigType()),drivers=drivers,loads=loads,ambiguous_terminals=ambiguous,
                instance_pins=sorted(ins,key=lambda t:(t['instance'],t['pin'])),boundary_pins=sorted(bs,key=lambda t:t['port']))
        return name
    def detail(d):
        inst,t=resolve(d['physical_pin']);direction=str(t.getIoType());net=net_record(t.getNet())
        if net is None:classification=direction.lower()+'_disconnected'
        elif nets[net]['ambiguous_terminals']:classification='connected_ambiguous_direction'
        elif direction=='OUTPUT':classification='output_with_loads'if nets[net]['loads']else'output_no_loads'
        elif direction=='INPUT':classification='input_with_driver'if nets[net]['drivers']else'input_no_driver'
        else:classification='connected_other_direction'
        result=dict(d,master=inst.getMaster().getName(),direction=direction,net=net,classification=classification)
        if direction!='OUTPUT':
            result['instance_pin_connections']=[dict(iterm(p),net=net_record(p.getNet()))for p in inst.getITerms()]
        return result
    coverage={}
    for delay,expected in [('max',1072),('min',1117)]:
        source_rows=inventory['coverage'][delay]['endpoints'];assert len(source_rows)==expected
        rows=[detail(d)for d in source_rows]
        coverage[delay]=dict(endpoints=rows,counts=dict(Counter(d['classification']for d in rows)),directions=dict(Counter(d['direction']for d in rows)))
    setup={c:[detail(d)for d in v['worst32']]for c,v in inventory['setup'].items()}
    exemplar=inventory['coverage']['max']['endpoints'][0]['physical_pin']
    controls=[]
    for field in ('instance','pin'):
        bad=dict(exemplar);bad[field]+='__NSSOC_NONEXISTENT_IDENTITY_CONTROL__'
        try:resolve(bad)
        except AssertionError as e:
            assert str(e).startswith("('missing_"+field+"'")
            controls.append(dict(field=field,rejected=True,reason=str(e)))
        else:raise AssertionError(('malformed_identity_accepted',field))
    assert sha(source)==ODB_SHA
    result=dict(status='COMPLETE_ACTUAL_NATIVE_CONNECTIVITY_NOT_TIMING_EXCEPTION',accepted=False,
        odb_sha256=ODB_SHA,source_unchanged=True,coverage=coverage,worst_setup=setup,nets=nets,identity_controls=controls,
        scope='Native pin direction, master and net connectivity only. No clock/exception/fan-in functional proof; disconnected or no-load nodes are not waived. No SDC/ODB change.')
    (OUT/'native-connectivity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:coverage[k]['counts']for k in coverage}),flush=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,constraints_changed=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        inv,ip=reports.restore_report('routed-coverage-gaps',38998404892,
            '94c9b083f1bc8d2cc55659410d56dabf4c0f4181977a9850208faf8fed1d41ca',
            'd47ac7f5d6098e2416590f46ff7dadfea68a6f1b7519862f7f500a6a24b65c1e',OUT/'inventory',())
        assert inv['status']=='COMPLETE_EXACT_ROUTED_COVERAGE_GAP_INVENTORY_NOT_TIMING_ACCEPTANCE'
        assert inv['source']['run']==38992990610 and inv['source_unchanged']
        source,sp=reports.restore_report('ethernet-compatible-rc',38992990610,
            '40ef6346436194693fea5797abbec711be536a28341fd177d81c3166b47226c1',
            '9987410d8eac9ec94c53ee3d2bfed3643bde1281098b142bdeede27e2bb80858',OUT/'source',('routed.odb',))
        assert source['candidate_odb_sha256']==ODB_SHA and source['source_unchanged']
        runtime=Path(os.environ['CLOUD_APPIMAGE']);assert sha(runtime)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        result.update(inventory_source=ip,routed_source=sp,runtime_sha256=sha(runtime));save()
        with(OUT/'native.log').open('w')as log:
            p=subprocess.run([str(runtime),'openroad','-exit','-python',str(Path(__file__).resolve())],
                env=dict(os.environ,NSSOC_GAP_CONNECTIVITY_NATIVE='1'),stdout=log,stderr=subprocess.STDOUT)
        text=(OUT/'native.log').read_text(errors='replace');print(text[-5000:],flush=True)
        assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:|^Traceback',text),(p.returncode,text[-1500:])
        native_result=json.loads((OUT/'native-connectivity.json').read_text())
        assert native_result['status']=='COMPLETE_ACTUAL_NATIVE_CONNECTIVITY_NOT_TIMING_EXCEPTION'
        for directory,proof in [(OUT/'source',sp),(OUT/'inventory',ip)]:
            assert all(sha(directory/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        result.update(status='COMPLETE_ROUTED_GAP_NATIVE_CONNECTIVITY_NOT_TIMING_ACCEPTANCE',source_unchanged=True,
            counts={k:v['counts']for k,v in native_result['coverage'].items()},directions={k:v['directions']for k,v in native_result['coverage'].items()},
            identity_controls=native_result['identity_controls'],native_report_sha256=sha(OUT/'native-connectivity.json'))
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    if os.environ.get('NSSOC_GAP_CONNECTIVITY_NATIVE')=='1':native()
    else:main()
