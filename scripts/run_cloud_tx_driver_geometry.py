#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inspect real TX driver geometry before routing; no layout or PHY acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import urllib.request
from run_cloud_tx_layout_repair import fetch, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hw/soc/out/cloud-tx-driver-geometry'
PDK_COMMIT = 'c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
DRIVER_SHA = 'de22ecc19975aab5b35cf441f0c4b0ee289ae2dae9f1727625b22e2ae595f135'
FILES = {
    'gds/sg13g2_stdcell.gds': ('39bbae40a3ac9b82a373d346c575c3fd9425cea9', 626688),
    'cdl/sg13g2_stdcell.cdl': ('782eb876931a7751d79bc1db8d8c25654bb548f5', 86148),
    'spice/sg13g2_stdcell.spice': ('1f6511575128062820cc3b0f76be6ce96ffe80fa', 118224),
    'lef/sg13g2_stdcell.lef': ('4dd096a420edb5c52575e46f63bb1d2354feae49', 188966),
}

def extract_cell(text, cell):
    match = re.findall(r'(?ims)^\.subckt\s+' + re.escape(cell) + r'\s+[^\n]*\n.*?^\.ends[^\n]*(?:\n|$)', text)
    assert len(match) == 1
    return match[0]

def inspect():
    import xml.etree.ElementTree as ET
    pdk = ROOT / 'pdk'
    source = pdk / 'libs.tech/klayout/python'
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / 'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    out = OUT / 'native'
    out.mkdir()
    layout = pya.Layout()
    def rect(b): return [b.left, b.bottom, b.right, b.top]
    def region(cell, layer, dtype=0):
        return pya.Region(cell.begin_shapes_rec(layout.layer(layer, dtype))).merged()
    rows = []
    for ng in (1, 10):
        cell = layout.create_cell('nmosHV', 'SG13_dev', {'w': '10u', 'l': '.45u', 'ng': ng})
        assert cell is not None and not cell.is_empty()
        active = region(cell, 1)
        poly = region(cell, 5)
        gates = sorted((poly & active).each(), key=lambda p:p.bbox().left)
        contacts = sorted(region(cell, 8).each(), key=lambda p:p.bbox().left)
        assert len(gates) == ng and len(contacts) == ng + 1
        for gate in gates:
            b=gate.bbox()
            assert gate.area()==b.area()
            assert abs(b.width()*layout.dbu-.45) < 1e-9
            assert abs(b.height()*layout.dbu-10/ng) < 1e-9
        for i,gate in enumerate(gates):
            assert contacts[i].bbox().right < gate.bbox().left < gate.bbox().right < contacts[i+1].bbox().left
        metal_pins = sorted(region(cell,8,2).each(), key=lambda p:p.bbox().left)
        gate_pins = list(region(cell,5,2).each())
        assert len(metal_pins)==2 and len(gate_pins)==1
        assert (pya.Region(metal_pins[0])-pya.Region(contacts[0])).is_empty()
        assert (pya.Region(metal_pins[1])-pya.Region(contacts[1])).is_empty()
        assert not (pya.Region(gate_pins[0]) & pya.Region(gates[0])).is_empty()
        rows.append(dict(ng=ng, cell=cell.name, bbox_um=rect(cell.dbbox()),
            gate_intersections_um=[rect(g.bbox().to_dtype(layout.dbu)) for g in gates],
            diffusion_contacts=[dict(index=i, connection_required='source' if i%2==0 else 'drain',
                bbox_um=rect(c.bbox().to_dtype(layout.dbu))) for i,c in enumerate(contacts)],
            metal_pin_boxes_um=[rect(p.bbox().to_dtype(layout.dbu)) for p in metal_pins],
            gate_pin_boxes_um=[rect(p.bbox().to_dtype(layout.dbu)) for p in gate_pins],
            all_fingers_connected=False))
    layout.write(str(out/'native_nmos_specimens.gds'))
    std=pya.Layout();std.read(str(OUT/'upstream/gds/sg13g2_stdcell.gds'))
    cell=std.cell('sg13g2_buf_16');assert cell is not None and not cell.is_empty()
    layers=[]
    for index in std.layer_indexes():
        info=std.get_info(index);reg=pya.Region(cell.begin_shapes_rec(index)).merged()
        texts=[];it=cell.begin_shapes_rec(index)
        while not it.at_end():
            s=it.shape()
            if s.is_text():texts.append(dict(text=s.text.string,position=str(s.text.trans.transformed(it.trans()))))
            it.next()
        if not reg.is_empty() or texts:
            layers.append(dict(layer=info.layer,datatype=info.datatype,polygons=reg.count(),area_um2=reg.area()*std.dbu**2,texts=texts))
    # Exact original cell reference is retained: no transistor width, finger count or junction-area rewriting.
    for kind in ('cdl','spice'):
        text=extract_cell((OUT/'upstream'/kind/('sg13g2_stdcell.'+kind)).read_text(),'sg13g2_buf_16')
        (out/('buf16.'+kind)).write_text(text)
    spice=(out/'buf16.spice').read_text()
    assert spice.splitlines()[0].split()[2:]==['X','A','VDD','VSS']
    devices=[l for l in spice.splitlines() if l.startswith('X')]
    assert len(devices)==4
    widths=sorted((float(re.search(r'\bw=([\d.]+)u',l)[1]),int(re.search(r'\bng=(\d+)',l)[1])) for l in devices)
    assert widths==[(4.44,6),(6.72,6),(11.84,16),(17.92,16)]
    driver=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
    assert sha(driver)==DRIVER_SHA
    hv=[l for l in driver.read_text().splitlines() if l.startswith('XHV_')]
    assert len(hv)==4 and all(l.split()[1:]==['sink','drv','avss','sub','sg13_hv_nmos','w=10u','l=.45u','ng=10'] for l in hv)
    # Geometry inventory is deliberately not reported as transistor LVS or routed-driver completion.
    record=dict(status='PASS_NATIVE_DRIVER_GEOMETRY_INVENTORY_NOT_ROUTED_OR_LVS_ACCEPTANCE',
        nmos_specimens=rows,buf16=dict(bbox_um=rect(cell.dbbox()),layers=layers,
            original_spice=spice,device_widths_um_and_fingers=widths),
        required_routing=dict(hv_instances=4,total_hv_gate_fingers=40,
            per_hv_source_contacts=6,per_hv_drain_contacts=5,per_hv_gate_contacts=10,
            buf16_ports=['X','A','VDD','VSS'],external_ports=['din','dout','avdd','dvdd','avss','sub'],
            resistor_instances=4,local_body_and_well_connections_required=True),
        accepted=False,driver_routed=False,drc_pass=False,lvs_pass=False,qualified_pex=False,serial_phy_complete=False)
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inspect',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.inspect: inspect();return
    OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,serial_phy_complete=False)
    protected={str(p):sha(p) for p in (Path(__file__).resolve(),ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc')}
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'restore.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed) as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        assert all(sha(Path(p))==h for p,h in protected.items())
        result['fixture']=spec['receipt'];result['upstream']={};save()
        for path,(oid,size) in FILES.items():
            url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK_COMMIT+'/ihp-sg13g2/libs.ref/sg13g2_stdcell/'+path
            with urllib.request.urlopen(url,timeout=120) as response: data=response.read(size+1)
            assert len(data)==size
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
            dest=OUT/'upstream'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            result['upstream'][path]=dict(url=url,git_blob=oid,bytes=size,sha256=sha(dest))
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        result['runtime_sha256']=sha(app);save()
        with (OUT/'native.log').open('w') as log:
            code=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--inspect'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if code:
            print((OUT/'native.log').read_text(errors='replace')[-10000:]);raise RuntimeError(('native inspection',code))
        result['native']=json.loads((OUT/'native/result.json').read_text())
        assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest['files'].items())
        assert all(sha(Path(p))==h for p,h in protected.items())
        result['status']=result['native']['status']
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['protected_inputs']=protected
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
