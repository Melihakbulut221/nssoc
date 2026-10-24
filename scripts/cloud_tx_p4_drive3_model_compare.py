#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check compact transistor topology after geometrical return repair."""
import copy,difflib,hashlib,json,os,tarfile,re
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
from build_pcie_local_vco_hybrid_v6 import statements
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-p4-drive3-model-compare'
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
        models={};proof={};physical_keys={};interfaces={};bindings={}
        for label,name,root in [('baseline','tx-fast-wire20-composition-pass-20261020.json','cloud-tx-fast-wire20-physical'),('candidate','tx-p4-drive3-composition-pass-20261020.json','cloud-tx-p4-drive3-physical')]:
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
                physical_keys[label]=keys;interfaces[label]=interface;bindings[label]=binding
            archive.unlink();(OUT/(label+'.spice')).write_bytes(raw);models[label]=raw.decode()
            proof[label]=dict(source_run=pin['source_run'],source_head=pin['source_head'],summary_sha256=pin['summary_sha256'],archive_sha256=pin['sha256'],compact_sha256=pin['model_sha256']['compact'])
        result['sources']=proof
        original,b=[statements(models[label])for label in ('baseline','candidate')]
        assert len(original[1:-1])==len(b[1:-1])==1674
        before={r[0].lower():r for r in original[1:-1]}
        tags={'p4_0','p4_1','p4_2','p4_3'}
        baseline_keys=physical_keys['baseline'];candidate_keys=physical_keys['candidate']
        old_owner={name:k[0]for k,name in baseline_keys.items()}
        def model_index(row):
            indices=[i for i,v in enumerate(row)if v in ('npn13g2','rppd','ptap1')]
            assert len(indices)==1 and indices[0]in (3,4,5)
            return indices[0]
        node_owners={}
        for name,row in before.items():
            tag=old_owner[name]
            for n in row[1:model_index(row)]:node_owners.setdefault(n,set()).add(tag)
        physical_pin=json.loads((ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json').read_text())
        assert physical_pin['run']==39304550527 and physical_pin['summary_sha256']=='03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d'
        maps=physical_pin['report']['plan']['maps']
        public=set(bindings['baseline']['native_ports'])
        def port_node(tag,port):
            net=maps[tag][port]
            if net in public:return net
            nodes=interfaces['baseline']['modes']['compact'][net]
            assert len(nodes)==1 and nodes[0].startswith('xtree.')
            return nodes[0][len('xtree.'):]
        expected=[copy.deepcopy(original[0])]+[copy.deepcopy(row)for row in original[1:-1]if old_owner[row[0].lower()]not in tags]
        rename={}
        expected_keys=set()
        for key,name in baseline_keys.items():
            if key[0]in tags:continue
            assert key in candidate_keys
            rename[candidate_keys[key]]=before[name][0];expected_keys.add(key)
        master=[(k,name)for k,name in baseline_keys.items()if k[0]=='a'];assert len(master)==54
        substitutions=[]
        for tag in sorted(tags):
            ports={port_node('a',p):port_node(tag,p)for p in maps['a']}
            assert len(ports)==12
            private_map={}
            def node(n):
                if n in ports:return ports[n]
                if node_owners[n]!={'a'}:return n
                return private_map.setdefault(n,'expected_'+tag+'_'+n)
            made=[]
            for key,name in master:
                wanted=(tag,key[1],key[2]);assert wanted in candidate_keys
                row=copy.deepcopy(before[name]);idx=model_index(row)
                row[0]='X_EXPECTED_'+tag+'_'+name
                row[1:idx]=[node(n)for n in row[1:idx]]
                expected.append(row);made.append(row)
                assert candidate_keys[wanted]not in rename
                rename[candidate_keys[wanted]]=row[0];expected_keys.add(wanted)
            assert len(made)==54
            substitutions.append(dict(tag=tag,source_native_master='a',source_cells=54,source_port_nodes=ports,private_node_map=private_map))
        expected.append(copy.deepcopy(original[-1]))
        assert expected_keys==set(candidate_keys)and len(rename)==len(set(rename.values()))==1674
        assert len(expected[1:-1])==1674 and len({x[0]for x in expected[1:-1]})==1674
        assert set(rename)=={r[0].lower()for r in b[1:-1]}
        b=copy.deepcopy(b)
        for row in b[1:-1]:row[0]=rename[row[0].lower()]
        hbts=[r for r in expected[1:-1]if 'npn13g2'in r]
        emitters=sum(int(next(v.split('=')[1]for v in row if v.startswith('nx=')))for row in hbts)
        assert len(hbts)==589 and emitters==863
        (OUT/'expected-four-master-replacement.spice').write_text('\n'.join(' '.join(x)for x in expected)+'\n')
        result['master_substitutions']=substitutions
        result['native_instance_correspondence']=dict(method='Unchanged macros use original primitive nanometer bbox; four p4 macros use the original a master primitive nanometer bbox and original public topology',pairs=rename,devices=1674)
        result['comparison']=compare(expected,b)
        result['reference_emitters']=emitters
        controls=[]
        for fault in ['missing_device','changed_parameter','wrong_terminal']:
            bad=copy.deepcopy(b)
            if fault=='missing_device':bad.pop(1)
            elif fault=='changed_parameter':
                row=next(v for v in bad[1:-1]if 'npn13g2'in v);j=next(i for i,v in enumerate(row)if v.startswith('nx='));row[j]='nx='+str(int(row[j].split('=')[1])+1)
            else:
                row=next(v for v in bad[1:-1]if 'npn13g2'in v);row[1]='avdd'if row[1]!='avdd'else'avss'
            try:compare(expected,bad)
            except AssertionError as e:controls.append(dict(fault=fault,rejected=True,reason=str(e)))
            else:raise AssertionError('Real compact model fault accepted: '+fault)
        bad=copy.deepcopy(b);left=next(row for row in bad[1:-1]if 'npn13g2'in row);right=next(row for row in bad[1:-1]if 'rppd'in row)
        left[0],right[0]=right[0],left[0]
        try:compare(expected,bad)
        except AssertionError:result['physical_identity_swap_rejected']=True
        else:raise AssertionError('Wrong physical-device correspondence accepted')
        bad=copy.deepcopy(b);row=next(row for row in bad[1:-1]if row[0].startswith('X_EXPECTED_p4_')and 'npn13g2'in row and 'nx=3'in row)
        j=row.index('nx=3');row[j]='nx=1'
        try:compare(expected,bad)
        except AssertionError:result['old_low_drive_parameter_rejected']=True
        else:raise AssertionError('Old low-drive model substituted into new native master')
        assert len(controls)==3
        result.update(status='PASS_NATIVE1674_FOUR_P4_MASTER_SUBSTITUTION_WITH_THREE_FAULTS',controls=controls,
            scope='Exact native compact circuit correspondence to four existing high-drive masters and unchanged remaining cells. This is an intentional circuit change, not equivalence to the rejected low-drive circuit; no waveform or PHY acceptance.')
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
