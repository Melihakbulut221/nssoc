# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A timeout must clean up a descendant even when its parent exits first."""
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hw/soc/flow'))
from bounded_process import bounded_run


def test_normal_completion(tmp_path):
    with (tmp_path/'log').open('w') as log:
        result = bounded_run([sys.executable, '-c', 'print("completed")'],
                             stdout=log, timeout=2)
    assert result.returncode == 0
    assert (tmp_path/'log').read_text().strip() == 'completed'


def test_timeout(tmp_path):
    with (tmp_path/'log').open('w') as log:
        result = bounded_run([sys.executable, '-c', 'import time;time.sleep(60)'],
                             stdout=log, timeout=.2, grace=.1)
    assert result.returncode == 124


def test_descendant_ignoring_term_cannot_outlive_deadline(tmp_path):
    pidfile = tmp_path/'descendant.pid'
    descendant = ('import signal,time,os;from pathlib import Path;'
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                  f'Path({str(pidfile)!r}).write_text(str(os.getpid()));time.sleep(60)')
    parent = ('import subprocess,sys,time;'
              f'subprocess.Popen([sys.executable,"-c",{descendant!r}]);time.sleep(60)')
    with (tmp_path/'log').open('w') as log:
        result = bounded_run([sys.executable, '-c', parent], stdout=log,
                             timeout=.5, grace=.1)
    assert result.returncode == 124 and pidfile.is_file()
    pid = int(pidfile.read_text())
    for _ in range(20):
        stat = Path(f'/proc/{pid}/stat')
        if not stat.exists() or stat.read_text().split()[2] == 'Z':
            break
        time.sleep(.05)
    else:
        subprocess.run(['kill', '-KILL', str(pid)], check=False)
        raise AssertionError('Live descendant survived its process-group deadline')
