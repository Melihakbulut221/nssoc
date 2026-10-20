#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check compact transistor topology after geometrical return repair."""
import copy,difflib,hashlib,json,os,tarfile,re
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
from build_pcie_local_vco_hybrid_v6 import statements
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-fast-wire20-model-compare'
def compare(a,b):
    assert a[0][0].lower()==b[0][0].lower()=='.subckt'
    assert a[-1][0].lower()==b[-1][0].lower()=='.ends'
    pa,pb=a[0][2:],b[0][2:];assert len(pa)==len(pb)==162 and set(pa)==set(pb)
    old={v[0]:v for v in a[1:-1]};new={v[0]:v for v in b[1:-1]}
    assert len(old)==len(new)==1674 and old.keys()==new.keys()
    mapping={n:n for n in pa};reverse=dict(mapping);types={}
    for name,row in old.items():
        other=new[name]
        matches=[i for i,v in enumerate(row)if v in ('npn13g2','rppd','ptap1')]
        assert len(matches)==1;idx=matches[0]
        assert row[idx:]==other[idx:],('Device type/parameters changed',name)
        assert idx in (3,4,5) and len(row)==len(other)
        types[row[idx]]=types.get(row[idx],0)+1
        for x,y in zip(row[1:idx],other[1:idx],strict=True):
            assert mapping.setdefault(x,y)==y,('Nonconsistent node map',name,x,y)
            assert reverse.setdefault(y,x)==x,('Nonbijective node map',name,x,y)
    assert len(mapping)==len(reverse)
    return dict(devices=len(old),ports=len(pa),device_types=types,bijective_node_map=mapping,changed_internal_names=sum(a!=b for a,b in mapping.items()),public_port_order_equal=pa==pb,all_public_names_fixed=True,all_device_parameters_exact=True)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False,parents=True)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        models={};proof={};physical_keys={}
        for label,name,root in [('baseline','tx-v5-timing-priority-composition-pass-20261019.json','cloud-tx-v5-timing-priority-assembly'),('candidate','tx-fast-wire20-composition-pass-20261020.json','cloud-tx-fast-wire20-physical')]:
            pin=json.loads((ROOT/'docs/evidence'/name).read_text());archive=OUT/(label+'.tar.gz')
            fetch(pin['url'],pin['sha256'],archive);assert archive.stat().st_size==pin['bytes']
            with tarfile.open(archive)as tar:
                raw=tar.extractfile(root+'/binding96/tree1674-compact01.spice').read()
                assert hashlib.sha256(raw).hexdigest()==pin['model_sha256']['compact']
                def member(rel,digest):
                    data=tar.extractfile(root+'/'+rel).read();assert hashlib.sha256(data).hexdigest()==digest;return json.loads(data)
                interface=member('wire96/all-interface-probes.json',pin['outputs']['wire96/all-interface-probes.json'])
                assert interface['status']=='PASS_ALL124_PHYSICAL_INPUT_LEGS_AND372_DATA_BASES'
                def bound(rel):
                    hits=[x for n,x in interface['inputs'].items()if n.endswith('/'+rel)];assert len(hits)==1
                    return member(rel,hits[0])
                locations=bound('wire96/device-locations01.json');layout=bound('layout/result.json')
                binding=member('binding96/binding01.json',pin['outputs']['binding96/binding01.json'])
                def rect(raw):
                    fields=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(fields)==4;return fields
                dx,dy=layout['origin_translation_um'];boxes={}
                for tag,p in layout['placements'].items():
                    l,b,rr,t=rect(p['bbox_um']);boxes[tag]=[l+dx,b+dy,rr+dx,t+dy]
                ids={d['native_id']:d['instance'].lower()for d in binding['devices']}
                keys={}
                for d in locations['devices']:
                    b=rect(d['pcell']['bbox']);owners=[tag for tag,q in boxes.items()if b[0]>=q[0]-1e-8 and b[1]>=q[1]-1e-8 and b[2]<=q[2]+1e-8 and b[3]<=q[3]+1e-8];assert len(owners)==1
                    tag=owners[0];q=boxes[tag];relative=[b[0]-q[0],b[1]-q[1],b[2]-q[0],b[3]-q[1]]
                    quantized=tuple(round(x*1000)for x in relative);assert all(abs(x-y/1000)<1e-7 for x,y in zip(relative,quantized))
                    key=(tag,d['model'].lower(),quantized);assert key not in keys;keys[key]=ids[d['native_id']]
                assert len(keys)==len(ids)==len(locations['devices'])==1674
                physical_keys[label]=keys

            archive.unlink();(OUT/(label+'.spice')).write_bytes(raw);models[label]=raw.decode()
            proof[label]=dict(source_run=pin['source_run'],source_head=pin['source_head'],summary_sha256=pin['summary_sha256'],archive_sha256=pin['sha256'],compact_sha256=pin['model_sha256']['compact'])
        result['sources']=proof
        a,b=[statements(models[label])for label in ('baseline','candidate')]
        result['byte_identical']=models['baseline']==models['candidate']
        result['statement_diff']=list(difflib.unified_diff(models['baseline'].splitlines(),models['candidate'].splitlines()))[:100]
        # Native numbering changes with placement. Fix correspondence from
        # independently hashed primitive positions inside unchanged named macros,
        # before looking at any electrical node or parameter values.
        assert physical_keys['baseline'].keys()==physical_keys['candidate'].keys()
        original_names={row[0].lower():row[0]for row in a[1:-1]};assert len(original_names)==1674
        rename={physical_keys['candidate'][k]:original_names[physical_keys['baseline'][k]]for k in physical_keys['baseline']}
        assert len(rename)==len(set(rename.values()))==1674
        assert set(rename)=={r[0].lower()for r in b[1:-1]}
        b=copy.deepcopy(b)
        for row in b[1:-1]:row[0]=rename[row[0].lower()]
        result['native_instance_correspondence']=dict(method='Actual primitive model and local nanometer bbox within each named physical macro',renamed=sum(x!=y for x,y in rename.items()),pairs=rename,devices=1674)
        result['comparison']=compare(a,b)
        controls=[]
        for fault in ['missing_device','changed_parameter','wrong_terminal']:
            bad=copy.deepcopy(b)
            if fault=='missing_device':bad.pop(1)
            elif fault=='changed_parameter':
                row=next(v for v in bad[1:-1]if 'npn13g2'in v);j=next(i for i,v in enumerate(row)if v.startswith('nx='));row[j]='nx='+str(int(row[j].split('=')[1])+1)
            else:
                row=next(v for v in bad[1:-1]if 'npn13g2'in v);row[1]='avdd'if row[1]!='avdd'else'avss'
            try:compare(a,bad)
            except AssertionError as e:controls.append(dict(fault=fault,rejected=True,reason=str(e)))
            else:raise AssertionError('Real compact model fault accepted: '+fault)
        # Actual physical identity corruption must also fail, independently of node spelling.
        bad=copy.deepcopy(b);left=next(row for row in bad[1:-1]if 'npn13g2'in row);right=next(row for row in bad[1:-1]if 'rppd'in row)
        left[0],right[0]=right[0],left[0]
        try:compare(a,bad)
        except AssertionError:result['physical_identity_swap_rejected']=True
        else:raise AssertionError('Wrong physical-device correspondence accepted')
        assert len(controls)==3
        result.update(status='PASS_NATIVE1674_COMPACT_MODEL_TOPOLOGY_EQUIVALENCE_WITH_THREE_FAULTS',controls=controls)
    except BaseException as e:result.update(status='FAIL_COMPACT_MODEL_COMPARISON',error=repr(e));raise
    finally:
        result['outputs']={p.name:sha(p)for p in OUT.iterdir()if p.is_file()and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
