# SPDX-License-Identifier: Apache-2.0
"""Slice immutable completed timing reports in cloud; no CAD rerun."""
import pathlib,hashlib,zipfile,json,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
p=pathlib.Path('reports.zip');assert hashlib.sha256(p.read_bytes()).hexdigest()=='65a0b3c26fc315e23ee1396d3fda00d3748c1d14d824b8dba5723e0eee8f5b8e'
out=pathlib.Path('out');out.mkdir()
with zipfile.ZipFile(p) as z:
 summary=json.loads(z.read('routed-summary.json'));assert len(summary['corners'])==3
 (out/'routed-summary.json').write_text(json.dumps(summary,indent=2))
 rows=[]
 for corner in summary['corners']:
  for delay in ['max','min']:
   name=corner+'/'+delay+'.head.rpt';data=z.read(name);text=data.decode();pieces=text.split('Startpoint:',2);assert len(pieces)==3
   first='Startpoint:'+pieces[1];assert 'data arrival time' in first and 'slack (' in first
   target=corner+'-'+delay+'-worst.rpt';(out/target).write_text(first)
   rows.append({'source_report':name,'source_sha256':hashlib.sha256(data).hexdigest(),'slice':target,'slice_sha256':hashlib.sha256(first.encode()).hexdigest()})
 (out/'slice-proof.json').write_text(json.dumps({'source_run':43591198141,'source_artifact':14120119428,'source_artifact_sha256':'65a0b3c26fc315e23ee1396d3fda00d3748c1d14d824b8dba5723e0eee8f5b8e','slices':rows,'cad_rerun':False,'manufacturing_approval':False},indent=2))
