# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite pump/filter slice measurements; no loaded-force or loop acceptance."""
import argparse, concurrent.futures, copy, gzip, hashlib, json, re
import os, resource, shutil, stat, subprocess, sys, time, zlib
from pathlib import Path
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent
S=R/'hw/soc/out/pcie-tail115-pump13-source-20261006'
P16=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006'
sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(P16))
import characterize_sixteenthstep01 as previous
core=previous.core;n=previous.n;stream=previous.stream;require=previous.require;life=previous.life
SOURCE=S/'pump-filter13.spice'
NATIVE_ROOT=B/'native01'
POINT_LIMIT=64*1024**2;AGGREGATE_LIMIT=1024**3
FLOOR=512*1024**2;SSD_FLOOR=1024**3;RECEIPT_RESERVE=2*1024**2
MAX_ROWS=120000;HEADER_CAP=4*1024**2;FAILED_TAIL_RESERVE=1024**2
POINTS=(0.5,0.6,0.7)
STATES=dict(idle=(0.0,0.0),source=(2.5,0.0),sink=(0.0,2.5),both=(2.5,2.5))
CASES=tuple(f'v{int(round(v*100)):03d}-{state}' for v in POINTS for state in STATES)
OBS=['time']+stream.previous.data_names(json.loads((S/'composition01.json').read_text())['vectors'])
assert len(OBS)==len(set(OBS))==28

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def config(case='v060-idle',fault=''):
 require(case in CASES and fault=='','Only twelve named nominal pump13 diagnostics')
 freeze=S/'source-freeze02.json'
 require(pin(freeze)==dict(bytes=7253,sha256='f747b2b1fab2e4dd60b3cd8e4a3b571cec34b4d8989667134de0bbeeadd0970e'),'Frozen13 source contract')
 f=json.loads(freeze.read_text())
 for path,value in f['inputs'].items():require(pin(path)==value,'13 source input drift '+path)
 peer=json.loads((S/'architecture-source-peer-root01.json').read_text())
 require(peer['status']=='PASS_SOURCE_ONLY_PUMP13_FORCE_CONTRACT' and peer['freeze']==pin(freeze) and peer['contract']==pin(S/'force-contract02.json') and not peer['findings'],'Independent13 exact source and force-contract gate')
 composition=json.loads((S/'composition01.json').read_text())
 rows=copy.deepcopy(composition['devices'])
 texts={p.name:p.read_text() for p in (S/'pll_pfd_charge_pump_hv_v1.spice',SOURCE)}
 voltage,state=case.split('-');vctrl=int(voltage[1:])/100.0
 c=dict(case='pump13_'+case,sources=[str(freeze),str(S/'architecture-source-peer-root01.json'),str(S/'composition01.json'),str(S/'force-contract02.json'),str(SOURCE),str(S/'pll_pfd_charge_pump_hv_v1.spice'),str(Path(__file__))],
        roots=[composition['root']],fixture=composition['fixtures'][case],step_s=3.125e-13,stop_s=34e-9,window_s=[4e-9,34e-9],vctrl=vctrl,state=state,
        command_levels=list(STATES[state]),fault='',polarity_selected=False,connected_loop_acceptance=False,maximum_rows=MAX_ROWS)
 c['extra_vectors']=[f'i({line.split()[0].lower()})' for line in c['fixture']]
 require(len(rows)==13 and not any(r['model']=='npn13g2' or r['model']in('ptap1','ntap1')for r in rows),'Exactly13 devices, zeroHBT and zero contacts')
 require(sum(len(r['nets'])for r in rows)==47,'Complete47 terminal census')
 require(n.vectors(rows,c['extra_vectors'])==composition['vectors'] and len(composition['vectors'])==27,'Exact27 ordered observations')
 return c,rows,texts

def measurement(data,c):
 t=data['time'];start,end=c['window_s'];mask=(t>=start)&(t<=end)
 require(mask.any(),'Settled13 pump samples')
 expected={'v(up)':c['command_levels'][0],'v(down)':c['command_levels'][1],
           'v(vctrl)':c['vctrl'],'v(avdd)':2.3,'v(dvdd)':2.5}
 checks={key:bool(np.max(abs(data[key][mask]-value))<=1e-9)for key,value in expected.items()}
 windows=[]
 for lo,hi in [(start,end),(4e-9,14e-9),(14e-9,24e-9),(24e-9,34e-9)]:
  select=(t>=lo)&(t<=hi);require(select.any(),'Each declared13 current window')
  values={}
  for key,value in data.items():
   if key.startswith('i('):
    charge=float(n.common.integrate(t,value,lo,hi))
    values[key]=dict(min_a=float(value[select].min()),max_a=float(value[select].max()),charge_c=charge,mean_a=charge/(hi-lo))
  require(all(key in values for key in ['i(vdd)','i(vddiv)','i(vup)','i(vdown)','i(vctrl)']),'All five actual boundary currents')
  windows.append(dict(interval_s=[lo,hi],currents=values))
 return dict(passed=all(checks.values()),checks=checks,state=c['state'],vctrl_external_v=c['vctrl'],windows=windows,
             full_capture_extrema={key:[float(value.min()),float(value.max())]for key,value in data.items() if key!='time'},
             current_sign_control_required=True,matched570_idle_baseline=False,loaded_force_computed=False,
             pump_reachability_qualified=False,polarity_selected=False,connected_loop_acceptance=False,
             scope='Ideal external command slice only. Quantitative570 subtraction requires separately established exact idle boundary matching or measured replay/error correction; no interpolation, current-force sign acceptance or loop result.')


def regular_bytes(directory):
 """Bounded conservative sample; only the exact owned FIFO may be nonregular."""
 used=0
 with os.scandir(directory)as entries:
  for entry in entries:
   metadata=entry.stat(follow_symlinks=False)
   if stat.S_ISDIR(metadata.st_mode):used+=regular_bytes(entry.path)
   elif stat.S_ISFIFO(metadata.st_mode):
    require(Path(entry.path).name=='stream.fifo'and Path(entry.path).parent.parent==NATIVE_ROOT,'Only exact direct-point stream FIFO')
   else:
    require(stat.S_ISREG(metadata.st_mode),'No linked or special native evidence')
    used+=metadata.st_size
 return used


def sampled_bytes(directory):
 directory=Path(directory)
 if not directory.exists():
  require(not directory.is_symlink(),'No dangling native evidence symlink')
  return 0
 require(not directory.is_symlink(),'No native evidence root symlink')
 for attempt in range(4):
  try:return regular_bytes(directory)
  except FileNotFoundError:
   if attempt==3:raise
 raise AssertionError('unreachable')


def guard(folder,pending=0,*,terminal_tail=False):
 folder=Path(folder)
 require(folder.parent==NATIVE_ROOT and not folder.is_symlink(),'Declared fresh SSD point root')
 require(B.stat().st_dev!=Path('/dev/shm').stat().st_dev,'SSD native storage')
 free=shutil.disk_usage('/dev/shm').free;ssd_free=shutil.disk_usage(B).free
 reserve=RECEIPT_RESERVE if not terminal_tail else RECEIPT_RESERVE-FAILED_TAIL_RESERVE
 if terminal_tail:
  # This branch is only reached after an exception and always re-raises it.
  # Close already-received bytes from the reserved space even if the trigger
  # was a shared/SSD floor violation. It cannot make a failed point pass.
  require(0<=pending<=FAILED_TAIL_RESERVE,'Reserved failed-tail bytes only')
  require(ssd_free>=pending+reserve,'Failed-tail physical space and receipt reserve')
 else:
  require(free>=FLOOR,'Shared512MiB reserve')
  require(ssd_free>=SSD_FLOOR+pending+reserve,'SSD1GiB continuous and terminal reserve')
 point=sampled_bytes(folder);total=sampled_bytes(NATIVE_ROOT)
 require(point+pending+reserve<=POINT_LIMIT,'Point64MiB byte cap and final receipts')
 require(total+pending+reserve<=AGGREGATE_LIMIT,'Aggregate1GiB byte cap including failures')
 return free,total


class Meter(stream.Meter):
    """Exact inherited MOS/passive formulas; thirteen devices and zero contacts/HBT."""

    def __init__(self, columns, rows, c):
        self.contacts = [r for r in rows if r["model"] in ("ptap1", "ntap1")]
        super().__init__(columns, [r for r in rows if r not in self.contacts], c, OBS)
        self.contact_max = {r["path"]: 0.0 for r in self.contacts}

    def push(self, block):
        require(self.count + len(block) <= MAX_ROWS, "Bounded120000 native rows including adaptive extras")
        super().push(block)
        for row in self.contacts:
            values = [
                block[:, self.names.index(f"v({x})")]
                if x != "0"
                else np.zeros(len(block))
                for x in row["nets"]
            ]
            self.contact_max[row["path"]] = max(
                self.contact_max[row["path"]], float(abs(values[0] - values[1]).max())
            )

    def finish(self):
        safety, data, grid = super().finish()
        for row in self.contacts:
            vmax = self.contact_max[row["path"]]
            safety["all_device_bounds"].append(
                dict(
                    path=row["path"],
                    model=row["model"],
                    max_capture_terminal_difference=vmax,
                    voltage_limit=3.3,
                    inferred_ohmic_peak_a=vmax / float(row["params"]["r"]),
                    contact_current_qualified=False,
                    passed=vmax <= 3.3,
                )
            )
        safety["passed"] = safety["passed"] and all(
            r["passed"] for r in safety["all_device_bounds"]
        )
        require(len(safety["all_device_bounds"]) == 13, "Every device screen retained")
        return safety, data, grid


def deck(c, rows, texts):
    lines = ["Pump13 exact subset ideal-command diagnostic; no loaded-force or loop acceptance"]
    lines += [
        f'.lib "{n.MODELS}/corner{k}.lib" {v}'
        for k, v in [
            ("HBT", "hbt_typ"),
            ("RES", "res_typ"),
            ("CAP", "cap_typ"),
            ("MOShv", "mos_tt"),
            ("MOSlv", "mos_tt"),
        ]
    ]
    lines += [f'.include "{p}"' for p in texts]
    lines += [".temp 27", ".options reltol=1e-4 abstol=1e-12", *c["fixture"]]
    for model, path, ports in c["roots"]:
        lines.append(path + " " + " ".join(ports) + " " + model)
    lines += [
        f".tran {c['step_s']:.12g} {c['stop_s']:.12g} 0 {c['step_s']:.12g}",
        ".control",
    ]
    lines += ["pre_osdi " + str(x) for x in n.OSDI]
    lines += [
        "set filetype=binary",
        "save " + " ".join(n.vectors(rows, c["extra_vectors"])),
    ]
    for r in rows:
        if r["model"] == "npn13g2":
            name = "q." + r["path"] + ".qnpn13g2"
            lines += [
                f"alter @{name}[off] = 1",
                "echo NSSOC_NATIVE_FLAG_BEGIN " + name,
                "show " + name + " : off",
                "echo NSSOC_NATIVE_FLAG_END",
            ]
    lines += [
        "op",
        "write op.raw all",
        "run stream.fifo",
        "setplot",
        "display",
        "rusage space",
        "quit",
        ".endc",
        ".end",
        "",
    ]
    return "\n".join(lines)


def run_native(out, rows, c):
    fifo = out / "stream.fifo"
    os.mkfifo(fifo)
    keep = os.open(fifo, os.O_RDWR)
    reader = fifo.open("rb")
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in ("GH_TOKEN", "GITHUB_TOKEN", "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME")
    }
    env.update(SPICE_SCRIPTS=str(out), RAYON_NUM_THREADS="1", OMP_NUM_THREADS="1")
    start, proc, pool = time.monotonic(), None, None
    free_min, own_peak = guard(out)
    affinity = None

    def close_keep():
        nonlocal keep
        if keep is not None:
            os.close(keep)
            keep = None

    with life.ProcessOwner(out / "owned-processes.json") as owner:
        try:
            with (out / "run.log").open("x") as log:
                proc = owner.launch(
                    "native",
                    [str(n.NG), "-n", "-b", "bench.cir"],
                    cwd=out,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=native_limit,
                )
                affinity = sorted(os.sched_getaffinity(proc.pid))
                require(affinity == [10], "Actual native CPU10 affinity")
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                def consume():
                    try:
                        with reader:
                            return capture(reader, out, rows, c)
                    except BaseException as error:
                        owner.request_cancel(error)
                        raise

                future = pool.submit(consume)
                while True:
                    if future.done():
                        result = future.result()
                    owner.check()
                    free, used = guard(out)
                    free_min, own_peak = min(free_min, free), max(own_peak, used)
                    if proc.poll() is not None:
                        close_keep()
                        require(proc.returncode == 0, "Native nonzero exit")
                        if future.done():
                            result = future.result()
                            owner.complete(proc)
                            owner.check()
                            free, used = guard(out)
                            free_min, own_peak = min(free_min, free), max(own_peak, used)
                            break
                    owner.cancelled.wait(0.1)
        except BaseException as error:
            owner.stop_failed(error)
            close_keep()
            raise
        finally:
            close_keep()
            if pool is not None:
                pool.shutdown(wait=True)
            reader.close()
            n.common.atomic(
                out / "execution.json",
                dict(
                    returncode=None if proc is None else proc.poll(),
                    elapsed_seconds=time.monotonic() - start,
                    elapsed_watchdog_seconds=None,
                    address_space_limit_bytes=2 * 1024**3,
                    actual_affinity=affinity,
                    min_shared_free_bytes=free_min,
                    max_own_bytes=own_peak,
                ),
            )
    owner.check()
    free, used = guard(out)
    fifo.unlink()
    return result


def run(out, case, fault=""):
    c, rows, texts = config(case, fault)
    require(
        not out.exists() and out.parent == NATIVE_ROOT and not out.is_symlink(),
        "Fresh SSD point output",
    )
    require(shutil.disk_usage("/dev/shm").free >= 1024**3, "Native1GiB entry floor")
    _, owned = guard(out)
    require(owned + 24 * 1024**2 < OWN_LIMIT, "24MiB launch headroom")
    require(n.common.sha(n.NG) == n.common.NG47_SHA, "Exact ng47")
    require(
        {p.name: n.common.sha(p) for p in n.OSDI} == n.common.OSDI_PINS, "Exact OSDIs"
    )
    inventory = {p.name: n.common.sha(p) for p in sorted(n.MODELS.glob("*.lib"))}
    require(
        hashlib.sha256(
            json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == n.common.MODEL_INVENTORY_SHA,
        "Exact PDK model inventory",
    )
    NATIVE_ROOT.mkdir(exist_ok=True)
    out.mkdir()
    for name, text in texts.items():
        (out / name).write_text(text)
    (out / "spinit").write_text("set num_threads=1\n")
    (out / "bench.cir").write_text(deck(c, rows, texts))
    paths = [
        SOURCE,
        n.NG,
        *n.OSDI,
        *n.MODELS.glob("*.lib"),
        *[Path(p) for p in c["sources"]],
        *[Path(p) for p in stream.previous.method_inventory()],
        *out.iterdir(),
    ]
    pins = {str(p.resolve()): n.common.pin(p) for p in paths}
    record = dict(
        status="RUNNING",
        inputs=pins,
        config=c,
        devices=rows,
        raw_estimate_bytes=int(c["stop_s"] / c["step_s"] + 32)
        * (len(n.vectors(rows, c["extra_vectors"])) + 1)
        * 8,
        limits="Finite27C pump13 ideal-command slice only;27 saved vectors/28columns,120000-row bound, SSD64MiB percase/1GiB aggregate. No matched-idle570 subtraction, reachability, polarity, PVT or lock acceptance.",
    )
    n.common.atomic(out / "result.json", record)
    try:
        record.update(run_native(out, rows, c))
        # Exact zero HBT/OFF census, same zero-source OP and clean-log gate.
        record.update(startup_proof(out, dict(devices=rows, config=c)))
        require(
            all(n.common.pin(p) == pin for p, pin in pins.items()),
            "All inputs unchanged after native",
        )
        good = record["safety"]["passed"] and record["measurement"]["passed"]
        record["status"] = (
            "PASS_NATIVE_PUMP13_IDEAL_COMMAND_POINT"
            if good
            else "FAIL_NATIVE_PUMP13_IDEAL_COMMAND_POINT"
        )
        record["accepted_actual_fault"] = bool(
            fault and record["safety"]["passed"] and not record["measurement"]["passed"]
        )
    except BaseException as error:
        record.update(status="ERROR_NATIVE_OR_CAPTURE", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): n.common.pin(p)
            for p in out.rglob("*")
            if p.is_file() and p.name != "result.json"
        }
        n.common.atomic(out / "result.json", record)
    return record


def capture(source,out,rows,c):
 expected=n.vectors(rows,c['extra_vectors'])
 seen=bytearray()
 class HeaderPrefix:
  def readline(self,limit):
   line=source.readline(limit);seen.extend(line);return line
 try:
  header,meta=life.tiny.parse_header(HeaderPrefix(),expected)
  require(meta['declared_points']==0 and sys.byteorder=='little','NativeFIFO format')
  require(len(header)<=HEADER_CAP,'Bounded native header')
  meter=Meter(meta['columns'],rows,c);width=len(meta['columns'])*8
  require(width==28*8,'Exact13 full raw row width')
 except BaseException as error:
  # The exact inherited parser reads at most 65535+4097 header bytes.
  # Preserve even a rejected early header, but never consume unread FIFO data.
  require(len(seen)<=65536+4097,'Inherited parser bounded failed header')
  blob=gzip.compress(bytes(seen),mtime=0);free,_=guard(out,len(blob),terminal_tail=True)
  with(out/'wave.raw.gz').open('xb',buffering=0)as dst:
   left=blob
   while left:
    count=dst.write(left);require(count is not None and count>0,'Complete failed-header write progress');left=left[count:]
   dst.flush();os.fsync(dst.fileno())
  n.common.atomic(out/'capture-failure.json',dict(status='FAILED_HEADER_PREFIX_RETAINED',error=repr(error),received_raw_bytes=len(seen),received_raw_sha256=hashlib.sha256(seen).hexdigest(),failure_shared_free_bytes=free,resumable_solver_checkpoint=False))
  raise
 del seen
 raw_limit=MAX_ROWS*width+HEADER_CAP+64
 pending=bytearray();whole=hashlib.sha256(header);payload=hashlib.sha256()
 compressor=zlib.compressobj(level=6,wbits=31);raw_bytes=len(header);queued=b'';flushed=False
 with(out/'wave.raw.gz').open('xb',buffering=0)as dst:
  def write(blob):
   nonlocal queued
   require(not queued,'No overwritten queued compressed bytes')
   queued=blob;guard(out,len(blob))
   while queued:
    count=dst.write(queued);require(count is not None and count>0,'Complete compressed write progress');queued=queued[count:]
  try:
   write(compressor.compress(header))
   while raw:=source.read(65536):
    whole.update(raw);raw_bytes+=len(raw)
    write(compressor.compress(raw));pending.extend(raw)
    require(raw_bytes<=raw_limit,'Bounded native raw bytes including header and adaptive samples')
    count=len(pending)//width
    if count:
     blob=bytes(pending[:count*width]);payload.update(blob)
     meter.push(np.frombuffer(blob,'<f8').reshape(count,-1));del pending[:count*width]
   tail=compressor.flush();flushed=True;write(tail);dst.flush();os.fsync(dst.fileno())
  except BaseException as error:
   # Preserve every byte already read, including a queued compressed block and
   # zlib's buffered tail. This is a failed finite prefix, never a resumable
   # solver checkpoint or a valid complete waveform.1MiB is reserved for it.
   tail=queued+(b''if flushed else compressor.flush());queued=b'';flushed=True
   require(len(tail)<=FAILED_TAIL_RESERVE,'Bounded gzip failure tail')
   failure_shared_free,_=guard(out,len(tail),terminal_tail=True)
   failure_ssd_free=shutil.disk_usage(B).free
   tail_left=tail
   while tail_left:
    count=dst.write(tail_left);require(count is not None and count>0,'Complete failed-tail write progress');tail_left=tail_left[count:]
   dst.flush();os.fsync(dst.fileno())
   n.common.atomic(out/'capture-failure.json',dict(status='FAILED_CAPTURE_PREFIX_RETAINED',error=repr(error),received_raw_bytes=raw_bytes,received_raw_sha256=whole.hexdigest(),complete_rows_reduced=meter.count,pending_bytes=len(pending),failed_tail_bytes=len(tail),failure_shared_free_bytes=failure_shared_free,failure_ssd_free_bytes=failure_ssd_free,failed_only_reserved_finalization=True,resumable_solver_checkpoint=False))
   raise
 require(bytes(pending)==str(meter.count).encode(),'Exact native sample-count trailer')
 safety,data,grid=meter.finish()
 digest,total=hashlib.sha256(),0
 with gzip.open(out/'wave.raw.gz','rb')as src:
  while part:=src.read(1024**2):
   guard(out);digest.update(part);total+=len(part)
 require(total==raw_bytes and digest.hexdigest()==whole.hexdigest(),'Lossless gzip all-byte replay')
 guard(out)
 return dict(columns=meta['columns'],raw_table=meta['raw_table'],rows=meter.count,values=meter.count*len(meta['columns']),raw_bytes=raw_bytes,raw_sha256=whole.hexdigest(),payload_sha256=payload.hexdigest(),safety=safety,measurement=measurement(data,c),time_grid=grid,compression_readback=True,storage=dict(filesystem='SSD',per_point_bytes=POINT_LIMIT,aggregate_bytes=AGGREGATE_LIMIT,maximum_rows=MAX_ROWS,raw_limit_bytes=raw_limit,file_fsync_at_close=True,live_power_loss_tail_durable=False,resumable_solver_checkpoint=False))


def startup_proof(folder, prior):
    log = (folder / "run.log").read_text()
    bad = [
        line
        for line in log.splitlines()
        if re.search(
            r"warning|error|failed|singular|timestep too small|gmin stepping|source stepping",
            line,
            re.I,
        )
    ]
    require(not bad and "ngspice-47 done" in log, "Strict clean native diagnostics")
    flags = [
        "q." + r["path"] + ".qnpn13g2"
        for r in prior["devices"]
        if r["model"] == "npn13g2"
    ]
    observed = re.findall(
        r"(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$", log
    )
    require(
        [x[0] for x in observed] == flags and len(flags) == 0,
        "Exact zero HBT/OFF census in13 subset",
    )
    for name, body in observed:
        require(
            re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body) == [name[:21]]
            and re.findall(r"(?m)^\s*off\s+([01])\s*$", body) == ["1"],
            "Native OFF readback",
        )
    op = n.read_raw(
        folder / "op.raw",
        n.vectors(prior["devices"], prior["config"]["extra_vectors"]),
        False,
    )
    require(
        all(len(v) == 1 and abs(v[0]) <= 1e-10 for v in op.values()),
        "Exact finite zero-source OP",
    )
    return dict(zero_source_op=True, native_off_flags=flags, clean_diagnostics=True)


OWN_LIMIT=AGGREGATE_LIMIT
def native_limit():
    # Bound BOTH native regular files; compressed FIFO data has its own cap.
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024**2,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {10})

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--case',choices=CASES,required=True);a=ap.parse_args()
 out=NATIVE_ROOT/(a.case+'-01')
 result=run(out,a.case)
 print(result['status'])
 raise SystemExit(0 if result['status']=='PASS_NATIVE_PUMP13_IDEAL_COMMAND_POINT' else 1)
