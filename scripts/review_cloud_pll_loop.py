#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inventory the exact failed-acquisition PLL's physical device and RC sources."""
import collections,hashlib,json,math,os,tarfile
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-loop-source'
PARENT_SHA='91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc'
SUMMARY_SHA='781a1cafebb529f4cfb82ff861937898e2425ba0429157097c02553188610da4'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'

def records(text):
    rows=[]
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('*'):continue
        if line.startswith('+'):
            assert rows;rows[-1]+=line[1:].split()
        else:rows.append(line.split())
    assert rows[0][0].lower()=='.subckt' and rows[-1][0].lower()=='.ends'
    assert sum(r[0].lower()=='.subckt' for r in rows)==1
    assert len({r[0].lower() for r in rows[1:-1]})==len(rows)-2
    assert all(r[0][0].lower() in ('x','r','c') for r in rows[1:-1])
    return rows

def inventory(text):
    rows=records(text);ports=rows[0][2:];devices=[];wires=[];uf={}
    def root(n):
        uf.setdefault(n,n)
        while uf[n]!=n:uf[n]=uf[uf[n]];n=uf[n]
        return n
    for row in rows[1:-1]:
        if row[0][0].lower()=='x':
            first=next((i for i,v in enumerate(row) if '=' in v),len(row));assert first>=4
            model=row[first-1];nodes=row[1:first-1];parameters=row[first:]
            assert '=' not in model and all('=' in p for p in parameters)
            devices.append(dict(instance=row[0],model=model,nodes=nodes,parameters=parameters,record=' '.join(row)))
            for n in nodes:root(n)
        else:
            assert len(row)==4;value=float(row[3]);assert math.isfinite(value) and value>=0
            wires.append(dict(instance=row[0],kind=row[0][0].upper(),nodes=row[1:3],value=value,record=' '.join(row)))
            for n in row[1:3]:root(n)
            if row[0][0].lower()=='r':uf[root(row[1])]=root(row[2])
    assert len(devices)==845 and len(wires)==8648 and len(ports)==17
    for n in ports:root(n)
    components=collections.defaultdict(list)
    for n in uf:components[root(n)].append(n)
    groups=sorted((sorted(ns) for ns in components.values()),key=lambda ns:ns[0])
    by_node={n:i for i,ns in enumerate(groups) for n in ns}
    public={i:[n for n in ports if n in ns] for i,ns in enumerate(groups)}
    for d in devices:
        d['resistor_components']=[by_node[n] for n in d['nodes']]
        d['public_ports_by_terminal']=[public[by_node[n]] for n in d['nodes']]
    for c in wires:
        c['resistor_components']=[by_node[n] for n in c['nodes']]
    return dict(top=rows[0][1],ports=ports,device_count=len(devices),wire_count=len(wires),device_models=dict(collections.Counter(d['model'] for d in devices)),device_name_groups=dict(collections.Counter('_'.join(d['instance'].split('_')[:2]) for d in devices)),wire_kinds=dict(collections.Counter(w['kind'] for w in wires)),devices=devices,public_port_components={p:by_node[p] for p in ports},resistor_components=[dict(index=i,nodes=ns,public_ports=public[i]) for i,ns in enumerate(groups)],wire_inventory_sha256=hashlib.sha256(json.dumps(wires,sort_keys=True).encode()).hexdigest())

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,scope='Read-only exact845device/8648wire source inventory and resistor-component mapping to guide physical PLL repair. No circuit change, waveform rerun, qualified RC, device safety, PVT or lock acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        fetch(BASE+'cloud-results-38813902351-1-pll-vbic-acquisition/pll-vbic-acquisition-38813902351-1.summary.json',SUMMARY_SHA,OUT/'acquisition-summary.json')
        observed=json.loads((OUT/'acquisition-summary.json').read_text())
        assert observed['status']=='COMPLETE_PATCHED_ACTUAL845_ONE_US_MEASUREMENT_NOT_PHY_ACCEPTANCE'
        assert observed['source_receipt']['parent_sha256']==PARENT_SHA and observed['protected_inputs_unchanged']
        assert observed['original_gate_passed'] is False and observed['capture']['end_s']==1e-6
        result['acquisition_source']=dict(run=38813902351,summary_sha256=SUMMARY_SHA,parent_sha256=PARENT_SHA)
        windows=[w for w in observed['independent_acquisition']['rolling_windows'] if any(abs(w['interval_s'][0]-s)<1e-18 for s in (8e-7,9e-7))]
        assert len(windows)==2
        result['mandatory_windows']=[dict(w,frequency_error_ppm=(w['frequency_hz']/1e8-1)*1e6) for w in windows]
        packed=OUT/'source.tar.gz';archive_sha='ff8837dce9298abd8cb649eceb5b86dcd8e48454d7175002096b4b5b80a4205b'
        fetch(BASE+'cloud-results-38672085461-1-pll-pfd-layout/pfd94-layout-38672085461-1.tar.gz',archive_sha,packed)
        assert packed.stat().st_size==11295468
        prefix='hw/soc/out/cloud-pfd-layout/'
        with tarfile.open(packed) as tar:
            entries={m.name:m for m in tar.getmembers()}
            assert len(entries)==len(tar.getmembers())
            for name in ('result.json','parent845.spice','graph-diagnostic.json','integrated/result.json','integrated/schematic.cir'):
                m=entries[prefix+name];assert m.isfile()
                p=OUT/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
        packed.unlink()
        assert sha(OUT/'source/result.json')=='22cae097bdb7c2a3fa77abaad4ebeff772fb08c1769c1e4fc10664f90f1e6f35'
        parent=json.loads((OUT/'source/result.json').read_text())
        assert parent['status']=='PASS_ACTUAL845_PARENT_COMPONENTS_REFERENCE_PLANES_AND_EXACT_INTRINSIC_GRAPH_NOT_ELECTRICAL_ACCEPTANCE'
        assert parent['counts']==dict(devices=845,wires=8648) and parent['candidate_sha256']==PARENT_SHA
        assert sha(OUT/'source/parent845.spice')==PARENT_SHA
        assert sha(OUT/'source/graph-diagnostic.json')==parent['graph_diagnostic_sha256']
        result['parent_source']=dict(run=38672085461,archive_sha256=archive_sha,summary_sha256=sha(OUT/'source/result.json'),parent_sha256=PARENT_SHA)
        result['inventory']=inventory((OUT/'source/parent845.spice').read_text())
        result['native_composition_evidence']={k:parent[k] for k in ('counts','component_preservation','exact_graph','pfd_reference_planes')}
        assert sha(OUT/'source/parent845.spice')==PARENT_SHA
        result['status']='COMPLETE_EXACT_PLL_DEVICE_AND_RESISTOR_COMPONENT_DIAGNOSIS_NOT_REPAIR'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':main()
