#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native prepare/audit stages only. No routing, archive access, or process launch."""
import hashlib,json,os,runpy
from pathlib import Path
import odb
import mainchip_original_clock_restoration as c

def load(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path))
    return db,db.getChip().getBlock()

def selected(b):
    # These two statements are copied byte-for-byte from the unchanged gate.
    clocks={n.getName()for n in b.getNets()if str(n.getSigType())=='CLOCK'or str(n.getWireType())=='FIXED'or any(str(t.getMTerm().getSigType())=='CLOCK'or t.getInst().getName().startswith('clkbuf')for t in n.getITerms())}
    clocks={n for n in clocks if str(b.findNet(n).getSigType())not in ('POWER','GROUND')}
    assert 'clknet_3_5_0_pcie_clk_i' in clocks and len(clocks)>100
    return clocks

def term(t):
    i=t.getInst()
    return [i.getName(),t.getMTerm().getName(),i.getMaster().getName(),str(t.getIoType()),
            list(i.getLocation()),str(i.getOrient()),list(t.getAvgXY()),
            str(i.getPlacementStatus()),list(i.getOrigin()),str(t.getMTerm().getSigType())]

def boxes(v):
    return sorted((b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())for b in v.getBoxes())

def identity(db,n):
    rule=n.getNonDefaultRule()
    return dict(name=n.getName(),sigtype=str(n.getSigType()),
        terminals=sorted(term(t)for t in n.getITerms()),
        bterms=sorted([p.getName(),str(p.getIoType()),str(p.getSigType()),
            [[list(x)for x in boxes(pin)]for pin in p.getBPins()]]for p in n.getBTerms()),
        rule=None if rule is None else [rule.getName(),rule.getHardSpacing(),
            [[l.getName(),rule.getLayerRule(l).getWidth(),rule.getLayerRule(l).getSpacing()]
             for l in db.getTech().getLayers()if rule.getLayerRule(l)]])

def encoded(n):
    w=n.getWire(); paths=[]
    if w:
        d=odb.dbWireDecoder();d.begin(w)
        while True:
            op=d.next()
            if op==d.END_DECODE:break
            if op in (d.PATH,d.JUNCTION,d.SHORT,d.VWIRE):paths.append(str(d.getWireType()))
    return dict(wire_present=w is not None,metadata=str(n.getWireType()),paths=paths)

def vias(db,b,names,required=None):
    result={}
    if required is None:
        for name in names:
            w=b.findNet(name).getWire()
            if not w:continue
            d=odb.dbWireDecoder();d.begin(w)
            while True:
                op=d.next()
                if op==d.END_DECODE:break
                if op in (d.VIA,d.TECH_VIA):
                    v=d.getVia()if op==d.VIA else d.getTechVia()
                    kind='block'if op==d.VIA else'tech'
                    result[kind+':'+v.getName()]=boxes(v)
    else:
        for key,expected in required.items():
            kind,name=key.split(':',1)
            v=b.findVia(name)if kind=='block'else db.getTech().findVia(name)
            assert v is not None,('missing imported via',key)
            result[key]=boxes(v)
        assert result==required,'donor/recipient via definition mismatch'
    return result

def ndr_records(raw, names):
    """Compare complete exported NDR definitions, beyond the qualified API projection."""
    import re
    found=list(re.finditer(rb'(?m)^NONDEFAULTRULES ([0-9]+) ;\n',raw))
    if not names:
        return {}
    assert len(found)==1
    end=raw.index(b'END NONDEFAULTRULES',found[0].end())
    body=raw[found[0].end():end]
    records={};pending=[]
    for line in body.splitlines(keepends=True):
        if re.match(rb'^[ \t]*- ',line):
            assert not pending;pending=[line]
        elif pending:pending.append(line)
        else:assert not line.strip()
        if pending and b';'in line:
            assert line.count(b';')==1 and not line.split(b';',1)[1].strip()
            record=b''.join(pending);name=record.split()[1].decode()
            assert name not in records;records[name]=record.decode();pending=[]
    assert not pending and len(records)==int(found[0].group(1)) and names<=records.keys()
    return {n:records[n]for n in sorted(names)}

def view(path,export_path,names=None,required_vias=None):
    db,b=load(path)
    try:
        assert len(list(b.getInsts()))==153130
        actual=selected(b) if names is None else set(names)
        assert len(actual)==1691
        odb.write_def(b,str(export_path))
        raw=c.regular(export_path).read_bytes();records=c.parse_def(raw)['records']
        assert actual<=records.keys()
        snaps={};ids={};enc={}
        for name in sorted(actual):
            n=b.findNet(name);assert n
            snaps[name]=dict(statement=records[name].decode().split(),
                instances={i.getName():dict(master=i.getMaster().getName(),location=list(i.getLocation()),
                    orientation=str(i.getOrient()),status=str(i.getPlacementStatus()))
                    for i in {t.getInst()for t in n.getITerms()}})
            ids[name]=identity(db,n);enc[name]=encoded(n)
        definitions=vias(db,b,actual,required_vias)
        rules={v['rule'][0]for v in ids.values()if v['rule']is not None}
        return dict(raw=raw,snapshot=snaps,identity=ids,encoded=enc,
                    vias=definitions,ndr=ndr_records(raw,rules),names=sorted(actual))
    finally:odb.dbDatabase.destroy(db)

def tcl_path(p):
    p=Path(p).resolve()
    assert str(p).startswith('/home/runner/work/nssoc/nssoc/')
    assert all(ch not in str(p)for ch in '{}\n\r\\')
    return '{'+str(p)+'}'

def import_tcl(source,patch,out,stem):
    # Exact qualified pair of FLOORPLAN imports; no DRT command or restart.
    return ('read_db '+tcl_path(source)+'\nread_def -floorplan_initialize '+tcl_path(patch)+
        '\nwrite_def '+tcl_path(out/(stem+'-single.def'))+
        '\nread_def -floorplan_initialize '+tcl_path(patch)+
        '\nwrite_def '+tcl_path(out/(stem+'.def'))+
        '\nwrite_db '+tcl_path(out/(stem+'.odb'))+'\n')

def context(donor,recipient,out):
    assert c.file_sha(donor)==c.DONOR_SHA and c.file_sha(recipient)==c.RECIPIENT_SHA
    report=c.diagnosis(c.regular(c.ROOT/c.DIAG).read_bytes())
    a=view(donor,out/'fresh-before.def')
    b=view(recipient,out/'fresh-after.def',a['names'],a['vias'])
    assert a['identity']==b['identity'],'source terminals/BTerms/masters/positions/NDR changed'
    assert a['ndr']==b['ndr'],'source complete NDR definition changed'
    expected,plan=c.make_plan(a['raw'],b['raw'],{'before':a['snapshot'],'after':b['snapshot']},report)
    return a,b,expected,plan

def audit_view(path,expected,baseline,out,label):
    got=view(path,out/(label+'-reread.def'),baseline['names'],baseline['vias'])
    c.verify_exact(expected,got['raw'])
    assert got['identity']==baseline['identity'],'native terminal or BTerm identity changed'
    assert got['ndr']==baseline['ndr'],'complete native NDR changed'
    return got

def original_gate(donor,candidate,out,label):
    assert c.file_sha(c.ROOT/c.GATE)==c.GATE_SHA
    keys={'NSSOC_CLOCK_BEFORE':str(donor),'NSSOC_CLOCK_AFTER':str(candidate),
          'NSSOC_CLOCK_AUDIT':str(out/label)}
    previous={k:os.environ.get(k)for k in keys}
    try:
        os.environ.update(keys);runpy.run_path(str(c.ROOT/c.GATE),run_name='__main__')
        p=out/label/'result.json';r=json.loads(c.regular(p).read_bytes())
        assert r['clock_or_fixed_nets']==1691 and r['all_source_clock_and_fixed_records_preserved']is True
        return dict(result=r,sha256=c.file_sha(p))
    finally:
        for k,v in previous.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=c.source_gate()
    assert m['native_prepare_audit_authorized']is True,'native prepare/audit not authorized'
    assert m['native_routing_authorized']is False and m['simulation_authorized']is False
    mode=os.environ['NSSOC_CLOCK_RESTORE_PHASE']
    assert mode in ('prepare','audit-restored','prepare-fixed','audit-fixed','audit-unfixed')
    donor=c.regular(Path(os.environ['NSSOC_CLOCK_RESTORE_DONOR']))
    recipient=c.regular(Path(os.environ['NSSOC_CLOCK_RESTORE_RECIPIENT']))
    out=Path(os.environ['NSSOC_CLOCK_RESTORE_OUT'])
    assert out.is_absolute()and not out.is_symlink()
    for p in out.parents:assert not p.is_symlink()
    if mode=='prepare':out.mkdir(exist_ok=False)
    else:assert out.is_dir()
    assert out.resolve()not in donor.parents and out.resolve()not in recipient.parents,'source inside writable output'
    for p in out.rglob('*'):
        assert not p.is_symlink()and (p.is_file()or p.is_dir()),('unsafe existing output',str(p))
    result=dict(status='RUNNING',phase=mode,accepted=False,routing_started=False,
        routing_drc_passed=False,final_timing_complete=False,full_phy_accepted=False)
    def save():
        (out/(mode+'-result.json')).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    try:
        a,b,expected,plan=context(donor,recipient,out)
        result['plan']=plan
        if mode=='prepare':
            records=c.parse_def(a['raw'])['records']
            patch,removed=c.patch_def(b['raw'],{n:records[n]for n in plan['changed_names']})
            (out/'restore-patch.def').write_bytes(patch);(out/'expected-restored.def').write_bytes(expected)
            (out/'restore.tcl').write_text(import_tcl(recipient,out/'restore-patch.def',out,'restored'))
            result.update(status='PREPARED_EXACT_218_RESTORE_REQUIRES_NATIVE_IMPORT_AND_ORIGINAL_GATE',
                          patch_sha256=c.digest(patch),removed_patch_connections=removed)
        else:
            restored=c.regular(out/'restored.odb')
            r=audit_view(restored,expected,b,out,'restored')
            assert r['snapshot']==a['snapshot'],'all original selected snapshots differ'
            assert r['encoded']==a['encoded'],'original encoded wire classes differ'
            if mode=='audit-restored':
                result['original_gate']=original_gate(donor,restored,out,'original-gate-restored')
                result['restored_odb_sha256']=c.file_sha(restored)
                result['status']='PASS_EXACT_ORIGINAL_CLOCK_RESTORE_REQUIRES_ZERO_DRC_DETERMINATION'
            else:
                prior=json.loads(c.regular(out/'audit-restored-result.json').read_bytes())
                assert prior['status']=='PASS_EXACT_ORIGINAL_CLOCK_RESTORE_REQUIRES_ZERO_DRC_DETERMINATION'
                assert prior['restored_odb_sha256']==c.file_sha(restored) and prior['plan']==plan
                proof=prior['original_gate']
                assert c.file_sha(out/'original-gate-restored/result.json')==proof['sha256']
                assert json.loads(c.regular(out/'original-gate-restored/result.json').read_bytes())==proof['result']
                assert proof['result']['clock_or_fixed_nets']==1691
                assert proof['result']['source_hashes']=={str(donor):c.DONOR_SHA,str(restored):c.file_sha(restored)}
                fixed,classes=c.fixed_overlay(expected,plan['all_clock_names'])
                names={n:v for n,v in classes.items()if v is not None}
                if mode=='prepare-fixed':
                    # This is a round-trip control only, with no repair or routing.
                    fixed_records=c.parse_def(fixed)['records']; restored_records=c.parse_def(expected)['records']
                    patch,_=c.patch_def(expected,{n:fixed_records[n]for n in names})
                    back,_=c.patch_def(expected,{n:restored_records[n]for n in names})
                    (out/'fixed-patch.def').write_bytes(patch);(out/'unfixed-patch.def').write_bytes(back)
                    (out/'fixed.tcl').write_text(import_tcl(restored,out/'fixed-patch.def',out,'fixed'))
                    (out/'unfixed.tcl').write_text(import_tcl(out/'fixed.odb',out/'unfixed-patch.def',out,'unfixed'))
                    result['status']='PREPARED_FIXED_ENCODING_ROUNDTRIP_NO_ROUTING'
                else:
                    f=audit_view(c.regular(out/'fixed.odb'),fixed,b,out,'fixed')
                    c.validate_encoded(f['encoded'],{n:'FIXED'if v is not None else None for n,v in classes.items()})
                    assert c.restore_classes(f['raw'],classes)==expected,'temporary class overlay is not reversible'
                    if mode=='audit-fixed':
                        result['status']='PASS_ACTUAL_FIXED_ENCODING_REQUIRES_ORIGINAL_CLASS_ROUNDTRIP'
                    else:
                        u=audit_view(c.regular(out/'unfixed.odb'),expected,b,out,'unfixed')
                        assert u['encoded']==r['encoded'],'original actual path classes not restored'
                        result['original_gate']=original_gate(donor,out/'unfixed.odb',out,'original-gate-unfixed')
                        result['status']='PASS_FIXED_ENCODING_ROUNDTRIP_NOT_DRC_OR_ROUTING_ACCEPTANCE'
        result['source_inputs_unchanged']=c.file_sha(donor)==c.DONOR_SHA and c.file_sha(recipient)==c.RECIPIENT_SHA
        assert result['source_inputs_unchanged']
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:save()

if __name__=='__main__':main()
