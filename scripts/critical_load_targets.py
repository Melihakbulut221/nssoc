# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit original-route load repairs, never auto-adopted or threshold relaxed."""
import hashlib,json,os
from pathlib import Path
PROFILE=os.environ.get('NSSOC_CRITICAL_LOAD_PROFILE','two_buffer')
assert PROFILE in ('two_buffer','control_three_buffer','measured_load_batch'),PROFILE
# Instance, exact original master, output terminal, original signal terminal count.
TARGETS=[
    ('$abc$1705011$auto$blifparse.cc:397:parse_blif$1749936','sg13g2_a22oi_1','Y',2),
    ('$abc$1705011$auto$blifparse.cc:397:parse_blif$1749937','sg13g2_nand4_1','Y',2),
]
SELECTION=dict(profile=PROFILE,source_run=38809759501)
if PROFILE=='control_three_buffer':
    TARGETS.append(('input37806','sg13g2_buf_2','X',4))
if PROFILE=='measured_load_batch':
    path=Path(__file__).resolve().parents[1]/'docs/evidence/cloud-routed-high-load-targets-20261016.json'
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    assert digest=='7f6572696f303fda18383f7d0def5c8e583c15b9cd7cf821dc4c7aa6170341de'
    RECIPE=json.loads(raw);assert RECIPE['source_run']==38809759501
    assert RECIPE['selection']['unique_outputs']==len(RECIPE['selection']['targets'])==50
    TARGETS=[]
    for row in RECIPE['selection']['targets']:
        inst,pin=row['pin'].rsplit('/',1);assert pin in ('X','Y') and row['reported_fanout']>=1
        assert row['master'].endswith(('_1','_2')) and not any(x in row['master'] for x in ('df','latch','dlygate','clk'))
        TARGETS.append((inst,row['master'],pin,row['reported_fanout']+1))
    assert len({r[0] for r in TARGETS})==len(TARGETS)
    SELECTION.update(recipe_sha256=digest,source_log_sha256=RECIPE['source_log_sha256'],scope='All50matched heavy-load weak outputs within original30negative-path reports per group; not exhaustive allnets. Native exact terminal/driver/fanout/master/signal/NDR checks still mandatory. No automatic adoption.')
COUNT=len(TARGETS)
DIRECTORY={'two_buffer':'cloud-critical-load-eco','control_three_buffer':'cloud-control-load-eco','measured_load_batch':'cloud-measured-load-eco'}[PROFILE]
COMPLETE_STATUS={'two_buffer':'COMPLETE_TWO_BUFFER_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF','control_three_buffer':'COMPLETE_THREE_BUFFER_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF','measured_load_batch':'COMPLETE_MEASURED_LOAD_BATCH_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'}[PROFILE]
# Native Opendp.tcl units are microns. Original cells remain FIRM throughout.
MAX_DISPLACEMENT_UM=(100,20) if PROFILE=='two_buffer' else (1000,200)

def validate_measurements(text):
    if PROFILE!='measured_load_batch':return
    assert hashlib.sha256(text.encode()).hexdigest()==RECIPE['source_log_sha256']
    for row in RECIPE['selection']['targets']:
        assert row['observations']
        for observed in row['observations']:
            line=observed['native_line'];assert line in text.splitlines()
            assert line.endswith(row['pin']+' ('+row['master']+')')
            values=line.split();assert int(values[0])==row['reported_fanout']
            assert float(values[1])==observed['cap_pf']>=.1 and float(values[3])==observed['stage_delay_ns']>=1
            assert observed['path_slack_ns']<0
