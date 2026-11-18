import importlib.util, os, json
from pathlib import Path
from unittest.mock import patch
import numpy as np

def test_all_six_cases_execute_and_any_failure_remains_fatal(tmp_path):
    os.environ['NSSOC_PAD_CLAMP_OHMS']='0'
    os.environ['NSSOC_PAD_ITL4']='100'
    spec=importlib.util.spec_from_file_location('pad_current', 'scripts/cloud_core_only_pad_turnoff_current.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.OUT=tmp_path/'out'
    class Capsule:
        def __init__(self, aid): self.aid=aid
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def extractall(self, inp, **kwargs):
            (inp/'manifest.json').write_text('{"files":{}}')
        def extractfile(self, name):
            import io
            return io.BytesIO(b'r3')
    def fake_sha(p):
        name=Path(p).name
        return {'r3_cmc.osdi':'9b41facf3c49d2266e542406547ed00677304f09c1dd281f3bf90414ee053828',
        'sg13g2_io.spi':'c2cfa122268050f770e91eeb0c70682775f9610cf4d5b066805b2d57c5980ce2'}.get(name,'fixture')
    def output(command,**kwargs):
        if '--version' in command:return 'ngspice-47'
        return b'{"content":""}'
    calls=[]
    def simulate(command, cwd, stdout, **kwargs):
        calls.append(cwd.name)
        stdout.write('NSSOC_POST_TRAN_SOLVER_READBACK\nIntegration Method = GEAR\nMaxOrder = 2\nitl4 (transient iterations) = 100\nNSSOC_PAD_CURRENT_CAPTURE_COMPLETE\n')
        if cwd.name=='0-turnoff':stdout.write('TRAN: Timestep too small\n')
        class Result:returncode=0
        return Result()
    times=np.linspace(0,50e-9,1001)
    data=np.column_stack([times,np.zeros_like(times),np.full_like(times,.001),np.zeros_like(times),np.zeros_like(times),np.full_like(times,1.5)])
    with patch.dict(os.environ,GITHUB_ACTIONS='true',GITHUB_SHA='fixture',CLOUD_NGSPICE='/fixture/ngspice'),patch.object(m,'asset',lambda aid,digest:Capsule(aid)),patch.object(m,'sha',fake_sha),patch.object(m.subprocess,'check_output',output),patch.object(m.subprocess,'run',simulate),patch.object(m.np,'loadtxt',lambda *a,**k:data):
        import pytest
        with pytest.raises(AssertionError):m.main()
    r=json.loads((m.OUT/'result.json').read_text())
    assert calls==['0-turnoff','0-enabled','0-disabled','1-turnoff','1-enabled','1-disabled']
    assert r['status']=='FAIL_OR_INCOMPLETE' and not r['accepted']
    assert r['cases']['0-turnoff']['status']=='FAIL_OR_INCOMPLETE'
    assert all(r['cases'][n]['status']=='CAPTURE_COMPLETE' for n in calls[1:])
    assert r['sources_unchanged']
