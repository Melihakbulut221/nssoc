# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One detached invocation of unchanged reviewed V4 for immutable32MiB parts."""
from pathlib import Path
import hashlib,json,os,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent
PYTHON=R/'hw/soc/tools/cocotb-venv/bin/python';PUBLISHER=R/'scripts/publish_pcie_native_capture_v4.py'
def pin(p):
 p=Path(p);assert p.is_file()and not p.is_symlink()or p==PYTHON
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def main():
 freeze=json.loads((B/'source-freeze01.json').read_text());peer=json.loads((B/'source-only-peer01-root.json').read_text())
 assert peer['status']=='PASS_SOURCE_ONLY_N16_IMMUTABLE_MULTIPART_PUBLICATION'and peer['freeze']==pin(B/'source-freeze01.json')and peer['findings']==[]
 assert all(pin(p)==v for p,v in freeze['inputs'].items())
 import prepare01 as m
 manifest_path=B/'pcie-tail115-sixteenthstep-multipart-manifest01.json';manifest=json.loads(manifest_path.read_text());assert m.verify(manifest,B/'parts01')==dict(**m.EXPECTED,parts=24)
 files=[B/'parts01'/r['name']for r in manifest['parts']]+[manifest_path]
 assert not(B/'publication-launch01.json').exists()and not(B/'release-parts01.json').exists()and not(B/'release-parts01.transport').exists()
 cmd=[str(PYTHON),str(PUBLISHER),'--tag','evidence-20261006-pcie-closure','--out',str(B/'release-parts01.json'),*[str(p)for p in files]]
 env={k:v for k,v in os.environ.items()if k not in ['PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD']};env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 log=R/'hw/soc/out/pcie-tail115-sixteenthstep-multipart-publication01.log'
 with log.open('xb')as stream:p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,env=env)
 stat=Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ',1)[1].split();assert int(stat[2])==p.pid
 result=dict(pid=p.pid,start_ticks=stat[19],process_group=stat[2],boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=cmd,freeze=pin(B/'source-freeze01.json'),peer=pin(B/'source-only-peer01-root.json'),note='Publisher owns bounded network children and reconciliation; this launcher exits immediately. No native process interaction.')
 (B/'publication-launch01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(pid=p.pid,start_ticks=stat[19],assets=len(files))))
if __name__=='__main__':main()
