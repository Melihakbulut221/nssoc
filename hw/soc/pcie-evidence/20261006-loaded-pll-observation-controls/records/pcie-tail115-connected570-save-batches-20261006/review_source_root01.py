"""Read-only review of exact batched-save source and bounded native control."""
from pathlib import Path
import ast,copy,gzip,hashlib,json,re,sys
B=Path(__file__).resolve().parent;T=B.parent/'pcie-tail115-connected570-tuning-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
f=read(B/'source-freeze01.json');assert len(f['pins'])==1780
for p,w in f['pins'].items():assert pin(p)==w,p
old=read(T/'source-freeze02.json')
for p,w in old['pins'].items():assert f['pins'][p]==w and pin(p)==w,p
peer=read(T/'source-only-peer-root02.json');assert peer['findings']==[] and peer['freeze']==pin(T/'source-freeze02.json')
sys.path.insert(0,str(T));sys.path.insert(0,str(B));import characterize_clamped570_02 as m;import save_batches03 as batch
config,rows,texts=m.config(.5);expected=m.n.vectors(rows,config['extra_vectors']);assert len(rows)==570 and len(expected)==len(set(expected))==1133
olddeck=m.deck(config,rows,texts);new=batch.replace_save(olddeck,expected)
assert new==(B/'proposed-full34ns-deck03.cir').read_text()
assert new.replace('\n'.join(batch.commands(expected))+'\n','save '+' '.join(expected)+'\n')==olddeck
assert '.tran 3.125e-13 3.4e-08 0 3.125e-13' in new
assert [len(s.split())-1 for s in batch.commands(expected)]==[128]*8+[109]
assert [v for s in batch.commands(expected)for v in s.split()[1:]]==expected
controls=(B/'run_controls01.py').read_text();tree=ast.parse(controls)
assert "tiny['stop_s']=2e-12" in controls and "run\\nwrite tiny.raw all" in controls
assert "len(meta['columns'])==1134" in controls and "len(rows)==570 and len(expected)==1133" in controls
assert "assert startup['zero_source_op']and len(startup['native_off_flags'])==64" in controls
assert "for mode in ('missing','duplicate','reordered')" in controls
assert "full34ns_tuning_executed=False" in controls
contract=read(B/'control-contract01.json');assert contract['resource']==dict(CPU=10,AS=2147483648,FSIZE=16777216,SSDcap=134217728,SSDfloor=1073741824,shared_entry=1073741824,shared_continuous_terminal=536870912,elapsed_watchdog=None,owner='exact inherited ProcessOwner with registered child group, real41priorcontrols+02native failure closure retained')
# Fully read owner implementation as bound by preceding independent resource peer.
owner=Path(m.life.__file__);ownertext=owner.read_text();assert 'class ProcessOwner' in ownertext and 'def complete' in ownertext
prior=T/'native02/v050-01';assert (prior/'bench.cir').read_text()==olddeck
failure=read(prior/'capture-failure.json');raw=gzip.decompress((prior/'wave.raw.gz').read_bytes());assert len(raw)==65596 and hashlib.sha256(raw).hexdigest()==failure['received_raw_sha256']
assert b'No. Variables: 2679\n'in raw and 'save: too many args.'in(prior/'run.log').read_text()
for pid,birth in [(414067,'6532224'),(414085,'6532468')]:
 p=Path(f'/proc/{pid}/stat');assert not p.exists() or p.read_text().rsplit(')',1)[1].split()[19]!=birth
u=B/'upstream-source01';cp=next(u.rglob('cpdefs.h')).read_text();cmd=next(u.rglob('commands.c')).read_text();control=next(u.rglob('control.c')).read_text();bp=next(u.rglob('breakp2.c')).read_text()
assert re.search(r'#define\s+LOTS\s+1000',cp)
assert re.search(r'\{\s*"save"\s*,\s*com_save.*?LOTS',cmd,re.S)
assert 'too many args.' in control and 'settrace' in bp
assert not (B/'native-control01').exists()
out=dict(status='PASS_SOURCE_ONLY_570_BATCHED_SAVE_NATIVE_CONTROLS',freeze=pin(B/'source-freeze01.json'),findings=[],reviewer_method=pin(__file__),pins=1780,old02pins_unchanged=len(old['pins']),observations=1133,raw_columns=1134,save_batches=[128]*8+[109],unchanged_full34ns_deck_except_save_partition=True,expected_control_stop_s=2e-12,prior_failure_prefix_bytes=65596,owner_source=pin(owner),source_limit=1000,scope='Only one bounded same570graph actual OP/2ps command-format control authorized. Full34ns physical campaign still needs actual control success and independent additive03 peer.',native_run_by_review=False,physics_acceptance=False)
(B/'source-only-peer-root01.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
