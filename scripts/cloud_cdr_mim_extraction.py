#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure actual native MIM extraction with/without intrinsic device masks.

Uses the three real PD394 primitive sizes, never a substitute ideal capacitor.
No net-coupling subtraction or full-parent capacitance acceptance is inferred.
"""
import argparse,json,os,shutil,subprocess,tarfile
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-mim-extraction'
TOP='nssoc_cdr_retimed_pd394_layout_v1'
METALS=(8,10,30,50,67,126,134);VIAS=(19,29,49,66,125,133)

def generate():
    import pya
    G=OUT/'inputs/parent/layout'/(TOP+'.gds');L=pya.Layout();L.read(str(G));assert L.dbu==.001
    geometry=json.loads((OUT/'inputs/wire/device-locations01.json').read_text());by={d['native_id']:d for d in geometry['devices']}
    binding=json.loads((ROOT/'docs/evidence/cdr-retimed-binding-pass-20261018.json').read_text())['report']['binding']
    selected={}
    for d in binding['devices']:
        if d['model']!='cap_cmim':continue
        dims=tuple(str(Decimal(d['native_parameters'][k]).normalize())for k in ('w','l'))
        selected.setdefault(dims,by[d['native_id']])
    assert set(selected)=={('3.6','3.6'),('4.8','4.8'),('4E+1','4E+1')}
    cases=[]
    for dims,d in sorted(selected.items()):
        cell=L.cell(d['pcell']['cell']);assert cell is not None and not list(cell.each_inst())
        top=pya.Region(cell.begin_shapes_rec(L.layer(126,0))).merged();bottom=pya.Region(cell.begin_shapes_rec(L.layer(67,0))).merged()
        shape_record=dict(native_id=d['native_id'],cell=cell.name,top=dict(polygons=top.count(),area_dbu2=top.area(),bbox=str(top.bbox())),bottom=dict(polygons=bottom.count(),area_dbu2=bottom.area(),bbox=str(bottom.bbox())))
        with (OUT/'plate-geometry.jsonl').open('a')as stream:stream.write(json.dumps(shape_record)+'\n')
        assert (top^pya.Region(top.bbox())).is_empty()and(bottom^pya.Region(bottom.bbox())).is_empty(),shape_record
        shape_record['both_plate_unions_equal_filled_rectangle']=True
        # Real source plate drawing can contain slots. Pick an interior rectangle
        # from that unchanged drawing, never fill a slot or probe its bounding-box hole.
        rects=[p.bbox()for p in top.decompose_trapezoids_to_region().each()if p.area()==p.bbox().area()and p.bbox().width()>2 and p.bbox().height()>2]
        assert rects,shape_record
        plus=max(rects,key=lambda b:b.area()).center();bb=bottom.bbox();minus=pya.Point(bb.left+200,bb.center().y)
        for point,region in ((plus,top),(minus,bottom)):
            witness=pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))
            assert (witness-region).is_empty(),(shape_record,str(point))
        tag='mim_'+str(Decimal(dims[0])).replace('.','p').replace('+','')
        folder=OUT/'cases'/tag;folder.mkdir(parents=True)
        for variant in ('wire_only','mim_aware','mim_explicit_model'):
            dst=pya.Layout();dst.dbu=L.dbu;c=dst.create_cell('mim_probe')
            if variant!='wire_only':c.copy_tree(cell)
            else:
                for layer in METALS+VIAS:c.shapes(dst.layer(layer,0)).insert(pya.Region(cell.begin_shapes_rec(L.layer(layer,0))))
            for layer in METALS+VIAS:
                assert(pya.Region(c.begin_shapes_rec(dst.layer(layer,0)))^pya.Region(cell.begin_shapes_rec(L.layer(layer,0)))).is_empty()
            path=folder/(variant+'.gds')
            if variant=='mim_explicit_model':shutil.copyfile(folder/'mim_aware.gds',path)
            else:dst.write(str(path))
            cases.append(dict(tag=tag,variant=variant,native_id=d['native_id'],source_cell=cell.name,w_um=dims[0],l_um=dims[1],gds=str(path.relative_to(OUT)),gds_sha256=sha(path),plus_dbu=[plus.x,plus.y],minus_dbu=[minus.x,minus.y],all_original_metal_vias_equal=True,layers=[dict(layer=str(dst.get_info(i)),area_dbu2=pya.Region(c.begin_shapes_rec(i)).area())for i in dst.layer_indexes()if not pya.Region(c.begin_shapes_rec(i)).is_empty()]))
    (OUT/'cases.json').write_text(json.dumps(dict(cases=cases,source_gds_sha256=sha(G)),indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');a=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT;r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_parent_capacitance_corrected=False,full_phy_accepted=False,closed_loop=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,cwd,log,env=None):
        with log.open('w')as stream:rc=subprocess.call(list(map(str,command)),cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        if rc:print(log.read_text(errors='replace')[-12000:],flush=True)
        assert rc==0,(str(log),rc)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-retimed-wire-inputs-pass-20261018.json').read_text())
        selected=['parent/layout/'+TOP+'.gds','wire/device-locations01.json']
        prior,proof=reports.restore_report('cdr-retimed-wire-inputs',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'inputs',selected)
        assert prior['status']==pin['status']and prior['sources_unchanged'];r['physical_source']=proof
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        run([app,'python',Path(__file__),'--generate'],ROOT,OUT/'generate.log')
        r['generated']=json.loads((OUT/'cases.json').read_text());save()
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz';fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(rt,filter='data')
        packed.unlink();manifest=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        lib=rt/'runtime/lib';tech=rt/'tech';env={k:v for k,v in os.environ.items()if k not in ('PYTHONHOME','PYTHONPATH','PYTHONEXECUTABLE','LD_PRELOAD')};env['CAD_ROOT']=str(lib)
        private=OUT/'ngspice-mim-tech';shutil.copytree(tech,private)
        baseline=(tech/'ihp-sg13g2-extract.tech').read_text()
        removed=[' defaultareacap     *mimcap metal5 1500\n',' defaultperimeter   *mimcap metal5 40\n']
        expected=baseline
        for line in removed:assert expected.count(line)==1;expected=expected.replace(line,'')
        (private/'ihp-sg13g2-extract.tech').write_text(expected)
        assert all(sha(private/p.name)==sha(p)for p in tech.iterdir()if p.is_file()and p.name!='ihp-sg13g2-extract.tech')
        r['private_ngspice_tech']=dict(original_sha256=sha(tech/'ihp-sg13g2-extract.tech'),private_sha256=sha(private/'ihp-sg13g2-extract.tech'),removed_cdl_device_estimate_lines=removed,all_other_technology_bytes_unchanged=True,scope='Used only with explicit cap_cmim subcircuit in ngspice() style; not approved for CDL or capacitor-only extraction.')
        legacy=json.loads((ROOT/'docs/evidence/cdr-mim-mask-comparison-pass-20261018.json').read_text())['report']
        def caps_key(rows):return sorted((tuple(sorted(row[1:3])),str(parser.number(row[3]).normalize()))for row in rows)
        legacy_cases={(x['source']['tag'],x['source']['variant']):x for x in legacy['cases']}
        r['cases']=[]
        for case in r['generated']['cases']:
            G=OUT/case['gds'];assert sha(G)==case['gds_sha256'];dest=G.parent/case['variant'];dest.mkdir()
            selected_tech=private if case['variant']=='mim_explicit_model'else tech
            if case['variant']=='mim_explicit_model':assert sha(G)==sha(G.parent/'mim_aware.gds')
            lines=['puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"',f'cd {{{dest}}}','drc off',f'gds read {{{G}}}','load mim_probe','select top cell']
            for index,(name,point,metal)in enumerate([('PLUS',case['plus_dbu'],'metal6'),('MINUS',case['minus_dbu'],'metal5')],1):
                x,y=[f'{v/1000:.3f}um'for v in point];lines +=[f'box values {x} {y} {x} {y}',f'label {name} center {metal}',f'port {name} make {index}',f'port {name} class inout',f'port {name} use signal']
            lines +=['save mim_probe','extract unique all','extract style ngspice()','extract all','ext2spice lvs','ext2spice merge none','ext2spice global off','ext2spice cthresh 0','ext2spice rthresh 0','ext2spice extresist off','ext2spice -o extracted.spice','puts NSSOC_MIM_EXTRACTION_COMPLETE','quit -noprompt']
            script=dest/'extract.tcl';script.write_text('\n'.join(lines)+'\n')
            run(['/usr/bin/tclsh8.6',lib/'magic/tcl/magic.tcl','-dnull','-noconsole','-rcfile',selected_tech/'ihp-sg13g2.magicrc',script],dest,dest/'native.log',env)
            log=(dest/'native.log').read_text();assert log.count('NSSOC_MIM_EXTRACTION_COMPLETE')==1
            assert not any(s in log for s in ('Error in extracting node','Unknown layer','Missing terminal','Error: Node with no area'))
            text=(dest/'extracted.spice').read_text();rows=parser.statements(text);devices=[x for x in rows if x[0][0].lower()=='x'];caps=[x for x in rows if x[0][0].lower()=='c']
            if case['variant']!='wire_only':
                assert len(devices)==1 and devices[0][3]=='cap_cmim',devices
                params=dict(x.split('=')for x in devices[0][4:]);assert parser.number(params['w'])==Decimal(case['w_um'])*Decimal('1e-6')and parser.number(params['l'])==Decimal(case['l_um'])*Decimal('1e-6')
                assert set(devices[0][1:3])=={'PLUS','MINUS'},devices
            else:assert not devices
            assert all(len(x)==4 and parser.number(x[3])>=0 for x in caps)
            mutual=sum((parser.number(x[3])for x in caps if set(x[1:3])=={'PLUS','MINUS'}),Decimal(0))
            if case['variant']!='mim_explicit_model':
                old=legacy_cases[case['tag'],case['variant']]
                assert caps_key(caps)==caps_key(old['regular_capacitors'])and devices==old['native_devices'],'Unchanged baseline extraction drifted'
            ground={name:str(sum((parser.number(x[3])for x in caps if set(x[1:3])=={name,'sub'}),Decimal(0)))for name in ('PLUS','MINUS')}
            r['cases'].append(dict(source=case,native_devices=devices,regular_capacitors=caps,regular_ground_capacitance_f=ground,regular_plus_minus_capacitance_f=str(mutual),native_intrinsic_capacitor_count=len(devices),technology_sha256=sha(selected_tech/'ihp-sg13g2-extract.tech'),outputs={p.name:sha(p)for p in dest.iterdir()if p.is_file()}));save()
        assert len(r['cases'])==9
        assert all(sha(OUT/'inputs'/n)==prior['outputs'][n]for n in selected)and all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        assert (private/'ihp-sg13g2-extract.tech').read_text()==expected
        r['sources_unchanged']=True;r['status']='PASS_MIM_EXPLICIT_MODEL_ESTIMATE_RETIREMENT_PILOT_REQUIRES_FULL_PARENT_VALIDATION'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
