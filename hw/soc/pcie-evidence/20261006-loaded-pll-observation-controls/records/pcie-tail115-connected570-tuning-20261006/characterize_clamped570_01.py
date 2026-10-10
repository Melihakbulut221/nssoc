# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Three finite clamped570 diagnostics; no polarity/acquisition acceptance."""
import argparse, concurrent.futures, copy, gzip, hashlib, importlib.util, json
import os, resource, shutil, stat, subprocess, sys, time, types, zlib
from pathlib import Path
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent
S=R/'hw/soc/out/pcie-tail115-connected570-source-20261006'
P16=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006'
sys.path.insert(0,str(R/'scripts'));sys.path.insert(0,str(P16))
import characterize_sixteenthstep01 as previous
core=previous.core;n=previous.n;stream=previous.stream;require=previous.require;life=previous.life
HYBRID=previous.HYBRID;PINS=previous.PINS;SOURCE=S/'loop-negative01.spice'
NATIVE_ROOT=B/'native01'
POINT_LIMIT=1280*1024**2;AGGREGATE_LIMIT=4*1024**3
FLOOR=512*1024**2;SSD_FLOOR=1024**3;RECEIPT_RESERVE=2*1024**2
MAX_ROWS=120000;HEADER_CAP=4*1024**2;FAILED_TAIL_RESERVE=1024**2
POINTS=(0.5,0.6,0.7)
OBS=[x.replace('v(xchain.','v(xloop.xchain.') for x in previous.OBS]
OBS+=['v(vctrl)','i(vctrl)','v(up)','v(down)','v(reset)','v(reference)']
assert len(OBS)==len(set(OBS))

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def config(vctrl=0.6,fault=''):
 require(vctrl in POINTS and fault=='','Only three named nominal tuning diagnostics')
 freeze=json.loads((S/'source-freeze01.json').read_text())
 require(pin(S/'source-freeze01.json')==dict(bytes=35763,sha256='961db3c0f582da14ddfa73cd3da648e3ab10b3424e362a7df9dda55c765f400a'),'Frozen570 source contract')
 for path,value in freeze['inputs'].items():require(pin(path)==value,'570 source input drift '+path)
 peer=json.loads((S/'source-contract-peer-root01.json').read_text())
 require(peer['status']=='PASS_SOURCE_ONLY_570_COMPOSITION_AND_TUNING_CONTRACT'and peer['findings']==[]and peer['freeze']==pin(S/'source-freeze01.json'),'570 independent source gate')
 composition=json.loads((S/'composition01.json').read_text());variant=composition['variants']['negative']
 rows=copy.deepcopy(variant['devices']);texts={p.name:p.read_text()for p in sorted((S/'includes01').glob('*.spice'))}
 texts[SOURCE.name]=SOURCE.read_text()
 fixture=list(variant['fixture'])
 old='VRESET reset 0 PWL(0 0 500p 2.5 8n 2.5 8.1n 0)'
 require(fixture.count(old)==1,'Exact original PFD reset fixture')
 fixture[fixture.index(old)]='VRESET reset 0 PWL(0 0 500p 2.5)'
 fixture.append(f'VCTRL vctrl 0 PWL(0 0 500p {vctrl:.1f})')
 c=dict(case='clamped570_pfd_idle_tuning_only',sources=[str(S/'source-freeze01.json'),str(S/'source-contract-peer-root01.json'),str(S/'composition01.json'),str(S/'tuning-contract01.json'),str(SOURCE),str(Path(__file__)),*[str(S/'includes01'/name)for name in texts if name!=SOURCE.name]],roots=[variant['root']],fixture=fixture,step_s=3.125e-13,stop_s=34e-9,window_s=[4e-9,34e-9],minimum_states=8,vctrl=vctrl,fault='',polarity_selected=False,connected_loop_acceptance=False,maximum_rows=MAX_ROWS)
 extras=[f'i({line.split()[0].lower()})'for line in fixture if line.startswith('V')]
 native_nodes={f'v({node})'for r in rows for node in r['nets']if node!='0'}
 for vector in OBS[1:]:
  if vector not in native_nodes and vector not in extras:extras.append(vector)
 c['extra_vectors']=extras
 require(len(rows)==570 and sum(x['model']=='npn13g2'for x in rows)==64,'Complete570/64HBT census')
 require(sum(x['model']in('ptap1','ntap1')for x in rows)==31,'Complete31 contacts')
 expected=set(variant['observation_vectors'])|{'i(vctrl)'}
 actual=n.vectors(rows,extras)
 require(set(actual)==expected and len(actual)==1133,'Every source-census observation plus actual clamp current')
 return c,rows,texts

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
 require(point+pending+reserve<=POINT_LIMIT,'Point1280MiB byte cap and final receipts')
 require(total+pending+reserve<=AGGREGATE_LIMIT,'Aggregate4GiB byte cap including failures')
 return free,total

def measurement(data,c):
 observed={key.replace('v(xloop.xchain.','v(xchain.'):value for key,value in data.items()}
 result=previous.core.old.measure_chain(observed,c)
 require(len(result['checks'])==13,'Original thirteen division predicates')
 result['vctrl_external_v']=c['vctrl'];result['connected_pll']=False
 t=data['time'];mask=(t>=c['window_s'][0])&(t<=c['window_s'][1]);require(mask.any(),'Settled570 tuning samples')
 tuning=dict(pfd_up_idle=bool(np.max(abs(data['v(up)'][mask]))<=0.25),pfd_down_idle=bool(np.max(abs(data['v(down)'][mask]))<=0.25),external_reset_asserted=bool(np.min(data['v(reset)'][mask])>=2.25),actual_clamp_level=bool(np.max(abs(data['v(vctrl)'][mask]-c['vctrl']))<=1e-9))
 result['tuning_checks']=tuning;result['division_passed']=result['passed'];result['passed']=result['passed']and all(tuning.values())
 result['polarity_selected']=False;result['quasistatic_pump_reachability_measured']=False
 result['clamp_current_sign']='Positive i(VCTRL) is current sunk by external ideal clamp; sign control is required before combining with separate pump force measurements.'
 result['windows']=[]
 for start,end in [(4e-9,14e-9),(14e-9,24e-9),(24e-9,34e-9)]:
  item=dict(interval_s=[start,end],clamp_charge_c=float(n.common.integrate(t,data['i(vctrl)'],start,end)),vctrl_min_v=float(data['v(vctrl)'][(t>=start)&(t<=end)].min()),vctrl_max_v=float(data['v(vctrl)'][(t>=start)&(t<=end)].max()))
  item['clamp_mean_a']=item['clamp_charge_c']/(end-start)
  for label,signal,threshold in [('vco',data['v(clkp)']-data['v(clkn)'],0),('cml',data['v(qp)']-data['v(qn)'],0),('feedback',data['v(fb)'],0.6)]:
   edges=[x for x in n.common.crossings(t,signal,threshold)if start<=x<end]
   item[label]=dict(edges_s=edges,frequency_hz=None if len(edges)<2 else float(1/np.mean(np.diff(edges))))
  result['windows'].append(item)
 return result


class Meter(stream.Meter):
    """Frozen539 non-contact device screens plus explicit31 contact terminal-voltage screens."""

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
        require(len(safety["all_device_bounds"]) == 570, "Every device screen retained")
        return safety, data, grid


def deck(c, rows, texts):
    lines = ["Clamped570 full-device PFD-idle tuning diagnostic; not a connected-loop run"]
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


def run(out, vctrl, fault=""):
    c, rows, texts = config(vctrl, fault)
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
        *[HYBRID / x for x in PINS],
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
        limits="Finite27C clamped570/PFD-idle tuning only;1133 saved vectors,120000-row hard bound, SSD1280MiB perpoint/4GiB aggregate with failures retained; no polarity, pump reachability, lock, PVT or fullPHY qualification.",
    )
    n.common.atomic(out / "result.json", record)
    try:
        record.update(run_native(out, rows, c))
        # Same 64 actual native OFF readbacks, zero-source OP and strict clean-log gate.
        record.update(stream.previous.startup_proof(out, dict(devices=rows, config=c)))
        require(
            all(n.common.pin(p) == pin for p, pin in pins.items()),
            "All inputs unchanged after native",
        )
        good = record["safety"]["passed"] and record["measurement"]["passed"]
        record["status"] = (
            "PASS_NATIVE_CLAMPED570_TUNING_POINT"
            if good
            else "FAIL_NATIVE_CLAMPED570_TUNING_POINT"
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


# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# This fragment is included literally in the complete reviewed driver.
def capture(source,out,rows,c):
 expected=n.vectors(rows,c['extra_vectors'])
 seen=bytearray()
 class HeaderPrefix:
  def readline(self,limit):
   line=source.readline(limit);seen.extend(line);return line
 try:header,meta=life.tiny.parse_header(HeaderPrefix(),expected)
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
 require(meta['declared_points']==0 and sys.byteorder=='little','NativeFIFO format')
 require(len(header)<=HEADER_CAP,'Bounded native header')
 meter=Meter(meta['columns'],rows,c);width=len(meta['columns'])*8
 require(width==1134*8,'Exact570 full raw row width')
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


OWN_LIMIT=AGGREGATE_LIMIT
native_limit=previous.native_limit

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--vctrl',type=float,choices=POINTS,required=True);a=ap.parse_args()
 out=NATIVE_ROOT/f'v{int(round(a.vctrl*100)):03d}-01'
 result=run(out,a.vctrl)
 print(result['status'])
 raise SystemExit(0 if result['status']=='PASS_NATIVE_CLAMPED570_TUNING_POINT'else 1)
