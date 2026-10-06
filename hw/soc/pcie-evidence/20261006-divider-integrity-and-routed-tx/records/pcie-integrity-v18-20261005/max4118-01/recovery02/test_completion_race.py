# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact observe AST with a real exited process and a real live peer pidfd."""
import ast,hashlib,json,os,signal,subprocess,time
from pathlib import Path
B=Path(__file__).resolve().parent
source=(B/'run.py').read_text();tree=ast.parse(source)
functions={n.name:n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
code=compile(ast.fix_missing_locations(ast.Module(body=[functions['identity'],functions['same'],functions['observe']],type_ignores=[])),str(B/'run.py'),'exec')
dead=subprocess.Popen(['/bin/sleep','0.1'],start_new_session=True)
def row(pid):
 f=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split();return dict(pid=pid,state=f[0],ppid=int(f[1]),process_group=int(f[2]),start_ticks=f[19])
deadrow=row(dead.pid);dead.wait()
live=subprocess.Popen(['/bin/sleep','20'],start_new_session=True);liverow=row(live.pid)
ns=dict(Path=Path,os=os,known={},fds={},record={},snapshot_tree=lambda seeds:[deadrow,liverow])
exec(code,ns);observed=ns['observe']();assert observed==[deadrow,liverow];assert len(ns['fds'])==1;assert (live.pid,liverow['start_ticks']) in ns['fds'];assert not ns['same'](deadrow)
fd=ns['fds'][(live.pid,liverow['start_ticks'])];signal.pidfd_send_signal(fd,signal.SIGTERM);assert live.wait()==-signal.SIGTERM;os.close(fd);assert not ns['same'](liverow)
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
r=dict(status='PASS_ACTUAL_EXIT_BEFORE_PIDFD_OPEN_AND_REMAINING_LIVE_PEER',source=pin(B/'run.py'),method=pin(__file__),dead_identity=deadrow,live_identity=liverow,dead_returncode=dead.returncode,live_returncode=live.returncode,exact_observe_AST=True,actual_ESRCH_caught=True,remaining_live_peer_pidfd_opened_and_signalled=True,no_remaining_births=True)
p=B/'completion-race-control.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
