# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent complete native waveform reduction for the finite emitter-array-local wire experiment."""
from pathlib import Path
import gzip, hashlib, io, json, resource, tarfile
import numpy as np
resource.setrlimit(resource.RLIMIT_AS, (1536*1024**2,)*2)
B=Path(__file__).resolve().parent
def pin(p):
    with p.open("rb") as f:
        return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
rows=[]
for tag,name in [("wired06","ring-via-array-local-vco-v4-wired06-01.tar.xz")]:
    a=B/name
    v=json.loads((B/f"validation-{tag}-01.json").read_text())
    rel=json.loads((B/f"release-{tag}-01.json").read_text())
    asset=next(x for x in rel["assets"] if x["name"]==name)
    assert asset["authenticated_roundtrip"] and asset["anonymous_roundtrip"]
    assert pin(a)=={k:asset[k] for k in ("bytes","sha256")}
    members={}
    with tarfile.open(a,"r:xz") as t:
        for m in t:
            assert m.isfile() and m.name not in members
            members[m.name]=dict(bytes=m.size,sha256=hashlib.file_digest(t.extractfile(m),"sha256").hexdigest())
    base=f"native/nssoc-vco-v4-local-v7-powered-{tag}-01/distributed_wire/"
    with tarfile.open(a,"r:xz") as t:
        contract=json.load(t.extractfile(base+"contract.json"))
        native=json.load(t.extractfile(base.replace("distributed_wire/","")+"result.json"))
        compressed=t.extractfile(base+"wave.dat.gz").read()
    raw=gzip.decompress(compressed)
    hdr=raw.split(b"\n",1)[0].decode().split()
    assert [x.lower() for x in hdr[1:]]==[x.lower() for x in contract["vectors"]]
    data=np.loadtxt(io.BytesIO(raw),skiprows=1)
    assert data.shape==(12011,len(hdr)) and np.isfinite(data).all()
    times=data[:,0];assert np.all(np.diff(times)>0) and abs(times[-1]-12e-9)<1e-23
    ix={n.lower():i for i,n in enumerate(hdr)}
    mask=(times>=6e-9)&(times<=times[-1]);assert int(mask.sum())==6001
    signals=[]
    for expected in v["raw_replay"]["audit"]["metrics"]["signals"]:
        p,n=expected["vectors"];s=(data[:,ix[p.lower()]]-data[:,ix[n.lower()]])[mask];tt=times[mask]
        cross=np.flatnonzero((s[:-1]<=0)&(s[1:]>0))
        edges=tt[cross]-s[cross]*(tt[cross+1]-tt[cross])/(s[cross+1]-s[cross])
        freq=float(1/np.mean(np.diff(edges))) if len(edges)>1 else None
        row=dict(vectors=[p,n],minimum_differential_v=float(s.min()),maximum_differential_v=float(s.max()),rising_edges=len(edges),mean_frequency_hz=freq)
        assert len(edges)==expected["rising_edges"] and np.allclose(edges,expected["rising_edge_times"],rtol=0,atol=1e-23)
        for k in ("minimum_differential_v","maximum_differential_v"):assert abs(row[k]-expected[k])<1e-12
        assert freq is None and expected["mean_frequency_hz"] is None or abs(freq-expected["mean_frequency_hz"])<.001
        signals.append(row)
    bounds=[]
    for d in contract["hbts"]:
        vce=data[:,ix[d["C"].lower()]]-data[:,ix[d["E"].lower()]]
        current=np.abs(data[:,ix[d["current"].lower()]])/d["Nx"]
        bounds.append(dict(id=d["id"],min_vce=float(vce[mask].min()),max_vce=float(vce[mask].max()),all_time_max_vce=float(vce.max()),all_time_min_vce=float(vce.min()),current_per_emitter=float(current[mask].max())))
    assert len(bounds)==30
    assert all(x["min_vce"]>=.4 and x["all_time_max_vce"]<=1.6 and x["current_per_emitter"]<=.003 for x in bounds)
    for k,value in [("min_vce",min(x["min_vce"] for x in bounds)),("max_vce",max(x["max_vce"] for x in bounds)),("full_time_max_vce",max(x["all_time_max_vce"] for x in bounds)),("peak_abs_current_per_emitter_a",max(x["current_per_emitter"] for x in bounds))]:
        assert abs(value-v["raw_replay"]["audit"]["metrics"][k])<1e-12
    public=next(x for x in signals if [s.lower() for s in x["vectors"]]==["v(clkp)","v(clkn)"])
    swing_pass=public["minimum_differential_v"]<=-.3 and public["maximum_differential_v"]>=.3
    assert swing_pass
    complete_cycles=[]
    public_diff=(data[:,ix["v(clkp)"]]-data[:,ix["v(clkn)"]])
    public_edges=next(x for x in v["raw_replay"]["audit"]["metrics"]["signals"] if [n.lower() for n in x["vectors"]]==["v(clkp)","v(clkn)"])["rising_edge_times"]
    for a_edge,b_edge in zip(public_edges,public_edges[1:]):
        window=(times>=a_edge)&(times<=b_edge)
        minimum=float(public_diff[window].min());maximum=float(public_diff[window].max())
        assert minimum<=-.3 and maximum>=.3
        complete_cycles.append(dict(start_s=a_edge,end_s=b_edge,minimum_v=minimum,maximum_v=maximum))
    assert len(complete_cycles)==44
    public["complete_cycles"]=complete_cycles
    rows.append(dict(tag=tag,archive=pin(a),release=pin(B/f"release-{tag}-01.json"),validation=pin(B/f"validation-{tag}-01.json"),all_member_readback=members,raw=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),compressed=dict(bytes=len(compressed),sha256=hashlib.sha256(compressed).hexdigest()),samples=12011,active_samples=6001,signals=signals,bounds=bounds,public_clock=public,swing_gate="PASS_FINITE_PLUS_MINUS_300mV" if swing_pass else "FAIL_UNCHANGED_PLUS_MINUS_300mV"))
    del raw,compressed,data
r=dict(status="PASS_INDEPENDENT_ALL_SAMPLE_EMITTER_RETURN_V7_WAVE_AND_44_CYCLES",method=pin(Path(__file__)),results=rows,native_reruns=0,scope="Every native sample, all30HBT bounds and44complete public output cycles remeasured independently with NumPy; prior versions remain unchanged. Not steady8GHz, qualifiedRC/ESD or fullPLL/CDR.")
(B/"root-wave-peer.json").write_text(json.dumps(r,indent=2)+"\n")
print(r["status"])
