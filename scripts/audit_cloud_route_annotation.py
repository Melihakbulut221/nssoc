#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Classify every native unannotated driver against actual routes and exact SPEF."""
import collections,hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-route-annotation'
SUMMARY_SHA='aa721c7ccd04c30ed97af33dac632eb0cfdd99fd27232a46819299d12f62e583'
ARCHIVE_SHA='131bc44b4dc4d26f9ba1fa6a34b17742aa0ccf65e8c3075dca91dfe5dc5c1d4a'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38809759501-1-routed-extraction/routed-extraction-38809759501-1'

def drivers(text):
    match=re.search(r'(?m)^Found (\d+) unannotated drivers\.\s*\n(.*?)^Found (\d+) partially unannotated drivers\.',text,re.S)
    assert match,'Missing native annotation section'
    rows=[x.strip() for x in match[2].splitlines() if x.strip()]
    assert len(rows)==int(match[1]) and len(rows)==len(set(rows))
    assert int(match[3])==0,'Partial annotation requires separate classification'
    return rows

def controls():
    text='Found 2 unannotated drivers.\n a\n b/Y\nFound 0 partially unannotated drivers.'
    assert drivers(text)==['a','b/Y']
    faults=[text.replace('Found 2','Found 3'),text.replace(' b/Y',' a'),text.replace('Found 0 partially','Found 1 partially'),text.split('Found 0')[0]]
    for bad in faults:
        try:drivers(bad)
        except AssertionError:continue
        raise AssertionError('Malformed native annotation accepted')
    return dict(positive=1,negative=len(faults))

def spef_net_name(name):
    # Exact extSpef::addEscChar(name, false), pinned OpenROAD dcf36133.
    # Already escaped literal brackets must not be unescaped into bus indexes.
    assert name.isascii()
    return ''.join(('\\' if not ch.isalnum() and ch not in '_\\/[]' and (i==0 or name[i-1]!='\\') else '')+ch for i,ch in enumerate(name))

def name_controls():
    pairs=[('bus[2]','bus[2]'),(r'bus\[2\]',r'bus\[2\]'),('$a.b:c',r'\$a\.b\:c'),('path/a','path/a'),(r'\$a',r'\$a')]
    # Literal escaped brackets and true bus indexes remain distinct.
    for source,expected in pairs:assert spef_net_name(source)==expected,(source,expected,spef_net_name(source))
    assert spef_net_name(pairs[0][0])!=spef_net_name(pairs[1][0])
    return dict(exact_native_writer_cases=len(pairs),literal_brackets_distinct=True)

def native():
    import odb
    d=odb.dbDatabase.create();odb.read_db(d,str(OUT/'routed.odb'));b=d.getChip().getBlock()
    assert len(b.getInsts())==113791 and len(b.getNets())==113863
    nets={n.getName():n for n in b.getNets()};namemap={};caps={};inmap=False;aliases=collections.Counter()
    def resolve(token,name):
        assert re.fullmatch(r'\*\d+',token),('Expected native name map token',token)
        ident=int(token[1:]);assert ident>0
        net=odb.dbNet.getNet(b,ident);assert net,('Unknown native net id',ident)
        chosen=net.getName();assert chosen in nets;expected=spef_net_name(chosen)
        assert name==expected,('Native net id/name mismatch',ident,chosen,name,expected)
        aliases['native_id_and_exact_writer_name']+=1;return chosen
    with (OUT/'actual-route.nominal.spef').open() as stream:
        for line in stream:
            row=line.strip()
            if row=='*NAME_MAP':inmap=True;continue
            if inmap:
                m=re.fullmatch(r'(\*\d+)\s+(.+)',row)
                if m:assert m[1] not in namemap;namemap[m[1]]=m[2];continue
                if row.startswith('*'):inmap=False
            if row.startswith('*D_NET '):
                fields=row.split();assert len(fields)==3
                token=fields[1];n=resolve(token,namemap[token]);assert n not in caps;caps[n]=float(fields[2]);assert caps[n]>=0
    assert len(caps)==113556
    names=drivers((OUT/'actual-routed-sta.log').read_text());assert len(names)==1065
    rows=[]
    for name in names:
        term=b.findBTerm(name)
        if term:kind='boundary';io=str(term.getIoType());net=term.getNet();master=None
        else:
            inst,pin=name.rsplit('/',1);i=b.findInst(inst);assert i,('Missing driver instance',name)
            term=i.findITerm(pin);assert term,('Missing driver pin',name)
            kind='instance';io=str(term.getIoType());net=term.getNet();master=i.getMaster().getName()
        assert io in (('INPUT','INOUT') if kind=='boundary' else ('OUTPUT','INOUT')),('Not a driver',name,io)
        row=dict(driver=name,kind=kind,io=io,master=master,net=None if not net else net.getName())
        if not net:row.update(category='DISCONNECTED_DRIVER',sinks=[],spef_present=False)
        else:
            n=net.getName();terminals=[]
            for t in net.getITerms():terminals.append(dict(name=t.getInst().getName()+'/'+t.getMTerm().getName(),kind='instance',io=str(t.getIoType())))
            for t in net.getBTerms():terminals.append(dict(name=t.getName(),kind='boundary',io=str(t.getIoType())))
            sinks=[t['name'] for t in terminals if t['name']!=name and t['io'] in (('INPUT','INOUT') if t['kind']=='instance' else ('OUTPUT','INOUT'))]
            wire=net.getWire()
            category='CONNECTED_NO_SINK' if not sinks else 'LOADED_PRESENT_IN_SPEF_UNANNOTATED' if n in caps else 'LOADED_ABSENT_FROM_SPEF'
            row.update(category=category,sinks=sinks,terminals=terminals,spef_present=n in caps,spef_d_net_cap=caps.get(n),signal_type=str(net.getSigType()),wire_present=bool(wire),wire_length_dbu=wire.getLength() if wire else None)
        rows.append(row)
    counts=dict(collections.Counter(r['category'] for r in rows));loaded=[r for r in rows if r['sinks']]
    (OUT/'driver-classification.json').write_text(json.dumps(dict(status='COMPLETE_SOURCE_BOUND_ANNOTATION_DIAGNOSIS_NOT_COVERAGE_ACCEPTANCE',accepted=False,checked=len(rows),counts=counts,loaded_unannotated_drivers=len(loaded),spef_nets=len(caps),spef_name_resolution=dict(aliases),drivers=rows,scope='Descriptive native OpenSTA driver classification against exact routed ODB terminals and extracted SPEF D_NET inventory. No missing loaded net is waived. Disconnected outputs alone do not prove unused functional interfaces or complete timing coverage.'),indent=2)+'\n')
    print(json.dumps(dict(counts=counts,loaded_unannotated_drivers=len(loaded))),flush=True)

def main():
    from route_cloud_newer_postcts import fetch,sha
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source_run=38809759501,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['controls']=dict(annotation=controls(),spef_names=name_controls());fetch(BASE+'.summary.json',SUMMARY_SHA,OUT/'original-summary.json');old=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'source.tar.gz';fetch(BASE+'.tar.gz.part0000',ARCHIVE_SHA,packed);assert packed.stat().st_size==225682086
        selected={'source/routed.odb':'routed.odb','actual-route.nominal.spef':'actual-route.nominal.spef','actual-routed-sta.log':'actual-routed-sta.log'}
        protected={}
        with tarfile.open(packed) as archive:
            for name,target in selected.items():
                member=archive.getmember('cloud-routed-extraction/'+name);assert member.isfile()
                with archive.extractfile(member) as src,(OUT/target).open('wb') as dst:
                    import shutil
                    shutil.copyfileobj(src,dst)
                assert sha(OUT/target)==old['outputs'][name];protected[target]=old['outputs'][name]
        packed.unlink();result['source_files']=protected;result['source_summary_sha256']=SUMMARY_SHA;save()
        with (OUT/'native-classification.log').open('w') as log:
            proc=subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(Path(__file__).resolve())],env=dict(os.environ,NSSOC_ANNOTATION_NATIVE='1'),stdout=log,stderr=subprocess.STDOUT)
        print((OUT/'native-classification.log').read_text(),flush=True);assert proc.returncode==0
        detail=json.loads((OUT/'driver-classification.json').read_text());result.update(classification={k:v for k,v in detail.items() if k!='drivers'},status='COMPLETE_SOURCE_BOUND_ANNOTATION_DIAGNOSIS_NOT_COVERAGE_ACCEPTANCE')
        assert all(sha(OUT/n)==v for n,v in protected.items());result['source_unchanged']=True
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':
    if os.environ.get('NSSOC_ANNOTATION_NATIVE')=='1':native()
    else:main()
