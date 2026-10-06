from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
def pin(p):
 b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
p=B/'architecture-contract01.json';assert pin(p)=={'bytes':10798,'sha256':'b547913785a996155405d5d9892a25f79d550654c965621652bbf5aaa9e2b39a'}
c=json.loads(p.read_text());inputs={str(p):pin(p)}
for r in [c['baseline'],*c['evidence'].values()]:
 q=Path(r['path']);assert pin(q)=={k:r[k]for k in('bytes','sha256')};inputs[str(q)]=pin(q)
s=Path(c['baseline']['path']).read_text()
for exact in ['if(flush_i || stream_start_i)', 'else if((stream_abort_i && active_o) || fault_now)', 'if(ending && read_ptr==write_ptr && (!output_valid || ready_i))', 'output_valid<=1;output_data<=read_data;output_keep<=read_keep;', 'read_ptr<=read_ptr+read_count;', 'if(ring_overflow_now) overflow_sticky<=1;']:
 assert exact in s,exact
out={'status':'PASS_SOURCE_ONLY_V21_REGISTERED_RETIRE_DESCRIPTOR_CONTRACT','contract':pin(p),'findings':[],'inputs_rehashed':inputs,'review':[
'Independently read the full proposed contract and the original V17 parser, retirement, bank writer, reset/flush/start/fault priority, output ownership and EDS drain blocks. This is approval of a concrete architecture contract before RTL, not executed functional proof.',
'With old-state nonblocking semantics, simultaneous pop and capture moves the old descriptor into output and atomically replaces all six descriptor payload fields; capture wins only descriptor ownership. No same-edge new payload bypass is allowed.',
'When output is held, a nonempty descriptor cannot pop or be overwritten. A zero-keep descriptor can pop and be replaced while leaving held output untouched. The separate has_data register must remain procedural known 0/1; selected X/Z data must remain literal in payload storage.',
'Original reset, flush/start (flush dominant), explicit abort and parser fault priorities clear descriptor validity. Payload copies on a parser fault edge are permitted only while invalid and must be fully overwritten before the next valid capture. Do not mask existing valid_o with prospective fault_now: an already-visible beat may handshake on that edge, then future ownership is cleared.',
'EDS additionally tests old retire_valid. The last descriptor must reach output before epoch completion; output consumption and stream_end can coincide only under existing ready/valid sampling rules. Empty descriptors must drain too.',
'Ring capacity counts only slots not yet copied. The extra descriptor adds up to four DWORDs buffering, so exact overflow cycle and stall-dependent beat grouping can differ. Permanent-stall overflow remains required; encoded-byte/metadata epoch scoreboards must not waive dropped or duplicated handshakes.',
'Under uninterrupted ready=1 and nonfault active ingress, retire_room remains true. V17 ring read-pointer/parser/CRC/acceptance cadence should correspond while both epochs are active, and public output is delayed one cycle. EDS/active completion is intentionally shifted. This restricted relation should supplement, never replace, adversarial transaction/ownership tests.',
'The new boundary removes selected read payload from retirement availability, but committed/count/capacity and fanout paths remain. Actual same-4ns mapped timing is necessary; architecture alone does not imply closure.'
],'mandatory_next_gates':c['actual_validation_plan'],'execution':{'RTL_generated_or_modified':False,'HDL_or_native_executed':False},'limitations':['No V21 RTL exists at this reviewed cut.','No cycle equivalence for arbitrary stalls/faults is claimed.','MAX150 functional/timing screen cannot close MAX4118 or full PHY acceptance.'],'method':pin(Path(__file__))}
(B/'architecture-contract-source-peer-rx01.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'receipt':str(B/'architecture-contract-source-peer-rx01.json'),**pin(B/'architecture-contract-source-peer-rx01.json')},indent=2))
