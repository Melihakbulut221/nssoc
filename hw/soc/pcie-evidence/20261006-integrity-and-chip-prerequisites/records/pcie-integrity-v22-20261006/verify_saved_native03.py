"""Require completed unchanged native outputs; no mapping/import executed."""
from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'native-recovery-basis03.json'
assert pin(p)=={'bytes': 9466, 'sha256': 'b6eaa93bd4806281b20592204db3119c14e5b90ceb777a5a89c802029c83d1b3'}
q=json.loads(p.read_text());assert q['status']=='SAVED_COMPLETE_V22_MAP_BOUNDARY_IMPORT_DISPATCH_TYPO_RETAINED'
for name,value in q['files'].items():assert pin(name)==value,name
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==q['boot_id']
for birth in q['closed_births']:
 s=Path(f"/proc/{birth['pid']}/stat")
 if s.exists():assert s.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
b=json.loads((B/'native-registered-boundary.json').read_text());assert b['status']=='PASS_EMITTED_REGISTERED_RETIRE_PAYLOAD_BOUNDARY_ONLY'and b['no_original_ring_content_q_in_output_d']and len(b['availability_consumer_flop_d'])==8
assert not Path('/dev/shm/nssoc-integrity-v22-balanced-sta-01').exists()
print('PASS_SAVED_V22_MAP_BOUNDARY_IMPORT_EXACT_REUSE')
