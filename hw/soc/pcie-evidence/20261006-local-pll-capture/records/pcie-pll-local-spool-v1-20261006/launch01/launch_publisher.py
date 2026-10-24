"""Independent source-gated publisher; never owns or signals the native run."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent
sys.path.insert(0,str(R/'scripts'))
import durable_pcie_spool_v1 as local
import publish_pcie_local_spool_v1 as worker

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert os.sched_getaffinity(0)=={14}
policy=json.loads((B/'policy.json').read_text())
for p,v in policy['pins'].items():assert pin(p)==v,p
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==policy['boot_id']
peer=json.loads((B/'source-peer-vco01.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_DETACHED_LOCAL_PLL_V5_LAUNCH'and not peer['findings']and peer['policy']==pin(B/'policy.json')
spool=Path(policy['spool_out']);out=Path(policy['publisher_out']);assert not out.exists()
expected=dict(schema='PCIE_LOCAL_LOSSLESS_SPOOL_V1',prefix=policy['prefix'],limits=vars(local.Limits()),reservation_is_filesystem_quota=False,native_resume_supported=False)
configuration=spool/'configuration.json';assert configuration.read_bytes()==local.encoded(expected)
assert not(spool/'native-terminal-invalid.json').exists()and not(spool/'terminal-retention-failure.json').exists()
# Read-only headroom observation; this is explicitly not an atomic reservation.
release=json.loads(subprocess.check_output(['gh','api',f'repos/{worker.publication.REPO}/releases/tags/{worker.TAG}'],timeout=120))
assert release['tag_name']==worker.TAG
pages=json.loads(subprocess.check_output(['gh','api',f'repos/{worker.publication.REPO}/releases/{release["id"]}/assets?per_page=100','--paginate','--slurp'],timeout=120))
assets=[asset for page in pages for asset in page];assert len({a['id']for a in assets})==len(assets)
assert len(assets)+local.Limits().parts+3<=1000,'Headroom for all bounded parts and metadata'
assert shutil.disk_usage(out.parent).free>=worker.SSD_FLOOR+worker.WORKER_CAP
command=[sys.executable,str(R/'scripts/publish_pcie_local_spool_v1.py'),'--spool',str(spool),'--out',str(out),'--configuration-sha',pin(configuration)['sha256']]
record=dict(command=command,configuration=pin(configuration),policy=pin(B/'policy.json'),source_peer=pin(B/'source-peer-vco01.json'),tag=worker.TAG,release_id=release['id'],observed_assets=len(assets),required_headroom=local.Limits().parts+3,atomic_reservation=False,native_signals_or_adoption=False,source=pin(__file__),boot_id=policy['boot_id'])
(B/'publication-command-runtime.json').write_text(json.dumps(record,indent=2)+'\n')
fd=os.open(B/'publication.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.dup2(fd,1);os.dup2(fd,2);os.close(fd);os.execv(command[0],command)
