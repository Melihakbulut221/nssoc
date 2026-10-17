#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read exact repaired OpenDB against actual overflowing GRT regions; never mutate it."""
import argparse,json,os,re,subprocess
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-clock200-geometry'
ODB_SHA='a1ad2156c0757c34ba81db3bc5d0034f3555aa41e49b2dc96d936dca62038ca6'
def native():
    import odb
    path=OUT/'source/run/5-openroad-resizertimingpostcts/soc_top.odb'
    assert sha(path)==ODB_SHA
    db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock();units=block.getDbUnitsPerMicron()
    assert units>0
    def box(b):return [b.xMin()/units,b.yMin()/units,b.xMax()/units,b.yMax()/units]
    def area(b):return max(0,b[2]-b[0])*max(0,b[3]-b[1])
    def overlap(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    def distance(a,b):return (max(0,a[0]-b[2],b[0]-a[2])**2+max(0,a[1]-b[3],b[1]-a[3])**2)**.5
    allinst=[];macros=[]
    for inst in block.getInsts():
        master=inst.getMaster();row=dict(name=inst.getName(),master=master.getName(),bbox_um=box(inst.getBBox()),placement=str(inst.getPlacementStatus()))
        if master.isBlock():
            row['obstruction_layers']=dict(Counter(o.getTechLayer().getName() for o in master.getObstructions()))
            macros.append(row)
        else:allinst.append(row)
    assert len(macros)==20 and len(allinst)>100000
    evidence=json.loads((ROOT/'docs/evidence/corrpre-clock200-native-regions-20261017.json').read_text())
    text=evidence['report']['congestion_regions']['run/1-openroad-globalrouting/congestion.rpt']
    rows=[];allnets=set()
    for part in text.split('violation type: ')[1:]:
        cap,usage,overflow=map(int,re.search(r'capacity:(\d+) usage:(\d+) overflow:(\d+)',part).groups())
        match=re.search(r'bbox = \(([-0-9.]+), ([-0-9.]+)\) - \(([-0-9.]+), ([-0-9.]+)\) on Layer (\S+)',part)
        assert match is not None;bounds=list(map(float,match.groups()[:4]));nets=re.findall(r'net:(\S+)',part);allnets.update(nets)
        expanded=[bounds[0]-50,bounds[1]-50,bounds[2]+50,bounds[3]+50]
        covered=sum(overlap(expanded,m['bbox_um'])for m in macros)
        cellarea=sum(overlap(expanded,x['bbox_um'])for x in allinst)
        available=area(expanded)-covered
        rows.append(dict(direction=part.splitlines()[0],bbox_um=bounds,reported_layer=match.group(5),capacity=cap,usage=usage,overflow=overflow,nets=nets,
            nearest_macros=[dict(name=m['name'],master=m['master'],bbox_um=m['bbox_um'],distance_um=distance(bounds,m['bbox_um'])) for m in sorted(macros,key=lambda m:distance(bounds,m['bbox_um']))[:3]],
            overlapping_macros=[m['name']for m in macros if overlap(bounds,m['bbox_um'])>0],
            within_50um=dict(window_um=expanded,cell_overlap_area_um2=cellarea,macro_overlap_area_um2=covered,window_area_um2=area(expanded),nonmacro_area_um2=available,cell_coverage_of_nonmacro_area=cellarea/available if available>0 else None)))
    assert len(rows)==96 and sum(x['overflow']for x in rows)==142
    topology=[];missing=[]
    for name in sorted(allnets):
        net=block.findNet(name)
        if net is None:missing.append(name);continue
        endpoints=[it.getInst()for it in net.getITerms()];bounds=[box(i.getBBox())for i in endpoints]
        span=[min(b[0]for b in bounds),min(b[1]for b in bounds),max(b[2]for b in bounds),max(b[3]for b in bounds)]if bounds else None
        topology.append(dict(name=name,inst_terminals=len(endpoints),block_terminals=len(list(net.getBTerms())),instance_bbox_union_um=span,macro_endpoints=sorted({i.getName()for i in endpoints if i.getMaster().isBlock()})))
    assert len(topology)>0 and not missing,('GRT net names do not bind exact original database',missing[:10])
    assert sha(path)==ODB_SHA
    result=dict(status='COMPLETE_READ_ONLY_NATIVE_ODB_CONGESTION_LOCALITY_NOT_REPAIR',odb_sha256=ODB_SHA,units_per_um=units,die_bbox_um=box(block.getDieArea()),macros=macros,nonmacro_instances=len(allinst),regions=rows,net_topology=topology,unresolved_nets=missing,
        boundaries='50um windows report geometry coverage only, not routing capacity. Net spans use instance boxes, not pin shapes. GRT reports no per-region layer name; do not assign one. Read-only evidence, no new placement/routing/timing acceptance.')
    (OUT/'native-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        source,proof=reports.restore_report('corrpre-banked-postcts',39030330882,
            '89a9520ad6022ff0112045ab086e57c843ad3c6a2609e31c551179205b3121db',
            '2e3ca4b78ad1feb5251390cf8671b0c8ec187194e222803d1dfa5db481b10953',OUT/'source',
            ['run/5-openroad-resizertimingpostcts/soc_top.odb','run/5-openroad-resizertimingpostcts/state_out.json'])
        assert source['sources_unchanged']and source['repaired_odb_sha256']==ODB_SHA;r['source']=proof
        route=json.loads((ROOT/'docs/evidence/corrpre-clock200-congestion-20261017.json').read_text())
        assert route['report']['native_ndr_screen']['preserved']and route['overflow']==142
        assert route['report']['logic_source']['run']==39031081958
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        with(OUT/'native.log').open('w')as log:
            code=subprocess.call([str(app),'openroad','-exit','-python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if code:print((OUT/'native.log').read_text()[-16000:],flush=True)
        assert code==0
        r['geometry']=json.loads((OUT/'native-geometry.json').read_text());r['status']=r['geometry']['status']
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
