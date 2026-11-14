# SPDX-License-Identifier: Apache-2.0
import pathlib,hashlib,zipfile,io,json,re
b=pathlib.Path('reports.zip').read_bytes();assert hashlib.sha256(b).hexdigest()=='cb79f308624a57c7650cd69a83bbe6dabb6803b5317d5a46d25755d0f07062dd'
z=zipfile.ZipFile(io.BytesIO(b));rows=[]
for corner,kind,needle in [('nom_slow_1p08V_125C','max','slice$165650'),('nom_fast_1p32V_m40C','min','g_wsel[6]')]:
 n=f'{corner}/{kind}.head.rpt';s=z.read(n).decode();blocks=re.split(r'(?=Startpoint:)',s)
 matches=[v for v in blocks if needle in v and 'VIOLATED' in v];assert matches,(n,needle)
 rows.append({'report':n,'matching_paths':len(matches),'first_matching_path':matches[0]})
r={'run':43505737740,'artifact':14089073072,'artifact_sha256':hashlib.sha256(b).hexdigest(),'paths':rows,'summary':json.loads(z.read('routed-summary.json')),'production_accepted':False}
pathlib.Path('out').mkdir();pathlib.Path('out/critical-paths.json').write_text(json.dumps(r,indent=2))
