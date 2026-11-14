# SPDX-License-Identifier: Apache-2.0
"""Frozen whole-loaded stimulus/gates on actual650 physical bindings."""
import os,re,hashlib,traceback
from pathlib import Path
import numpy as np
UI=125e-12;START=2e-9;STOP=START+258*UI;STEP=.3125e-12
CASES=['nominal_early','nominal_late','hot_early','hot_late','cold_early','cold_late','constant_zero','constant_one','clock_stopped','vi_bias_off']
BIASES=['ira','irb','irc','ird','irx','iry','ibda','ibdc','ibs0','ibs1']
CORNERS={
 'nominal':dict(temperature=27,scale=1.,res='res_typ',cap='cap_typ',mos='mos_tt'),
 'hot_low':dict(temperature=125,scale=.95,res='res_wcs',cap='cap_wcs',mos='mos_ss'),
 'cold_high':dict(temperature=-40,scale=1.05,res='res_bcs',cap='cap_bcs',mos='mos_ff')}

def pwl(points):
    assert all(a[0]<b[0]for a,b in zip(points,points[1:]))
    return 'PWL(\n+ '+'\n+ '.join(f'{t:.14g} {v:.14g}'for t,v in points)+')'

def clock(scale,positive,stopped):
    low=(1.29-.15)*scale;high=(1.29+.15)*scale
    if not positive:low,high=high,low
    points=[(0,0),(.5e-9,low)];current=low
    if not stopped:
        for i in range(258):
            for at,new in [(START+(i+.5)*UI,high),(START+(i+1)*UI,low)]:
                if at+2.5e-12>=STOP:continue
                points.extend([(at-2.5e-12,current),(at+2.5e-12,new)]);current=new
    points.append((STOP,current));return pwl(points)

def shifted_data(bits,cm,amp,offset):
    value=lambda b:cm+amp*(2*b-1)
    points=[(0,0),(.5e-9,value(bits[0]))]
    for i in range(1,256):
        if bits[i]!=bits[i-1]:points.extend([(START+i*UI+offset,value(bits[i-1])),(START+i*UI+offset+5e-12,value(bits[i]))])
    points.append((STOP,value(bits[-1])));return pwl(points)

def prbs(seed):
    state=seed;bits=[]
    for _ in range(256):
        bits.append(state&1);state=((state<<1)|(((state>>6)^(state>>5))&1))&127
    assert len(set(bits))==2
    return bits

def streaming_deck(deck, contract):
    body,control=deck.split('.control\n')
    rows=control.splitlines()
    trans=[r for r in rows if r.startswith('tran ')]
    assert len(trans)==1 and '.tran ' not in body
    output='wrdata wave.dat '+' '.join(contract['vectors'])
    assert rows.count(output)==1
    assert rows.count('op')==1
    assert rows.count('wrdata op.dat '+' '.join(contract['vectors']))==1
    assert rows[-3:]==['quit','.endc','.end']
    index=rows.index(trans[0])
    assert rows[index+1]==output
    rows[index:index+2]=['set filetype=binary','run wave.raw']
    # Preserve every device/model/source/solver/save/alter statement. Move the
    # identical analysis parameters into the netlist for run's rawfile path.
    return body+'.'+trans[0]+'\n.control\n'+'\n'.join(rows)+'\n'

def read_streamed_wave(path,vectors,stop,step):
    """Strict full regular-file raw reader with bounded memory mapping."""
    path=Path(path);assert vectors and len(vectors)==len(set(vectors))
    with path.open('rb') as stream:
        parts=[]
        while True:
            row=stream.readline(1048576)
            assert row and row.endswith(b'\n'),'Incomplete native header'
            parts.append(row)
            assert sum(map(len,parts))<=1048576,'Unbounded native header'
            if row==b'Binary:\n':break
        offset=stream.tell()
    header=b''.join(parts).decode('ascii')
    def field(key):
        matches=[line.split(':',1)[1].strip() for line in header.splitlines() if line.startswith(key+':')]
        assert len(matches)==1,('Missing/duplicate raw field',key)
        return matches[0]
    assert field('Flags')=='real' and field('Plotname')=='Transient Analysis'
    width=int(field('No. Variables'));count=int(field('No. Points'))
    assert width==len(vectors)+1 and count>1
    assert header.count('Variables:\n')==1
    table=[row.split() for row in header.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
    assert len(table)==width and all(len(row)==3 for row in table)
    assert [r[0] for r in table]==list(map(str,range(width)))
    assert table[0]==['0','time','time']
    aliases={'time':'time'}
    for name in vectors:
        for native in ([name,'i('+name+')'] if name.startswith('@') else [name]):
            assert native not in aliases or aliases[native]==name
            aliases[native]=name
    names=[]
    for _,native,kind in table:
        assert native in aliases,('Unexpected native vector',native)
        logical=aliases[native]
        expected='time' if logical=='time' else 'voltage' if logical.startswith('v(') else 'current'
        assert kind==expected,(native,kind,expected)
        names.append(logical)
    assert len(set(names))==width and set(names)=={'time',*vectors}
    assert path.stat().st_size-offset==count*width*8,'Truncated/extra raw payload or incorrect header row count'
    matrix=np.memmap(path,mode='r',dtype='<f8',offset=offset,shape=(count,width))
    for first in range(0,count,1024):
        assert np.isfinite(matrix[first:first+1024]).all(),'Nonfinite native sample'
    t=matrix[:,0]
    assert t[0]==0 and abs(t[-1]-stop)<1e-18
    delta=np.diff(t)
    assert np.all(delta>0) and np.max(delta)<=step*1.00001
    values={n:matrix[:,i] for i,n in enumerate(names) if i}
    return t,values,dict(header_rows=count,columns=width,header_bytes=offset,
        raw_bytes=path.stat().st_size,raw_sha256=digest(path),
        start_s=float(t[0]),end_s=float(t[-1]),max_step_s=float(delta.max()),
        logical_vector_order=names,complete_unmodified_rows=True,
        method='Memory-mapped full binary raw; every original vector retained; no interpolation/decimation')

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def native_save_commands(vectors):
    # ngspice command-table limits: save LOTS=1000; wrdata NLOTS=10000.
    # Preserve existing small-capture decks byte-for-byte. Large trees need
    # bounded save commands, without omitting or reordering any observations.
    assert vectors and len(vectors)==len(set(vectors))
    assert len(vectors)+1 <= 10000, 'wrdata argument limit; never truncate capture'
    size=len(vectors) if len(vectors)<=1000 else 128
    return ['save '+' '.join(vectors[i:i+size]) for i in range(0,len(vectors),size)]

def native_diagnostics(log, profile='default'):
    """Keep real diagnostics; exempt only two labels in verified option output."""
    if profile != 'default':
        verify_solver_options(log, profile)
    inside = False
    result = []
    benign = {'Truncation error correction, charge based, is selected:',
              'diaggmin (stepping) = 0'}
    for line in log.splitlines():
        if line.strip() == 'NSSOC_SOLVER_OPTIONS_BEGIN':
            inside = True
        elif line.strip() == 'NSSOC_SOLVER_OPTIONS_END':
            inside = False
        if profile != 'default' and inside and line.strip() in benign:
            continue
        if any(w in line.lower() for w in ('warning','error','nan','singular','stepping','too small','jmax','vmax')):
            result.append(line)
    return result

def option_values(text,backend):
    assert ('KLU' in text) if backend=='klu' else ('Sparse 1.3' in text)
    numeric={}
    for label,pattern in {'reltol':r'reltol(?:\s+\(current\))?','abstol':r'abstol(?:\s+\(current\))?','vntol':r'vntol(?:\s+\(voltage\))?','trtol':'trtol','maxord':r'(?:maxord|maxorder)','itl4':r'itl4(?:\s+\(transient iterations\))?'}.items():
        values=re.findall(r'(?mi)^\s*'+pattern+r'\s*=\s*(\S+)\s*$',text);assert len(values)==1,(label,values);numeric[label]=float(values[0])
    assert numeric['reltol']==1e-4 and numeric['abstol']==1e-12
    method=re.findall(r'(?mi)^\s*(?:method|integration method)\s*=\s*(\S+)\s*$',text);assert len(method)==1
    return dict(backend=backend,numeric=numeric,method=method[0],native_readback_sha256=hashlib.sha256(text.encode()).hexdigest())

def backend_readback(log,backend):
    blocks=re.findall(r'(?ms)^NSSOC_BACKEND_OPTIONS_BEGIN\s*\n(.*?)^NSSOC_BACKEND_OPTIONS_END\s*$',log)
    assert len(blocks)==1 and log.count('NSSOC_BACKEND_OPTIONS_BEGIN')==log.count('NSSOC_BACKEND_OPTIONS_END')==1,'Missing/duplicate native readback scope'
    block=blocks[0];parsed=option_values(block,backend)
    benign={'Truncation error correction, charge based, is selected:','diaggmin (stepping) = 0'}
    inside=False;scoped=[]
    for line in log.splitlines():
        if line.strip()=='NSSOC_BACKEND_OPTIONS_BEGIN':inside=True
        elif line.strip()=='NSSOC_BACKEND_OPTIONS_END':inside=False
        if inside and line.strip() in benign:continue
        scoped.append(line)
    return parsed,native_diagnostics('\n'.join(scoped)),block

def readback_controls():
    block='Sparse 1.3\nreltol (current) = 0.0001\nabstol (current) = 1e-12\nvntol (voltage) = 1e-6\ntrtol = 7\nmaxorder = 2\nitl4 (transient iterations) = 10\nIntegration method = trapezoidal\nTruncation error correction, charge based, is selected:\ndiaggmin (stepping) = 0\n'
    good='NSSOC_BACKEND_OPTIONS_BEGIN\n'+block+'NSSOC_BACKEND_OPTIONS_END\n'
    assert not backend_readback(good,'sparse')[1]
    assert not backend_readback(good.replace('Sparse 1.3','KLU'),'klu')[1]
    rejected=[]
    for name,bad in [('outside_label','diaggmin (stepping) = 0\n'+good),('inside_warning',good.replace('Sparse 1.3','Sparse 1.3\nWarning: genuine failure')),('changed_tolerance',good.replace('0.0001','0.01')),('duplicate',good+good),('missing_marker',good.replace('NSSOC_BACKEND_OPTIONS_END','')),('wrong_backend',good.replace('Sparse 1.3','KLU')),('missing_numeric',good.replace('trtol = 7\n',''))]:
        try:failed=bool(backend_readback(bad,'sparse')[1])
        except AssertionError:failed=True
        assert failed,name;rejected.append(name)
    return dict(positive=2,negative=rejected,only_verified_option_labels_exempted=True)

sha=digest
def measure_wave(bound,t,d,bits,offset,protected,r,constant,fault):
    devices=bound["groups"]["npn13g2"];mos=bound["groups"]["sg13_lv_nmos"];caps=bound["groups"]["cap_cmim"];active=t>=START
    def v(n):
        n=bound['aliases'].get(n,n)
        return np.zeros(len(t))if n=='0'else d['v('+n+')']
    def measure(p,n,expected,edges,phases,limit):
        delta=v(p)-v(n);signed=[];delays=[]
        for bit,edge in zip(expected,edges,strict=True):
            sign=2*bit-1
            for phase in phases:signed.append(float(np.interp(edge+phase*UI,t,delta))*sign)
            ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
            delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
        return dict(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),maximum_clock_to_valid_s=max(delays),clock_to_valid_by_bit_s=delays,passed=min(signed)>=.1 and max(delays)<=limit*UI)
    indices=range(1,256);current=[bits[i]for i in indices];previous=[bits[i-1]for i in indices];edge_bits=current if offset<0 else previous
    rising=[START+(i+.5)*UI for i in indices];falling=[START+i*UI for i in indices]
    expected=dict(a=current,b=edge_bits,c=previous,d=edge_bits)
    sampler_checks={tag:measure('xpd.'+tag+'qp','xpd.'+tag+'qn',expected[tag],falling if tag=='b'else rising,(.3,.6,.9),.3)for tag in 'abcd'}
    xbits=[a^b for a,b in zip(current,edge_bits,strict=True)];ybits=[a^b for a,b in zip(previous,edge_bits,strict=True)]
    comparisons=dict(x=measure('xp','xn',xbits,rising,(.6,.75,.9),.6),y=measure('yp','yn',ybits,rising,(.6,.75,.9),.6))
    delta=(v('xp')-v('xn'))-(v('yp')-v('yn'));window=(t>=START+8*UI)&(t<=START+255*UI)
    area=float(np.trapezoid(delta[window],t[window]));average=area/float(t[window][-1]-t[window][0]);direction=1 if offset>0 else-1
    phase_ok=abs(average)<=.01 if constant else direction*average>=.03
    checks={}
    for name,dev in devices.items():
        vc,vb,ve,_=map(v,dev['nodes']);ic=d['@q.'+name+'.qnpn13g2[ic]'];checks[name]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev['nx']))
    safe=all(x['minimum_active_vce_v']>=.4 and x['maximum_alltime_abs_vce_v']<=1.6 and x['maximum_alltime_abs_vbe_v']<=1 and x['maximum_alltime_abs_ic_per_emitter_a']<.003 for x in checks.values())
    tail_names=bound['tail_names']
    tails={n:float(d['@q.'+n+'.qnpn13g2[ic]'][active].min())for n in tail_names};safe=safe and min(tails.values())>=.0005
    mos_checks={}
    for name,dev in mos.items():
        vd,vg,vs,vb=map(v,dev['nodes']);ids=d['@n.'+name+'.nsg13_lv_nmos[ids]']
        peaks={label:float(abs(value).max())for label,value in [('vds',vd-vs),('vgs',vg-vs),('vgd',vg-vd),('vdb',vd-vb),('vsb',vs-vb)]}
        mos_checks[name]=dict(peaks_v=peaks,limit_v=1.32,minimum_active_vds_v=float((vd-vs)[active].min()),minimum_active_drain_current_a=float(ids[active].min()),maximum_alltime_abs_drain_current_a=float(abs(ids).max()),passed=max(peaks.values())<=1.32 and float((vd-vs)[active].min())>=0)
    mos_tails={name:mos_checks[name]['minimum_active_drain_current_a']for name in bound['mos_tail_names']}
    assert len(mos_checks)==200*bound['partition'] and len(mos_tails)==192*bound['partition']
    # Parallel devices are one physical stage tail. Sum their instantaneous
    # native currents before applying the unchanged 0.5mA stage-current gate.
    # Every individual MOS still passes the original terminal-voltage gates.
    stage_tail_currents={key:float(sum((d['@n.'+n+'.nsg13_lv_nmos[ids]']for n in names),np.zeros(len(t)))[active].min())for key,names in bound['mos_tail_groups'].items()}
    assert len(stage_tail_currents)==16
    safe=safe and all(x['passed']for x in mos_checks.values())and min(mos_tails.values())>=0 and min(stage_tail_currents.values())>=.0005
    r['mos_checks']=mos_checks;r['minimum_active_mos_tail_current_a']=mos_tails
    r['minimum_active_stage_tail_current_a']=stage_tail_currents
    r['stage_tail_current_gate_a']=.0005
    cap_checks={name:dict(maximum_alltime_abs_v=float(abs(v(dev['nodes'][0])-v(dev['nodes'][1])).max()),limit_v=1.6)for name,dev in caps.items()};safe=safe and all(x['maximum_alltime_abs_v']<=1.6 for x in cap_checks.values())
    data_ok=all(x['passed']for x in sampler_checks.values())and all(x['passed']for x in comparisons.values())and phase_ok
    r.update(expected_samples=expected,expected_comparisons=dict(x=xbits,y=ybits),sampler_checks=sampler_checks,comparisons=comparisons,phase_average_v=average,phase_passed=phase_ok,phase_gate=dict(minimum_signed_v=.03,constant_maximum_abs_v=.01,window_s=[START+8*UI,START+255*UI]),device_checks=checks,minimum_active_tail_current_a=tails,native_cap_voltage_checks=cap_checks,devices_passed=safe,data_passed=data_ok)
    # Direct native collector currents, with physical input-to-output
    # polarity. No Boolean reconstruction from ideal phase decisions.
    def ic(name):return d['@q.'+bound['vi_names'][name]+'.qnpn13g2[ic]']
    current=(ic('xxp')+ic('xyn'))-(ic('xxn')+ic('xyp'))
    output_delta=v('vip')-v('vin')
    def mean(values):return float(np.trapezoid(values[window],t[window])/(t[window][-1]-t[window][0]))
    mean_current=mean(current);mean_output=mean(output_delta)
    vi_phase_ok=(abs(mean_current)<=5e-6 and abs(mean_output)<=.002)if constant else(direction*mean_current>=50e-6 and direction*mean_output>=.005)
    vi_tails={tag:float(ic(tag)[active].min())for tag in ('xtx','xty')}
    vi_bias_ok=min(vi_tails.values())>=.0001
    vi_ok=vi_phase_ok and vi_bias_ok
    r['vi']=dict(mean_signed_current_a=mean_current,mean_output_difference_v=mean_output,minimum_active_tail_current_a=vi_tails,phase_passed=vi_phase_ok,bias_passed=vi_bias_ok,passed=vi_ok,phase_limits=dict(minimum_signed_current_a=50e-6,minimum_signed_voltage_v=.005,constant_maximum_abs_current_a=5e-6,constant_maximum_abs_voltage_v=.002),output_commonmode_v=[float(((v('vip')+v('vin'))/2)[active].min()),float(((v('vip')+v('vin'))/2)[active].max())],native_mim_geometry_um=[40,40],real_input_loading=True,actual_filter_connection=True,closed_loop=False)
    r['interface_observations']={name:dict(commonmode_v=[float(((v(p)+v(n))/2)[active].min()),float(((v(p)+v(n))/2)[active].max())],differential_v=[float((v(p)-v(n))[active].min()),float((v(p)-v(n))[active].max())])for name,p,n in [('data_a','xpd.adp','xpd.adn'),('data_c','xpd.cdp','xpd.cdn'),('select0','xpd.s0p','xpd.s0n'),('select1','xpd.s1p','xpd.s1n')]}
    assert all(sha(Path(f))==digest for f,digest in protected.items());r['sources_unchanged']=True;r['actual_fault_detected']=fault and not(data_ok and vi_ok)
    passed=r['actual_fault_detected']if fault else safe and data_ok and vi_ok
    r['status']='PASS_WHOLE_MIM_ACTUAL650_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF'if passed else'REJECTED_WHOLE_MIM_ACTUAL650_LOADED'
    assert passed,'Actual whole-wire retimed sampling, loaded phase/current or device gate failed'


def run_loaded(worker,models,variant,engine,model,contract,bound,case):
    devices=bound['groups']['npn13g2'];mos=bound['groups']['sg13_lv_nmos'];caps=bound['groups']['cap_cmim']
    groups=bound['groups'];ports=bound['ports']
    assert case in CASES
    corner='hot_low'if case.startswith('hot_')else'cold_high'if case.startswith('cold_')else'nominal'
    c=CORNERS[corner];scale=c['scale'];offset=(-.15 if case.endswith('_early')else.15)*UI
    bits=([0]*256 if case=='constant_zero'else[1]*256 if case=='constant_one'else prbs(0x7f))
    constant=case.startswith('constant_');fault=case in('clock_stopped','vi_bias_off')
    folder=worker.NATIVE/('loaded-n'+str(bound['partition'])+'-'+case);folder.mkdir()
    r=dict(status='RUNNING',case=case,partition=bound['partition'],corner=corner,accepted=False,
        full_phy_accepted=False,final_timing_complete=False,closed_loop=False,full_pex_qualified=False,
        scope='Actual650 nonlinear devices with current MIM-aware metal and physical gate-port reductions. External8GHz clock; full original256bits, loads and electrical gates. One selected partition/case; full serial PHY, gate extrinsicC, substrate, PVT/refinement and chip integration remain unqualified.',
        source_head=os.environ['GITHUB_SHA'],data_offset_s=offset,readback_controls=readback_controls())
    result=worker.DERIVED/('loaded-n'+str(bound['partition'])+'-'+case+'.json')
    def save():result.write_bytes(worker.enc(r))
    save()
    try:
        nodes={n for group in groups.values()for dev in group.values()for n in dev['nodes']}|set(ports)|set(bound['aliases'].values());nodes.discard('0')
        vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]+['@n.'+n+'.nsg13_lv_nmos[ids]'for n in mos]
        lib=variant/'models/models'
        deck=['NSSOC actual650 full nonlinear metal gate loaded circuit',
            f'.lib "{lib}/cornerHBT.lib" hbt_typ',f'.lib "{lib}/cornerRES.lib" {c["res"]}',
            f'.lib "{lib}/cornerCAP.lib" {c["cap"]}',f'.lib "{lib}/cornerMOSlv.lib" {c["mos"]}',
            f'.include "{model}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 sparse',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})']
        deck += [f'I_{bias} avdd {bias} PWL(0 0 500p '+('.001)'if bias.startswith('ib')else'.0005)')for bias in BIASES]
        deck += [f'I_{bias} avdd {bias} PWL(0 0 500p '+('0)'if case=='vi_bias_off'else'.00025)')for bias in('irvx','irvy')]
        deck += ['VDP dp0 0 '+shifted_data(bits,1.65*scale,.15*scale,offset),
            'VDN dn0 0 '+shifted_data([1-b for b in bits],1.65*scale,.15*scale,offset),
            'VCP cp0 0 '+clock(scale,True,case=='clock_stopped'),
            'VCN cn0 0 '+clock(scale,False,case=='clock_stopped'),
            'RDP dp0 dp 10','RDN dn0 dn 10','RCP cp0 cp 10','RCN cn0 cn 10',
            'XPD '+' '.join(ports)+' '+contract['model']]
        deck += [f'C_{net} {point} 0 150f'for net,point in bound['sampler_points'].items()]
        deck += [f'C_{node} {node} 0 50f'for node in('xp','xn','yp','yn')]
        deck += ['.control',f'pre_osdi {models/"models/r3_cmc.osdi"}',
            f'pre_osdi {models/"frontend/psp103.osdi"}',f'pre_osdi {models/"frontend/psp103_nqs.osdi"}',
            'set num_threads=1','set wr_singlescale','set wr_vecnames','set numdgt=16',*native_save_commands(vectors)]
        for name in devices:
            q='q.'+name+'.qnpn13g2'
            deck += [f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END']
        deck += ['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}',
            'wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        saves=native_save_commands(vectors)
        assert len(devices)==124 and len(mos)==200*bound['partition']and len(set(vectors))==len(vectors)
        assert [n for line in saves for n in line.split()[1:]]==vectors
        original_deck='\n'.join(deck)+'\n'
        (folder/'original-bench.cir').write_text(original_deck)
        (folder/'bench.cir').write_text(streaming_deck(original_deck,dict(vectors=vectors)))
        (folder/'spinit').write_text('set num_threads=1\n')
        protected={str(f):digest(f)for f in [Path(__file__),Path(worker.__file__),model,engine,
            folder/'bench.cir',folder/'original-bench.cir',folder/'spinit',*models.rglob('*'),*variant.rglob('*'),
            *[worker.ROOT/p for p in worker.read(worker.ROOT/worker.PINS)['files']]]if f.is_file()}
        r.update(binding=bound,vectors=vectors,source_bits=bits,source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest(),
            protected_inputs=protected,status='RUNNING_ACTUAL_WHOLE_WIRE_TRANSIENT',
            vector_census=dict(total=len(vectors),voltage_nodes=len(nodes),hbt_collector_currents=len(devices),mos_drain_currents=len(mos),save_commands=len(saves)))
        save()
        worker.execute([engine,'-n','-b','bench.cir'],folder.name,seconds=18000,cwd=folder)
        log=(worker.NATIVE/(folder.name+'.stdout')).read_text()+'\n'+(worker.NATIVE/(folder.name+'.stderr')).read_text()
        opts,notes,_=backend_readback(log,'sparse')
        notes += [line for line in log.splitlines()if 'too many arg'in line.lower()or 'no such vector'in line.lower()]
        r.update(returncode=0,native_options=opts,diagnostics=notes)
        if (folder/'op.dat').is_file():
            early_op=np.loadtxt(folder/'op.dat',skiprows=1)
            r['startup_op_observation']=dict(values=int(early_op.size),expected_values=len(vectors)+1,
                finite=bool(np.isfinite(early_op).all()),maximum_abs=float(abs(early_op).max())if np.isfinite(early_op).all()else None)
        save();assert not notes,notes
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
        assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in devices]and all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
        r['native_flags_verified']=len(flags)
        op=np.loadtxt(folder/'op.dat',skiprows=1)
        assert op.size==len(vectors)+1 and np.isfinite(op).all()and abs(op).max()<1e-9
        r['zero_source_op_maximum']=float(abs(op).max());save()
        t,d,capture=read_streamed_wave(folder/'wave.raw',vectors,STOP,STEP)
        r['raw_capture']=capture;save()
        measure_wave(bound,t,d,bits,offset,protected,r,constant,fault)
        return r
    except BaseException as error:
        if r['status'].startswith('RUNNING'):r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);r['traceback']=traceback.format_exc();raise
    finally:
        save()
