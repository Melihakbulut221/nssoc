# SPDX-License-Identifier: Apache-2.0
"""Coverage-limited corner/path survey; absent paths never imply timing closure."""
import pathlib, hashlib, zipfile, io, json, re
b=pathlib.Path('reports.zip').read_bytes()
assert hashlib.sha256(b).hexdigest()=='cb79f308624a57c7650cd69a83bbe6dabb6803b5317d5a46d25755d0f07062dd'
z=zipfile.ZipFile(io.BytesIO(b)); rows=[]
for n in z.namelist():
 if not (n.endswith('/max.head.rpt') or n.endswith('/min.head.rpt')): continue
 s=z.read(n).decode(errors='strict')
 blocks=re.split(r'(?=Startpoint:)',s)
 selected=[]
 for block in blocks:
  start=re.search(r'^Startpoint:\s*(.*)',block,re.M)
  end=re.search(r'^Endpoint:\s*(.*)',block,re.M)
  if not start or not end: continue
  if not any(q in block for q in ['g_wsel[6]','A_ADDR[6]','hold51227']):continue
  slack=re.search(r'(-?\d+(?:\.\d+)?)\s+slack\s*\((?:VIOLATED|MET)\)',block)
  if not slack:slack=re.search(r'slack\s*\((?:VIOLATED|MET)\)\s+(-?\d+(?:\.\d+)?)',block)
  if not slack: continue # Ignore truncated path tails, never infer their slack.
  selected.append({'startpoint':start[1],'endpoint':end[1],'slack_report_units':float(slack[1]) if slack else None,'path':block})
 if selected:
  selected.sort(key=lambda x:float('inf') if x['slack_report_units'] is None else x['slack_report_units'])
  rows.append({'report':n,'matching_path_count':len(selected),'worst_matching_paths':selected[:3]})
r={'run':43505737740,'artifact':14089073072,'artifact_sha256':hashlib.sha256(b).hexdigest(),'report_inventory':[n for n in z.namelist() if n.endswith('.rpt')],'coverage_limited_paths':rows,'scope':'Existing report coverage only; no path absent from a truncated report is assumed safe. These results do not authorize adding hold delay without endpoint-specific all-corner STA on the modified netlist.','production_accepted':False}
pathlib.Path('out').mkdir();pathlib.Path('out/ethernet-hold-setup-coverage.json').write_text(json.dumps(r,indent=2))
print(json.dumps({'reports_with_matches':len(rows),'total_reports':len(r['report_inventory'])}))
