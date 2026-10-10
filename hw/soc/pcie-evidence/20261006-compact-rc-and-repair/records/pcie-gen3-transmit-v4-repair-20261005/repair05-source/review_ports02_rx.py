# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json,subprocess
S=Path(__file__).resolve().parent;B=S.parent
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
fpath=S/'ports02-source-freeze.json';f=json.loads(fpath.read_text());a=Path(f['before']['path']);z=Path(f['after']['path']);assert pin(a)=={k:f['before'][k] for k in ('bytes','sha256')};assert pin(z)=={k:f['after'][k] for k in ('bytes','sha256')}
r=f['replacement'];assert a.read_text().count(r['from'])==r['count']==1;assert a.read_text().replace(r['from'],r['to'])==z.read_text()
pa=ast.parse(a.read_text());pz=ast.parse(z.read_text());assert [(n.name,ast.dump(n,include_attributes=False)) for n in pa.body if isinstance(n,ast.FunctionDef)]==[(n.name,ast.dump(n,include_attributes=False)) for n in pz.body if isinstance(n,ast.FunctionDef)]
old=json.loads((S/'proof-source-only-peer-rx02.json').read_text());assert old['findings']==[];assert pin(B/'owned_lifecycle05.py')==old['source_pins'][str(B/'owned_lifecycle05.py')]
failed=Path('/dev/shm/nssoc-tx-path-v4-repair05-physical-replay-01');assert pin(failed/'result.json')==f['failed_attempt'];d=json.loads((failed/'result.json').read_text());assert d['status']=='FAIL_RETAINED' and d['returncode']!=0
log=(failed/'simulation.log').read_text();assert 'SRE module mismatch' in log;assert not (failed/'results.xml').exists()
command=[f['launcher_python'],'-c','import sys,json;print(json.dumps(dict(executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix)))']
probe=json.loads(subprocess.check_output(command,text=True));assert probe==f['python_probe'];assert Path(probe['prefix'])==Path(f['launcher_python']).parent.parent and probe['prefix']!=probe['base_prefix']
p=S/'ports02-source-only-peer-rx.json';result=dict(status='PASS_SOURCE_ONLY_TX05_PORTS02_OUTPUT_ROOT_AND_VENV_LAUNCH',findings=[],freeze=pin(fpath),method=pin(__file__),source=pin(z),unchanged_lifecycle=pin(B/'owned_lifecycle05.py'),exact_single_output_path_inverse=True,actual_interpreter_probe=dict(command=command,observed=probe),old_failure=dict(result=pin(failed/'result.json'),log=pin(failed/'simulation.log'),results_xml_absent=True),scope='Only new port output root01→02; all methods/functions/bench/models/constraints unchanged. Lexicalvenv Python confirmed by actual bounded stdlib-only subprocess; no DUT/native/replay execution. Old launch failure retained.')
assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
