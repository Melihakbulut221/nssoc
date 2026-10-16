#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read exact prior native failure evidence on the hosted runner."""
import json,os,tarfile,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-hv-evidence'
assert os.environ.get('GITHUB_ACTIONS')=='true'
OUT.mkdir(parents=True,exist_ok=False)
p=OUT/'source.tar.gz'
fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38864608050-1-tx-hv-fingers/tx-hv-fingers-38864608050-1.tar.gz.part0000','eee6fa60f45def0fb443492bbd33833b566a7046ad64e85d05ee63a92e0fecfd',p)
assert p.stat().st_size==151687
r=dict(status='READ_PRIOR_FAILURE_EVIDENCE_NOT_PHYSICAL_ACCEPTANCE',source_run=38864608050,source_archive_sha256=sha(p),texts={},drc_items=[],accepted=False)
with tarfile.open(p) as tar:
    for member in tar:
        path=Path(member.name)
        assert not path.is_absolute() and '..' not in path.parts and path.parts[0]=='cloud-tx-hv-fingers'
        if not member.isfile():continue
        if member.name.endswith(('/base/aggregate.cir','/check-raw_lvs/extracted.cir','/check-aggregate_lvs/extracted.cir','/check-drc/drc.lyrdb','/base/layout.gds')):
            assert member.size<200000
            data=tar.extractfile(member).read();dest=OUT/path.name
            if path.name=='drc.lyrdb':
                xml=ET.fromstring(data)
                r['drc_items']=[ET.tostring(i,encoding='unicode') for i in xml.findall('.//items/item')]
            elif path.suffix!='.gds':r['texts'][str(path)]=data.decode()
            dest=OUT/('_'.join(path.parts[-2:]));dest.write_bytes(data)
spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
fixture=OUT/'fixture.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],fixture)
with tarfile.open(fixture) as tar:
    for member in tar:
        if member.isfile() and member.name.endswith('/nmosHV_code.py'):
            data=tar.extractfile(member).read();r['actual_nmos_pcell_source']=data.decode()
app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
script=OUT/'geometry.py'
script.write_text("""import pya,json
from pathlib import Path
root=Path(__file__).resolve().parent
layout=pya.Layout();layout.read(str(root/'base_layout.gds'))
result={}
for cell in layout.each_cell():
    entries=[]
    for layer in [1,5,6,8,14,31,44]:
        region=pya.Region(cell.begin_shapes_rec(layout.layer(layer,0))).merged()
        if not region.is_empty():entries.append(dict(layer=layer,polygons=[str(p) for p in region.each()]))
    result[cell.name]=dict(dbu=layout.dbu,layers=entries,instances=[dict(cell=layout.cell(i.cell_index).name,transform=str(i.dcplx_trans)) for i in cell.each_inst()])
(root/'native-geometry.json').write_text(json.dumps(result,indent=2)+'\\n')
""")
with (OUT/'geometry.log').open('w') as log:code=subprocess.call([str(app),'python',str(script)],stdout=log,stderr=subprocess.STDOUT)
assert code==0
r['native_geometry']=json.loads((OUT/'native-geometry.json').read_text())
r['outputs']={q.name:sha(q) for q in OUT.iterdir() if q.is_file()}
(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
