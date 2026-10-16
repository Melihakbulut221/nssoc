#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read exact prior native failure evidence on the hosted runner."""
import json,os,tarfile,xml.etree.ElementTree as ET
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
        if member.name.endswith(('/base/aggregate.cir','/check-raw_lvs/extracted.cir','/check-aggregate_lvs/extracted.cir','/check-drc/drc.lyrdb')):
            assert member.size<200000
            data=tar.extractfile(member).read();dest=OUT/path.name
            if path.name=='drc.lyrdb':
                xml=ET.fromstring(data)
                r['drc_items']=[ET.tostring(i,encoding='unicode') for i in xml.findall('.//items/item')]
            else:r['texts'][str(path)]=data.decode()
            dest=OUT/('_'.join(path.parts[-2:]));dest.write_bytes(data)
r['outputs']={q.name:sha(q) for q in OUT.iterdir() if q.is_file()}
(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
