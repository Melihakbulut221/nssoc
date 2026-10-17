#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the actual assembled162-device tree to its complete native metal RC graph.

All native execution occurs on hosted Actions. No concatenation of child RC,
ideal intermacro aliases, substrate-resistance qualification or PHY acceptance.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from run_cloud_tx_layout_repair import ROOT, fetch, sha

PORTS = 'd0p d0n d1p d1n d2p d2n d3p d3n sap san sbp sbn sp sn mp mn avdd avss sub ra rb mr'.split()
TOP = 'nssoc_tx_tree4_core_v1'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--placement-profile',choices=('baseline','compact_vertical','compact_m5_supply','compact_edge_supply','compact_return_strap'),default='baseline')
    profile=parser.parse_args().placement_profile
    tree = json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
    selected=tree if profile=='baseline' else tree['placement_variants'][profile]
    receipt = selected['verified_extraction']
    assert receipt.get('placement_profile','baseline')==profile
    expected_counts=dict(devices=162,R=receipt['resistors'],C=receipt['capacitors'])
    assert (receipt['devices'], receipt['ports'], receipt['conductors'], receipt['probes']) == (162,22,41,322)
    if profile=='baseline':assert expected_counts==dict(devices=162,R=11907,C=7847)
    assert expected_counts['R']>0 and expected_counts['C']>0
    spec = json.loads((ROOT/'docs/evidence/pcie-tx-cloud-composition-input-20261013.json').read_text())
    layout = json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
    out = ROOT/'hw/soc/out/cloud-tx-tree-assembly'
    assert not out.exists()
    out.parent.mkdir(parents=True,exist_ok=True)
    archive = out.parent/'tree-composition-input.tar.gz'
    result = dict(status='RUNNING',placement_profile=profile,source=receipt,qualified_pex=False,serial_phy_complete=False,
                  native_transient_accepted=False,adopted=False,
                  scope='Actual162-device four-input CML core and complete source-pinned metal RC graph, including real intermacro conductors. No body spreading resistance, RF qualification, loaded transient, full32:1/four-lane PHY or mainchip acceptance.')
    adaptations = {}

    def restore(pin,directory):
        fetch(pin['url'],pin['sha256'],archive)
        if 'bytes' in pin: assert archive.stat().st_size == pin['bytes']
        with tarfile.open(archive) as tar: tar.extractall(directory,filter='data')
        archive.unlink()

    def adapt(source,path,replacements):
        original=source
        changes=[]
        for before,after,count in replacements:
            assert source.count(before)==count,(path.name,before,source.count(before),count)
            source=source.replace(before,after)
            changes.append(dict(before=before,after=after,count=count))
        path.write_text(source)
        original_path=path.with_suffix(path.suffix+'.original')
        original_path.write_text(original)
        adaptations[str(path.relative_to(out))]=dict(original_sha256=sha(original_path),adapted_sha256=sha(path),changes=changes)

    def run(command,label):
        log=out/(label+'.log')
        with log.open('w') as stream:
            code=subprocess.call([str(x) for x in command],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-12000:],flush=True)
            raise RuntimeError(f'{label}: exit {code}')

    try:
        restore(receipt,ROOT)
        extraction_path=out/'extraction-result.json'
        assert sha(extraction_path)==receipt['summary_sha256']
        extraction=json.loads(extraction_path.read_text())
        assert extraction['status']=='PASS_ACTUAL_NATIVE_RC_GRAPH_AND_13_FAULT_CONTROLS_REQUIRES_WAVEFORMS'
        assert extraction['native_geometry_census']==receipt['native_geometry_census']
        assert extraction.get('placement_profile','baseline')==profile
        assert extraction['audit']['actual_exported_resistors']==expected_counts['R']
        assert extraction['audit']['actual_exported_capacitors']==expected_counts['C']
        protected={str(q):sha(q) for sub in ('layout','physical','wire96') for q in (out/sub).rglob('*') if q.is_file()}
        restore(layout['receipt'],ROOT)
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        electrical=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text())
        inputs=ROOT/'tree-composition-model-inputs';inputs.mkdir()
        restore(electrical['receipt'],inputs)
        manifest=json.loads((inputs/'manifest.json').read_text())
        assert all(sha(inputs/n)==v['sha256'] for n,v in manifest['files'].items())
        modeldir=ROOT/'pdk/libs.tech/ngspice/models'
        modeldir.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(inputs/'models',modeldir)
        helper=ROOT/'hw/soc/out/pcie-tail115-connected570-source-20261006/compose_source01.py'
        helper.parent.mkdir(parents=True,exist_ok=True)
        parser=spec['helpers']['composition_parser'];fetch(parser['url'],parser['sha256'],helper)
        binding=out/'binding96';binding.mkdir()
        fetch(spec['binding_archive']['url'],spec['binding_archive']['sha256'],archive)
        with tarfile.open(archive) as tar:
            for name,digest in spec['binding_methods'].items():
                path=binding/Path(name).name
                path.write_bytes(tar.extractfile(name).read());assert sha(path)==digest
                source=path.read_text()
                replacements=[("'physical92/","'physical/",source.count("'physical92/"))]
                if path.name=='export01.py':
                    replacements += [('nssoc_tx_mux2_passive_topmetal_layout_v1',TOP,1),('c.pin_count()==12','c.pin_count()==22',1),('len(rows)==54','len(rows)==162',1)]
                elif path.name=='build-devices01.py':
                    replacements += [
                        ("Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')","R/'pdk'",1),
                        ('dict(npn13G2=19,rppd=8,ptap1=27)','dict(npn13G2=57,rppd=24,ptap1=81)',1),
                        ("{'ap','an','bp','bn','sp','sn','op','on','avdd','avss','sub','iref'}and len(ports)==12",repr(set(PORTS))+'and len(ports)==22',1),
                        ('set(range(1,55))','set(range(1,163))',1),
                        ('nssoc_tx_mux54_compact_v1','nssoc_tx_tree162_compact_v1',2),
                        ('mux54-compact01.spice','tree162-compact01.spice',1),
                        ('PASS_NATIVE54_MODEL_AND_TERMINAL_BINDING','PASS_NATIVE162_MODEL_AND_TERMINAL_BINDING',1),
                        ('Twenty-seven actual2x2um','Eighty-one actual2x2um',1)]
                else: raise AssertionError(name)
                adapt(source,path,replacements)
        archive.unlink()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==layout['runtime_sha256']
        run([app,'python',binding/'export01.py'],'export-native-tree-devices')
        run([sys.executable,binding/'build-devices01.py'],'bind-native-tree-models')
        wire=out/'wire96'
        source=(wire/'compose49.py').read_text()
        replacements=[("B/'audit48.json'","B/'audit.json'",1),
            ('PASS_NATIVE54_MODEL_AND_TERMINAL_BINDING','PASS_NATIVE162_MODEL_AND_TERMINAL_BINDING',1),
            ('mux54-compact01.spice','tree162-compact01.spice',2),
            ('mux54-wire01.spice','tree162-wire01.spice',1),
            ('nssoc_tx_mux54_wire_v1','nssoc_tx_tree162_wire_v1',3),
            ('len(rows)==54','len(rows)==162',1),('devices=54','devices=162',1),
            ('SOURCE_ONLY_NATIVE54_WITH_DISTRIBUTED_METAL_RC','SOURCE_ONLY_NATIVE162_WITH_DISTRIBUTED_METAL_RC',1),
            ('Fifty-four native LVS devices','One hundred sixty-two native LVS devices',1),
            ('Exact fifty-four native devices with finite physical contacts,112actual metal reference points,17wire conductors','Exact162 native devices with81finite physical contacts,300intrinsic metal reference points and22public pins,41wire conductors',1)]
        adapt(source,wire/'compose-tree.py',replacements)
        run([sys.executable,wire/'compose-tree.py'],'compose-native-tree-wires')
        report=json.loads((wire/'composition01.json').read_text())
        assert report['status']=='SOURCE_ONLY_NATIVE162_WITH_DISTRIBUTED_METAL_RC'
        assert report['counts']==expected_counts
        # Independent output reparse, all device values and every source RC row,
        # plus real malformed output files. Never trust only generation counts.
        source=(wire/'check-compose98.py').read_text()
        replacements=[('mux54-wire01.spice','tree162-wire01.spice',2),
            ('nssoc_tx_mux54_wire_v1','nssoc_tx_tree162_wire_v1',2),
            ('len(devices)==54','len(devices)==162',1),
            ('dict(devices=54,R=229,C=301)',repr(expected_counts),1),
            ("assert'nx=1'in lines[i];lines[i]=lines[i].replace('nx=1','nx=2')","f=lines[i].split();j=next(j for j,v in enumerate(f) if v.startswith('nx='));f[j]='nx='+str(int(f[j].split('=')[1])+1);lines[i]=' '.join(f)+'\\n'",1),
            ("f[2]='iref'","f[2]='mr'",1),
            ('PASS_ALL54_NATIVE_DEVICES530_WIRES_AND_SIX_COMPOSITION_FAULTS',f"PASS_ALL162_NATIVE_DEVICES{expected_counts['R']+expected_counts['C']}_WIRES_AND_SIX_COMPOSITION_FAULTS",1)]
        adapt(source,wire/'check-tree-composition.py',replacements)
        run([sys.executable,wire/'check-tree-composition.py'],'check-tree-composition-faults')
        controls=json.loads((wire/'composition-controls98.json').read_text())
        assert len(controls['controls'])==6 and controls['counts']==report['counts']
        # Recover the original schematic connectivity independently by collapsing
        # only actual extracted resistor edges, never capacitors or ideal aliases.
        sys.path.insert(0,str(ROOT/'scripts'))
        import build_pcie_local_vco_hybrid_v6 as h
        import networkx as nx
        from collections import Counter
        native=json.loads((binding/'binding01.json').read_text())
        anchors=json.loads((wire/'anchors08.json').read_text())
        by_terminal={(r['device'],r['terminal']):r for r in anchors['rows']}
        assert len(by_terminal)==462
        records=h.statements((wire/'tree162-wire01.spice').read_text())
        devices={r[0]:r for r in records[1:-1] if r[0].startswith('X')}
        assert len(devices)==162 and len(records[1:-1])==sum(expected_counts.values())
        assert len({r[0].lower() for r in records[1:-1]})==len(records[1:-1])
        graph=nx.Graph();graph.add_edges_from((r[1],r[2]) for r in records[1:-1] if r[0].startswith('R'))
        components=list(nx.connected_components(graph));assert len(components)==41
        groups={node:i for i,c in enumerate(components) for node in c}
        owner={};counts=Counter()
        def claim(node,net):
            component=groups[node]
            if component in owner: assert owner[component]==net,(node,net,owner[component])
            owner[component]=net
        for d in native['devices']:
            fields=devices[d['instance']]
            for i,terminal in enumerate(d['compact_model_order'],1):
                anchor=by_terminal[d['native_id'],terminal]
                assert anchor['native_net']==d['native_nodes'][terminal]
                counts[anchor['disposition']]+=1
                if anchor['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE':
                    claim(fields[i],anchor['native_net'])
                else:
                    assert fields[i]==native['node_map'][anchor['native_net']]
                    assert fields[i] not in groups
        for port in native['native_ports']:claim(port,port)
        assert set(native['native_ports'])==set(PORTS)
        assert len(owner)==41 and len(set(owner.values()))==41
        assert counts==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=300,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=162)
        topology=dict(status='PASS_ALL_PHYSICAL_RESISTOR_COMPONENTS_RECOVER_NATIVE_SCHEMATIC_NETS',
            components=41,public_ports=22,terminal_counts=dict(counts),
            component_native_net={str(k):v for k,v in owner.items()},
            no_intermacro_ideal_alias=True,no_duplicate_child_rc=True)
        (wire/'tree-topology-check.json').write_text(json.dumps(topology,indent=2)+'\n')
        interface_helper=wire/'bind-tree-interface.py'
        interface_helper.write_text("# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\n# SPDX-License-Identifier: Apache-2.0\nfrom pathlib import Path\nimport json,hashlib\nimport pya\nB=Path(__file__).resolve().parent;P=B.parent\nlayout=json.loads((P/'layout/result.json').read_text())\nsource=json.loads((P/'wire96/native05/result.json').read_text())\nlocations=json.loads((P/'wire96/device-locations01.json').read_text())\nanchors=json.loads((P/'wire96/anchors08.json').read_text())\nbinding=json.loads((P/'binding96/binding01.json').read_text())\ng=pya.Layout();g.read(str(P/'layout/nssoc_tx_tree4_core_v1.gds'))\nl=pya.LayoutVsSchematic();l.read(str(P/'physical/lvs/result.lvsdb'))\nlayer=l.layer_by_index(source['native_layer_mapping']['134'])\ndx,dy=layout['origin_translation_um']\ndef shifted(box):\n b=pya.DBox.from_s(box);return pya.DBox(b.left+dx,b.bottom+dy,b.right+dx,b.top+dy)\ndef probe(endpoint):\n macro,port=endpoint.split('.');box=shifted(layout['placement'][macro]['ports'][port]);p=box.center()\n point=pya.Point(round(p.x/g.dbu),round(p.y/g.dbu));net=l.probe_net(layer,point)\n assert net is not None\n return dict(endpoint=endpoint,point_dbu=[point.x,point.y],native_net=net.name,native_cluster=net.cluster_id)\nfinal_box=shifted(layout['placement']['f']['bbox_um'])\ndevices={d['native_id']:d for d in locations['devices']}\nresult=dict(status='PASS_REAL_INTERMACRO_ENDPOINTS_TO_ALL_FINAL_HBT_BASES',modes={'compact':{},'wire':{}},references={},ideal_aliases_inserted=False)\nfor label,endpoint in [('ap','a.op'),('an','a.on'),('bp','b.op'),('bn','b.on')]:\n a,b=probe(endpoint),probe('f.'+label);assert a['native_cluster']==b['native_cluster']\n rows=[]\n for r in anchors['rows']:\n  if r['model']!='npn13G2' or r['terminal']!='B' or r['native_cluster']!=b['native_cluster']:continue\n  box=pya.DBox.from_s(devices[r['device']]['pcell']['bbox'])\n  if (box & final_box)!=box:continue\n  assert r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE'\n  rows.append(r)\n assert len(rows)==3 and len({r['device']for r in rows})==3\n result['references'][label]=dict(endpoints=[a,b],intrinsic_terminals=rows)\n result['modes']['compact'][label]=['xtree.'+binding['node_map'][b['native_net']].lower()]\n result['modes']['wire'][label]=sorted('xtree.'+r['wire_anchor'].lower() for r in rows)\nassert len({r['endpoints'][0]['native_cluster']for r in result['references'].values()})==4\nresult['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),P/'layout/result.json',P/'layout/nssoc_tx_tree4_core_v1.gds',P/'physical/lvs/result.lvsdb',P/'wire96/native05/result.json',P/'wire96/device-locations01.json',P/'wire96/anchors08.json',P/'binding96/binding01.json']}\n(B/'tree-interface-probes.json').write_text(json.dumps(result,indent=2)+'\\n');print(result['status'])\n")
        run([app,'python',interface_helper],'bind-real-final-interface-probes')
        interface=json.loads((wire/'tree-interface-probes.json').read_text())
        assert interface['status']=='PASS_REAL_INTERMACRO_ENDPOINTS_TO_ALL_FINAL_HBT_BASES'
        assert all(sha(Path(n))==digest for n,digest in protected.items())
        result.update(status='PASS_ACTUAL_TREE162_SOURCE_BOUND_RC_COMPOSITION_AND_FAULTS_REQUIRES_TRANSIENT',
            adaptations=adaptations,composition=report,controls=controls,topology=topology,
            model_census=native['census'],interface_probes=interface,
            extraction_source_sha256=sha(extraction_path),
            outputs={str(q.relative_to(out)):sha(q) for q in (binding/'tree162-compact01.spice',wire/'tree162-wire01.spice',binding/'binding01.json',wire/'tree-topology-check.json',wire/'tree-interface-probes.json')})
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error),adaptations=adaptations)
        raise
    finally:
        out.mkdir(parents=True,exist_ok=True)
        (out/'composition-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('status','adopted')}),flush=True)


if __name__=='__main__':
    main()
