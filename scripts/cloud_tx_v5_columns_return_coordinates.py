#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose unchanged native coordinate records for measured TX return bottlenecks."""
import hashlib,json,os,shlex,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-v5-columns-return-coordinates'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-v5-columns-native-return-diagnosis-20261018.json').read_text());diagnosis=pin['report']
        extraction=json.loads((ROOT/'docs/evidence/tx-v5-columns-extraction-pass-20261018.json').read_text())
        source=diagnosis['source'];assert source['extraction_summary_sha256']==extraction['summary_sha256']
        archive=OUT/'source.tar.gz';fetch(source['url'],source['sha256'],archive);assert archive.stat().st_size==source['bytes']
        inputs=OUT/'inputs';inputs.mkdir();receipts={}
        with tarfile.open(archive)as tar:
            names=tar.getnames()
            def extract(rel,expected):
                hits=[n for n in names if n=='cloud-tx-v5-columns-assembly/'+rel];assert len(hits)==1,(rel,hits)
                raw=tar.extractfile(hits[0]).read();assert hashlib.sha256(raw).hexdigest()==expected
                path=inputs/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                receipts[rel]=dict(sha256=expected,bytes=len(raw),member=hits[0]);return raw
            def native(rel):
                hits=[v for k,v in extraction['audit']['inputs'].items()if k.endswith('/'+rel)];assert len(hits)==1
                raw=extract(rel,hits[0]['sha256']);assert len(raw)==hits[0]['bytes'];return raw.decode()
            res=native('wire96/rc03/pump_wires.res.ext');base=native('wire96/rc03/pump_wires.ext')
            for rel in ('layout/result.json','wire96/device-locations01.json'):extract(rel,diagnosis['verified_files'][rel]['sha256'])
            anchors=json.loads(native('wire96/anchors08.json'))
        archive.unlink()
        focuses=[x for x in diagnosis['return_paths']if x['native_id']in (114,115,504)]
        assert len(focuses)==3
        nodes={n for x in focuses for e in x['top20_loss_branches']for n in e['nodes']}
        records={}
        for text in (res,base):
            for line in text.splitlines():
                fields=shlex.split(line)
                if len(fields)>1 and fields[0]in ('node','rnode')and fields[1]in nodes:records.setdefault(fields[1],[]).append(dict(raw=line,fields=fields))
        assert set(records)==nodes,dict(missing=sorted(nodes-set(records)))
        r.update(status='COMPLETE_NATIVE_RETURN_BOTTLENECK_COORDINATE_RECORDS_NOT_GEOMETRY_REPAIR',diagnostic_run=pin['run'],diagnostic_summary_sha256=pin['summary_sha256'],source=source,verified_files=receipts,focused_return_paths=focuses,native_node_records=records,native_replacement_header=res.splitlines()[:8],native_source_header=base.splitlines()[:8],native_terminal_anchors=[a for a in anchors['rows']if a['device']in (114,115,504)],sources_unchanged=all(sha(inputs/p)==v['sha256']for p,v in receipts.items()))
        assert r['sources_unchanged']
        print(json.dumps(dict(status=r['status'],source_header=r['native_source_header'],replacement_header=r['native_replacement_header'],records={n:records[n]for n in ('P_avss.n5354','P_avss.n5353','P_avss.n4189','P_avss.n4100')}),indent=2),flush=True)
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
