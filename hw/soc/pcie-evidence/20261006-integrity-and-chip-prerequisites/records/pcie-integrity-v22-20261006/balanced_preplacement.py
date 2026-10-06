# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact default TX/RX native netlists: bounded three-corner preplacement screen."""
from pathlib import Path
import datetime, hashlib, json, resource, subprocess, time
ROOT=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
OUT=Path('/dev/shm/nssoc-integrity-v22-balanced-sta-01');import shutil,signal,os
# One owner directly supervises OpenROAD; no intermediate nested process group.
def interrupted(s,f):raise InterruptedError(f'Signal{s}')
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
while shutil.disk_usage('/dev/shm').free<1024**3:time.sleep(5)
assert os.sched_getaffinity(0)=={6},'Launch taskset -c 6'
OUT.mkdir()
PDK=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell')
APP=ROOT/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
LIBS={'slow':PDK/'lib/sg13g2_stdcell_slow_1p08V_125C.lib','typical':PDK/'lib/sg13g2_stdcell_typ_1p20V_25C.lib','fast':PDK/'lib/sg13g2_stdcell_fast_1p32V_m40C.lib'}
def pin(p):
    with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def limit():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    os.sched_setaffinity(0,{6})
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
RECORD=dict(status='RUNNING',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cases=[],physical_acceptance=False,entry_shared_free_bytes=1024**3,continuous_shared_free_floor_bytes=528*1024**2,controller_allowed_cpus=sorted(os.sched_getaffinity(0)),native_cpu_limit=1)
def save():(OUT/'result.json').write_text(json.dumps(RECORD,indent=2)+'\n')
save()
try:
    for kind,parent,top in [('rx','nssoc-integrity-v22-balanced-import-01','soc_pcie_gen3_continuous_rx_integrity_v22')]:
        d=OUT/kind;d.mkdir();base=Path('/dev/shm')/parent
        module=json.loads((base/'mapped.json').read_text())['modules'][top]
        inputs=[name+('*' if len(row['bits'])>1 else '') for name,row in module['ports'].items() if row['direction']=='input' and name!='clk_i']
        lines=['set_thread_count 1','define_corners slow typical fast']
        lines += [f'read_liberty -corner {name} {{{path}}}' for name,path in LIBS.items()]
        lines += [f'read_lef {{{PDK/"lef/sg13g2_tech.lef"}}}',f'read_lef {{{PDK/"lef/sg13g2_stdcell.lef"}}}',f'read_verilog {{{base/"mapped.v"}}}',f'link_design {top}',
                  'create_clock -name development_clock -period 4.0 [get_ports clk_i]',
                  'set data_inputs [get_ports {'+' '.join(inputs)+'}]',
                  'set_input_delay -clock development_clock 0.2 $data_inputs',
                  'set_input_transition 0.1 $data_inputs','set_output_delay -clock development_clock 0.2 [all_outputs]','set_load 0.01 [all_outputs]',
                  'initialize_floorplan -die_area {0 0 2000 2000} -core_area {40 40 1960 1960} -site CoreSite',
                  'set_wire_rc -signal -layer Metal2','set_wire_rc -clock -layer Metal4']
        for stage in ('BASELINE_CELL_ONLY','PREPLACEMENT_REPAIRED'):
            if stage=='PREPLACEMENT_REPAIRED':lines.append('repair_design -pre_placement')
            lines += [f'puts {stage}','report_worst_slack -max','report_worst_slack -min','report_check_types -max_slew -max_capacitance -violators']
            for corner in LIBS:
                for direction in ('max','min'):
                    lines += [f'puts {stage}_{corner}_{direction}',f'report_checks -corner {corner} -path_delay {direction} -group_path_count 1 -fields {{slew cap fanout}} -digits 6']
        lines += [f'write_verilog {{{d/"repaired.v"}}}',f'write_db {{{d/"repaired.odb"}}}',f'write_sdc {{{d/"screen.sdc"}}}']
        (d/'screen.tcl').write_text('\n'.join(lines)+'\n')
        files=[Path(__file__),APP,*LIBS.values(),PDK/'lef/sg13g2_tech.lef',PDK/'lef/sg13g2_stdcell.lef',base/'mapped.v',base/'mapped.json',d/'screen.tcl']
        row=dict(kind=kind,source_pins={str(p):pin(p) for p in files},command=[str(APP),'openroad','-exit',str(d/'screen.tcl')],memory_limit_bytes=2*1024**3,elapsed_watchdog_seconds=None)
        RECORD['cases'].append(row);save();start=time.monotonic()
        with (d/'native.log').open('x') as log:
            process=None
            try:
                oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
                try:process=subprocess.Popen(row['command'],stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit,start_new_session=True)
                finally:signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
                row['native_allowed_cpus']=sorted(os.sched_getaffinity(process.pid));assert row['native_allowed_cpus']==[6]
                row['minimum_shared_free']=shutil.disk_usage('/dev/shm').free
                while process.poll() is None:
                    free=shutil.disk_usage('/dev/shm').free
                    row['minimum_shared_free']=min(free,row['minimum_shared_free'])
                    if free<528*1024**2:raise RuntimeError('Shared scratch floor breached')
                    time.sleep(.2)
                row['returncode']=process.wait()
            except BaseException:
                import os,signal
                if process is not None:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.wait()
                raise
        row['elapsed_seconds']=time.monotonic()-start
        row['outputs']={p.name:pin(p) for p in d.iterdir() if p.is_file()};save()
        assert row['returncode']==0
        assert row['source_pins']=={str(p):pin(p) for p in files}
    RECORD['status']='COMPLETE_PREPLACEMENT_SCREEN_REVIEW_REQUIRED'
except BaseException as error:RECORD.update(status='FAILED_RETAINED',error=repr(error));raise
finally:save()
