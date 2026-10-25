#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind actual XOR core/public planes and preserve exact native RC source methods."""
import argparse,copy,hashlib,json,os,re,subprocess,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-rc-inputs'
TOP='nssoc_cdr_xor_load_parent_v2';CORE='nssoc_cdr_xor_load_core_layout_v2'
def native():
    import pya
    P=OUT/'parent';A=P/'integrated';D=P/'physical/lvs_flat'
    r=json.loads((A/'result.json').read_text());m=json.loads((P/'core/layout/result.json').read_text())
    audit=json.loads((D/'audit.json').read_text());assert audit['status']=='PASS within comparison scope'
    roots=[c for c in audit['circuits']if c['layout']==TOP];assert len(roots)==1and roots[0]['layout_devices_recursive']==roots[0]['schematic_devices_recursive']==54
    L=pya.Layout();L.read(str(A/'flat.gds'));T=L.cell(TOP);assert T is not None and L.dbu==.001
    native=pya.LayoutVsSchematic();native.read(str(D/'result.lvsdb'))
    full=pya.Region(T.begin_shapes_rec(L.layer(134,0))).merged()
    candidates=[i for i in native.layer_indexes()if(native.layer_by_index(i)^full).is_empty()];assert len(candidates)==1,candidates
    plane=native.layer_by_index(candidates[0]);insts=list(T.each_inst());assert len(insts)==1 and insts[0].cell.name==CORE
    def point(b):
        f=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',b)));assert len(f)==4
        return pya.DBox(*f).to_itype(L.dbu).center()
    rows=[]
    for port,b in m['ports'].items():
        pt=insts[0].trans*point(b);n=native.probe_net(plane,pt);assert n is not None
        rows.append(dict(label='A_core_'+port,point_dbu=[pt.x,pt.y],metal=134,logical_net=r['core_port_map'][port],native_cluster=n.cluster_id))
    for port,b in r['ports'].items():
        pt=point(b);n=native.probe_net(plane,pt);assert n is not None
        rows.append(dict(label='P_'+port,point_dbu=[pt.x,pt.y],metal=134,logical_net=port,native_cluster=n.cluster_id))
    assert len(rows)==22 and len({x['label']for x in rows})==22
    def validate(rows):
        groups={}
        for x in rows:groups.setdefault(x['logical_net'],set()).add(x['native_cluster'])
        assert len(groups)==10 and all(len(v)==1for v in groups.values())
        assert len(set.union(*groups.values()))==10,'Different logical signals share a native net'
    validate(rows)
    controls=[]
    for label in ['A_core_bn','A_core_bp','A_core_op','A_core_on']:
        changed=copy.deepcopy(rows);x=next(x for x in changed if x['label']==label)
        x['logical_net']={'dp':'dn','dn':'dp','qp':'qn','qn':'qp'}[x['logical_net']]
        try:validate(changed)
        except AssertionError:controls.append(dict(label=label,rejected=True))
        else:raise AssertionError('Accepted wrong native plane map')
    # Native LEF reader observation; no LEF signoff from parsing alone.
    F=pya.Layout();F.read(str(A/(TOP+'.lef')));cell=F.cell(TOP);assert cell is not None
    lef=dict(native_read_succeeded=True,bbox_um=str(cell.dbbox()),layers=[str(F.get_info(i))for i in F.layer_indices()],qualified=False)
    result=dict(status='PASS_NATIVE54_XOR_PARENT22_PLANES_AND_FOUR_MAPPING_CONTROLS',anchors=rows,controls=controls,lef_reader=lef,
        inputs={str(p):sha(p)for p in [Path(__file__),A/'result.json',A/'flat.gds',D/'result.lvsdb',D/'audit.json',P/'core/layout/result.json',A/(TOP+'.lef')]},qualified_pex=False)
    (OUT/'native-planes.json').write_text(json.dumps(result,indent=2)+'\n')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-xor-parent-physical-pass-20261017.json').read_text())
        prior,proof=reports.restore_report('cdr-xor-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',list(pin['report']['outputs']))
        assert prior==pin['report']and prior['sources_unchanged'];r['physical_source']=proof
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text());packed=OUT/'methods.tar.gz'
        fetch(spec['method_archive']['url'],spec['method_archive']['sha256'],packed)
        folder=OUT/'original-methods';folder.mkdir();texts={}
        with tarfile.open(packed)as tar:
            for name,digest in spec['methods'].items():
                m=tar.getmember(name);assert m.isfile();data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==digest
                p=folder/Path(name).name;assert not p.exists();p.write_bytes(data);texts[p.name]=dict(sha256=digest,text=data.decode())
        packed.unlink();r['original_extraction_methods']=texts
        r['physical_core_reference']=(OUT/'parent/core/layout/schematic.cir').read_text()
        r['physical_parent_reference']=(OUT/'parent/integrated/schematic.cir').read_text()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466';save()
        with (OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if rc:print((OUT/'native.log').read_text()[-16000:],flush=True)
        assert rc==0
        r['native_planes']=json.loads((OUT/'native-planes.json').read_text())
        assert all(sha(OUT/'parent'/n)==v for n,v in prior['outputs'].items())
        assert all(sha(folder/n)==v['sha256']for n,v in texts.items())
        r['status']='PASS_NATIVE_XOR_PLANES_AND_PINNED_EXTRACTION_INPUTS_REQUIRES_RC_AND_WAVES'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
