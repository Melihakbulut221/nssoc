# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""An adopted worker survives its former deadline; its real verdict is retained."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'hw/soc/flow'))
from wait_without_deadline import supervise

CONTROLLER = '''
from pathlib import Path
import subprocess,sys,time,json
root=Path(sys.argv[1]); mode=sys.argv[2]
code="import time,sys; time.sleep(1.3); sys.exit("+('7'if mode=='exit7'else'0')+")"
if mode=='error':code="import time; time.sleep(.3); print('ERROR: Worker thread: std::bad_alloc',flush=True); time.sleep(20)"
with(root/'worker.log').open('w')as f:
 child=subprocess.Popen([sys.executable,'-c',code],stdout=f,start_new_session=True)
 (root/'pid').write_text(str(child.pid));start=time.monotonic();reason='finished'
 while child.poll()is None:
  if 'ERROR:'in(root/'worker.log').read_text():child.terminate();reason='error';break
  if time.monotonic()-start>.65:child.terminate();reason='timeout';break
  time.sleep(.02)
 code=child.wait();(root/'result.json').write_text(json.dumps(dict(reason=reason,returncode=code,pid=child.pid)))
'''


@pytest.mark.parametrize('mode,reason,code',[
    ('normal','finished',0),('exit7','finished',7),('error','error',-15)])
def test_live_worker_keeps_identity_and_original_verdict(tmp_path,mode,reason,code):
    parent=subprocess.Popen([sys.executable,'-c',CONTROLLER,str(tmp_path),mode],start_new_session=True)
    worker=None
    try:
        deadline=time.monotonic()+5
        while not(tmp_path/'pid').exists():
            assert time.monotonic()<deadline
            time.sleep(.01)
        worker=int((tmp_path/'pid').read_text())
        receipt=supervise(parent.pid,worker,tmp_path/'worker.log',tmp_path/'receipt.json',interval=.01)
        assert parent.wait(timeout=5)==0
        result=json.loads((tmp_path/'result.json').read_text())
        assert result==dict(reason=reason,returncode=code,pid=worker)
        assert receipt['status']=='ORIGINAL_CONTROLLER_RESUMED'
        assert receipt['elapsed_time_limit_seconds']is None
        assert receipt['worker_restarted']is False
    finally:
        if parent.poll()is None:
            os.kill(parent.pid,signal.SIGCONT)
            parent.kill()
            parent.wait()
        if worker:
            try:os.kill(worker,signal.SIGKILL)
            except ProcessLookupError:pass
