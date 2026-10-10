# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-only matrix-component review; no producer/HDL execution."""
from pathlib import Path
import ast,difflib,hashlib,json,shutil,re
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.with_name('pcie-integrity-v23-20261006')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def j(p):return json.loads(Path(p).read_text())
F=B/'component-source-freeze02.json';f=j(F);old=j(B/'component-source-freeze01.json')
assert pin(F)==dict(bytes=10721,sha256='5bac8dc9531a542919b05ebd76cd397a33a64a31d69c03e9754d92626f6f84c9')
assert len(f['sources'])==49
for p,v in f['sources'].items():assert pin(p)==v,p
for p,v in old['sources'].items():assert f['sources'][p]==v==pin(p),p
for tool,expected in f['selected_tools'].items():
 path=Path(shutil.which(tool)).absolute();assert str(path)==expected['path']
 assert pin(path)=={k:expected[k]for k in ('bytes','sha256')}
 text=path.read_text();assert f'/home/hasanmelih/.local/opt/iverilog12/usr/bin/{tool}' in text
# Independently regenerate every full unabridged unified source bridge.
for bridge,parents,children in [
 ('component-launch-bridge01.json',[P/'launch_controls_targeted03.py',P/'detach_controls_targeted03.py'],[B/'launch_component01.py',B/'detach_component01.py']),
 ('component-launch-bridge02.json',[B/'launch_component01.py',B/'detach_component01.py'],[B/'launch_component02.py',B/'detach_component02.py'])]:
 rec=j(B/bridge)
 for key,a,b in zip(['whole_launcher_diff','whole_detacher_diff'],parents,children):
  assert ''.join(difflib.unified_diff(a.read_text().splitlines(keepends=True),b.read_text().splitlines(keepends=True)))==rec[key],key
for n in ('test_matrix_relation01.py','launch_component02.py','detach_component02.py'):ast.parse((B/n).read_text())
source=(B/'prefix_candidate01.vh').read_text();test=(B/'test_matrix_relation01.py').read_text()
assignments=re.findall(r'token_prefix_context\[(\d+)\+d\]=',source)
assert sorted(map(int,assignments))==list(range(0,96,8))
assert source.count('context_prefix_modes=noncarry|({8{initial_mode[1]}}&carry);')==1
assert all(x in source for x in ['suffix2=control_compose(t2,t1);','({8{c0[1]&c1[2]}}&context_bits[88+:8])','({8{c0[1]&c1[7]}}&8\'h80)','({8{c0[1]&c1[1]}}&c2)'])
assert 'for(flags=0;flags<1024;' in test and 'for(carry_flags=0;carry_flags<16;'in test
assert 'nc!=4 || ni!=9 || nm!=nt*nc' in test and 'if(ref_mode!==dut_mode)'in test
assert 'full_matrix_checks!=nt*nt*nt*nc*nc*nc' in test and 'check_count!=full_matrix_checks*ni*3' in test
assert test.count('V24_PREFIX_RELATION word=')==2
assert all(x in test for x in ('wrong_initial_column','drop_bad_carry','drop_middle_exit','wrong_suffix','candidate.count(a)==1','result.returncode!=0'))
# Bind floor and selected runtime fixes without executing their guarded campaign.
launch=(B/'launch_component02.py').read_text();detach=(B/'detach_component02.py').read_text()
assert launch.index('entry_free=shared_floor(1024**3)')<launch.index("owner=life.ProcessOwner")
assert 'owner.check();shared_floor(528*1024**2);owner.cancelled.wait(0.05)'in launch
assert launch.index('owner.check();code=owner.complete(p);owner.check()')<launch.index("r['terminal_shared_free']=shared_floor(528*1024**2)")
assert '\n owner.check()\nexcept BaseException' in launch
assert 'j[\'detacher\']==pin(Path(__file__))' in detach
assert not(B/'component-status01.json').exists() and not Path('/dev/shm/nssoc-integrity-v24-matrix-controls01').exists()
receipt=dict(status='PASS_SOURCE_ONLY_V24_MATRIX_COMPONENT_CONTROLS',freeze=pin(F),launcher=pin(B/'launch_component02.py'),detacher=pin(B/'detach_component02.py'),findings=[],method=pin(__file__),input_files=49,prior_findings=pin(B/'component-source-findings-vco01.json'),
 full_source_review=['Read all candidate Verilog, actual HDL testbench, frozen transition/compose/apply functions, architecture contract and both generations of launchers. No reviewed helper or HDL executed.',
 '96-bit context covers exactly twelve eight-bit vectors. Three carried-prefix equations enumerate first/middle/last exits from mode1 plus absorbing badmode7; non-carried columns0/2/3 use original compose order. Mode1 cannot be entered from other modes in the frozen transition function.',
 'Actual HDL test enumerates16384 literal0/1/X/Z classifications, requires known matrices, checks noncarry independence and destination support, and enumerates every finite matrix triple against nine actual initial-state mode patterns at allthree prefixes. Four mutants alter distinct column/exit/suffix terms and must reach the exact relation fatal, not any compile failure.',
 'Four-state index suppression remains the original Verilog behavior. Candidate gates only known transition entries with initial0/1/X modes; no assumed two-state replacement. Component does not yet establish bank ownership, public port behavior or full product timing.',
 'All49 frozen inputs rehashed; candidate/test/contract identical across01/02. Both complete source-generation diffs independently reconstructed. Selected lexical wrappers and underlying pinned Icarus resources now bound; shared1GiB entry and528MiB continuous/terminal checks added with owned cancellation/cleanup and post-context stop check. CPU6/2GiB, sanitized detached launch, no healthy elapsed timeout.'],
 limits=['Source-only approval to execute the finite component proof. No tests or mutants have run yet; failure/survival must be retained.','Word0/default path and product bank/context capture are outside this three-prefix component experiment and require subsequent product integration controls.','Earlier runtime/floor findings retained in source01; no original failure or incomplete product claim erased.'])
(B/'component-source-peer-vco02.json').write_text(json.dumps(receipt,indent=2)+'\n');print(pin(B/'component-source-peer-vco02.json'))
