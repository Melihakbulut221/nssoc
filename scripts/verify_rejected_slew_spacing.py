import hashlib,io,json,subprocess,zipfile
repo='repos/Melihakbulut221/nssoc'
r=json.loads(subprocess.check_output(['gh','api',repo+'/actions/runs/44471950240']))
assert r['head_sha']=='1a6ba054e3a17179ff3b0099e1c5a2b7d3e2b0eb' and r['run_attempt']==1 and r['conclusion']=='failure'
b=subprocess.check_output(['gh','api',repo+'/actions/artifacts/14506240399/zip'])
assert hashlib.sha256(b).hexdigest()=='05bc324883ba6613a33805d26a56bad4ecae4f54af716ba8ca51536f056744b5'
z=zipfile.ZipFile(io.BytesIO(b));r=json.loads(z.read('result.json'))
assert r['source_head']=='1a6ba054e3a17179ff3b0099e1c5a2b7d3e2b0eb'
assert set(z.namelist())==set(r['outputs'])|{'result.json'}
for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==1 and r['metrics']['antenna__violating__pins']==1
assert r['visible_geometry']['inter_net_contact_pairs']==0
assert not r['visible_geometry']['signal_nets_with_disconnected_geometry']
assert not r['detailed_preservation']['changed_unselected_nets'] and not r['detailed_preservation']['changed_clock_nets']
report=z.read('antenna.rpt').decode();assert report.count('Net:')==1 and 'Net: nssoc_sta_n_56323' in report
print('Verified rejected spacing candidate manifest:',len(r['outputs']),'outputs; one antenna violation retained as rejection.')
