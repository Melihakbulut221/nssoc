#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Loaded whole PD394 native MIM-aware transient; not a recovered-clock loop.

Preserves all 9655 R, 7555 C and 394 native devices. Test loads are 150fF
at each sampler data-pair collector and 50fF at external comparator ports.
The collector reference is explicitly bound through native LVS/plane identities,
not an ideal alias of the distributed macro output net. External 8GHz clock.
"""
import argparse,copy,hashlib,json,os,re,shutil,subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path
import numpy as np
import cloud_cdr_pd_vi as legacy
import cloud_cdr_xor as primitive
import cloud_pll_pump_current as pump
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
UI=legacy.UI;START=legacy.START;STOP=legacy.STOP;STEP=legacy.STEP
MODEL='nssoc_cdr_pd394_avss256_mim_wire_v1'
CASES=['nominal_early','nominal_late','hot_early','hot_late','cold_early','cold_late','constant_zero','constant_one','clock_stopped','vi_bias_off']
BIASES=['ira','irb','irc','ird','irx','iry','ibda','ibdc','ibs0','ibs1']

def bind_native(text,contract,planes):
    rows=parser.statements(text);interface=contract['interface']
    assert rows[0]==['.subckt',MODEL,*interface]and rows[-1]==['.ends',MODEL]
    assert len(interface)==len(set(interface))==26
    assert set(interface)==set(['dp','dn','cp','cn','xp','xn','yp','yn','avdd','avss','sub','wire_cref','vip','vin','irvx','irvy',*BIASES])
    external={p:'0'if p in ('avss','sub','wire_cref')else p for p in interface}
    def node(n):return external[n]if n in external else 'xpd.'+n.lower()
    cards={r[0].lower():r for r in rows[1:-1]};assert len(cards)==len(rows)-2
    native={d['instance'].lower():d for d in contract['device_records']};assert len(native)==394
    assert {n for n in cards if n.startswith('x')}==set(native)
    assert Counter(r[0][0]for r in rows[1:-1])==dict(X=394,R=9655,C=7555)
    groups={kind:{}for kind in ('npn13g2','rppd','cap_cmim','ptap1')}
    logical={}
    for plane in planes['anchors']:
        pair=(plane['native_cluster'],plane['native_name'])
        assert logical.setdefault(plane['logical_net'],pair)==pair
    assert len(logical)==51
    witnesses={};native_nodes={}
    for name,d in native.items():
        terms=d['terminals'];f=cards[name];n=len(terms)
        assert f[1:n+1]==[t['node']for t in terms]and f[n+1]==d['model']
        params=dict(x.split('=')for x in f[n+2:]);assert len(params)==len(f[n+2:])and params==d['parameters']
        assert len({t['terminal']for t in terms})==n
        native_nodes[name]={t['terminal']:t['native_net']for t in terms}
        for t in terms:
            if t['native_net']in {v[1]for v in logical.values()}:
                assert (t['native_cluster'],t['native_net'])in logical.values()
        dev=dict(nodes=[node(t['node'])for t in terms],parameters=params,native_id=d['native_id'])
        if d['model']=='npn13g2':
            assert [t['terminal']for t in terms]==['C','B','E','S']
            assert set(params)=={'nx','we','le'}
            assert parser.number(params['we'])==Decimal('0.07e-6')and parser.number(params['le'])==Decimal('0.9e-6')
            nx=parser.number(params['nx']);assert nx==int(nx)and nx>0;dev['nx']=int(nx)
        groups[d['model']]['xpd.'+name]=dev
    assert {k:len(v)for k,v in groups.items()}==dict(npn13g2=122,rppd=102,cap_cmim=11,ptap1=159)
    hbts=groups['npn13g2'];aliases={};sampler_points={}
    def candidates(net,terminal='C'):
        cluster,native_net=logical[net]
        return [(name,d)for name,d in native.items()if d['model']=='npn13g2'and any(t['terminal']==terminal and t['native_cluster']==cluster and t['native_net']==native_net for t in d['terminals'])]
    # Choose the data-pair collector, not the cross-coupled hold-pair collector.
    # Both remain in the distributed network; no electrical aliases are inserted.
    for tag in 'abcd':
        for leg,other in [('p','n'),('n','p')]:
            net=tag+'q'+leg;opposite=logical[tag+'q'+other][1]
            choices=[(name,d)for name,d in candidates(net)if native_nodes[name]['B']!=opposite]
            assert len(candidates(net))==2 and len(choices)==1,(net,choices)
            name,d=choices[0];point=node(next(t['node']for t in d['terminals']if t['terminal']=='C'))
            aliases['xpd.'+net]=point;sampler_points[net]=point
            witnesses[net]=dict(device=name,terminal='C',native_cluster=logical[net][0],native_net=logical[net][1],probe=point,load_f=150e-15,selection='data-pair collector; hold-pair B is opposite output')
    for net in ('adp','adn','cdp','cdn','s0p','s0n','s1p','s1n'):
        choices=candidates(net);assert len(choices)==1
        name,d=choices[0];aliases['xpd.'+net]=node(next(t['node']for t in d['terminals']if t['terminal']=='C'))
    tails=[]
    for bias in ('ira','irb','irc','ird','ibda','ibdc','ibs0','ibs1'):
        found=['xpd.'+name for name,d in native.items()if d['model']=='npn13g2'and native_nodes[name]['B']==bias and native_nodes[name]['E']=='avss'and native_nodes[name]['C']!=bias]
        assert len(found)==(2 if bias in ('ira','irb','irc','ird')else 1);tails+=found
    assert len(tails)==12
    vi={}
    for role,base,collector in [('xxp','xp','vin'),('xxn','xn','vip'),('xyp','yp','vip'),('xyn','yn','vin')]:
        found=['xpd.'+name for name,d in native.items()if d['model']=='npn13g2'and native_nodes[name]['B']==base and native_nodes[name]['C']==collector]
        assert len(found)==1;vi[role]=found[0]
    for role,bias in [('xtx','irvx'),('xty','irvy')]:
        found=['xpd.'+name for name,d in native.items()if d['model']=='npn13g2'and native_nodes[name]['B']==bias and native_nodes[name]['E']=='avss'and native_nodes[name]['C']!=bias]
        assert len(found)==1;vi[role]=found[0]
    for a,b,tail in [('xxp','xxn','xtx'),('xyp','xyn','xty')]:
        assert native_nodes[vi[a][4:]]['E']==native_nodes[vi[b][4:]]['E']==native_nodes[vi[tail][4:]]['C']
    return dict(groups=groups,ports=[external[p]for p in interface],interface=external,aliases=aliases,sampler_points=sampler_points,probe_witnesses=witnesses,tail_names=tails,vi_names=vi)

def binding_controls(text,contract,planes):
    good=bind_native(text,contract,planes);rejected=[]
    # Equivalent physical unit spellings accepted; actual dimensions stay exact.
    equivalent=text.replace('we=0.070u','we=70n').replace('le=0.900u','le=900n')
    c=copy.deepcopy(contract)
    for d in c['device_records']:
        if d['model']=='npn13g2':d['parameters'].update(we='70n',le='900n')
    assert bind_native(equivalent,c,planes)['sampler_points']==good['sampler_points']
    for case in ('missing_contact','wrong_hbt_width','wrong_mim_width','swapped_collector_base','swapped_sample_plane','wrong_vi_polarity','wrong_public_port'):
        rows=parser.statements(text);p=copy.deepcopy(planes)
        if case=='swapped_sample_plane':
            a=next(a for a in p['anchors']if a['logical_net']=='aqp')
            other=next(a for a in p['anchors']if a['logical_net']=='aqn')
            assert (a['native_cluster'],a['native_name'])!=(other['native_cluster'],other['native_name'])
            a['native_cluster'],a['native_name']=other['native_cluster'],other['native_name']
        elif case=='wrong_public_port':rows[0][2],rows[0][3]=rows[0][3],rows[0][2]
        else:
            model='ptap1'if case=='missing_contact'else'cap_cmim'if case=='wrong_mim_width'else'npn13g2'
            i=next(i for i,r in enumerate(rows)if model in r)
            if case=='missing_contact':del rows[i]
            elif case in ('swapped_collector_base','wrong_vi_polarity'):
                if case=='wrong_vi_polarity':i=next(i for i,r in enumerate(rows)if r[0].lower()==good['vi_names']['xxp'][4:])
                rows[i][1],rows[i][2]=rows[i][2],rows[i][1]
            else:
                key='w='if case=='wrong_mim_width'else'we=';j=next(j for j,x in enumerate(rows[i])if x.startswith(key));rows[i][j]=key+'999u'
        altered='\n'.join(' '.join(r)for r in rows)+'\n'
        try:bind_native(altered,contract,p)
        except (AssertionError,ValueError,KeyError):rejected.append(case)
        else:raise AssertionError('Accepted '+case)
    assert len(rejected)==7
    return dict(equivalent_unit_spellings=2,rejected=rejected)

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-avss256-mim-loaded-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    corner='hot_low'if args.case.startswith('hot_')else'cold_high'if args.case.startswith('cold_')else'nominal'
    c=pump.CORNERS[corner];scale=c['scale'];offset=(-.15 if args.case.endswith('_early')else.15)*UI
    bits=([0]*256 if args.case=='constant_zero'else[1]*256 if args.case=='constant_one'else primitive.prbs(0x7f))
    constant=args.case.startswith('constant_');fault=args.case in ('clock_stopped','vi_bias_off')
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,full_phy_accepted=False,cdr_accepted=False,qualified_pex=False,closed_loop=False,
        scope='Actual PD394 complete native MIM-aware wire model:122HBT102rppd11MIM159contacts9655R7555C. External8GHz clock; original256bits and fixed phase/device gates. Added150fF at actual sampler data-pair collectors,50fF at external XOR outputs. No macro-port ideal alias, internal regenerated data or recovered clock. Native per-terminal voltages and actual VI collector currents. Requires full-loop/PVT/timestep/RF/body qualification.',data_offset_s=offset,corner=corner)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(Path(legacy.__file__))=='a319d6ba9b7a26964e29355e76b34685fff7ff35199ca5a8dbdd4a62031d9c33'
        assert sha(ROOT/'scripts/cloud_cdr_xor.py')=='3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'
        r['readback_controls']=readback_controls()
        pinpath=ROOT/'docs/evidence/cdr-avss256-mim-composition-pass-20261018.json';pin=json.loads(pinpath.read_text())
        prior,proof=reports.restore_report('cdr-avss256-mim-composition',pin['run'],pin['summary_sha256'],pin['parts_sha256'],out/'composed',['pd394-mim-wire.spice','composition.json'])
        assert prior==pin['report']and prior['sources_unchanged']and len(prior['controls'])==15
        model=out/'composed/pd394-mim-wire.spice';contract=json.loads((out/'composed/composition.json').read_text());assert contract==prior['composition']
        pp=ROOT/'docs/evidence/cdr-retimed-avss256-planes-pass-20261018.json';ppin=json.loads(pp.read_text());planes=ppin['report']['native_planes']
        assert planes['status']=='PASS_PD394_NATIVE158_PLANES_51_NETS_19_FAULTS'
        assert len(planes['anchors'])==158
        plane_report,plane_proof=reports.restore_report('cdr-retimed-avss256-planes',ppin['run'],ppin['summary_sha256'],ppin['parts_sha256'],out/'planes',['native-planes.json'])
        assert plane_report==ppin['report'] and plane_report['sources_unchanged']
        assert json.loads((out/'planes/native-planes.json').read_text())==planes
        bp=json.loads((ROOT/'docs/evidence/cdr-retimed-avss256-binding-pass-20261018.json').read_text())
        assert prior['model_source']['summary_sha256']==bp['summary_sha256']
        layout_hashes=[v for k,v in planes['inputs'].items()if k.endswith('/layout/result.json')]
        assert layout_hashes==[bp['report']['physical_source']['restore']['selected_files']['parent/layout/result.json']['sha256']]
        r['native_plane_source']=plane_proof

        r['composition_source']=proof;r['binding_controls']=binding_controls(model.read_text(),contract,planes)
        bound=bind_native(model.read_text(),contract,planes);devices=bound['groups']['npn13g2'];resistors=bound['groups']['rppd'];caps=bound['groups']['cap_cmim'];contacts=bound['groups']['ptap1'];ports=bound['ports'];biases=BIASES
        fetch(pump.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json',primitive.SUMMARY,out/'models-pin.json')
        mp=json.loads((out/'models-pin.json').read_text());wanted=[n for n in mp['outputs']if n.startswith('source/model-sources/')]+['source-pin.json','source/runtime/patched-ngspice']
        old,mproof=reports.restore_report('pll-pump-current',39029337682,primitive.SUMMARY,primitive.PARTS,out/'source',wanted);assert old==mp;r['models_source']=mproof
        original=json.loads((out/'source/source-pin.json').read_text());assert sha(out/'source/source-pin.json')==pump.SUMMARY
        lib=out/'models';shutil.copytree(out/'source/source/model-sources',lib)
        assert all(sha(lib/p)==d for p,d in original['preparation']['model_sources'].items())
        engine=out/'source/source/runtime/patched-ngspice';engine.chmod(0o755);assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        nodes={n for group in (devices,resistors,caps,contacts)for dev in group.values()for n in dev['nodes']}|set(ports)|set(bound['aliases'].values());nodes.discard('0')
        vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]
        models=lib/'models/models'
        deck=['NSSOC actual whole MIM-aware PD394',f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',f'.lib "{models}/cornerCAP.lib" {c["cap"]}',f'.include "{model}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 klu',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})']
        deck += [f'I_{bias} avdd {bias} PWL(0 0 500p '+('.001)'if bias.startswith('ib')else'.0005)')for bias in biases]
        deck += [f'I_{bias} avdd {bias} PWL(0 0 500p '+('0)'if args.case=='vi_bias_off'else'.00025)')for bias in ('irvx','irvy')]
        deck += ['VDP dp0 0 '+legacy.shifted_data(bits,1.65*scale,.15*scale,offset),'VDN dn0 0 '+legacy.shifted_data([1-b for b in bits],1.65*scale,.15*scale,offset),
            'VCP cp0 0 '+legacy.clock(scale,True,args.case=='clock_stopped'),'VCN cn0 0 '+legacy.clock(scale,False,args.case=='clock_stopped'),
            'RDP dp0 dp 10','RDN dn0 dn 10','RCP cp0 cp 10','RCN cn0 cn 10','XPD '+' '.join(ports)+' '+MODEL]
        deck += [f'C_{net} {point} 0 150f'for net,point in bound['sampler_points'].items()]
        deck += [f'C_{node} {node} 0 50f'for node in ('xp','xn','yp','yn')]
        deck += ['.control',f'pre_osdi {lib/"models/r3_cmc.osdi"}','set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
        for name in devices:
            q='q.'+name+'.qnpn13g2';deck += [f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END']
        deck += ['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}','wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
        protected={str(f):sha(f)for f in [Path(__file__),Path(legacy.__file__),model,pinpath,pp,ROOT/'scripts/cloud_cdr_xor.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
        r.update(binding=bound,devices=devices,native_caps=caps,vectors=vectors,source_bits=bits,source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest(),protected_inputs=protected,status='RUNNING_ACTUAL_WHOLE_WIRE_TRANSIENT');save()
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1')
        with(native/'native.log').open('w')as log:proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT)
        log=(native/'native.log').read_text();opts,notes,_=backend_readback(log,'klu');r.update(returncode=proc.returncode,native_options=opts,diagnostics=notes);save();assert proc.returncode==0 and not notes
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
        assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in devices]and all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
        r['native_flags_verified']=len(flags)
        op=np.loadtxt(native/'op.dat',skiprows=1);assert op.size==len(vectors)+1 and np.isfinite(op).all()and abs(op).max()<1e-9;r['zero_source_op_maximum']=float(abs(op).max())
        with(native/'wave.dat').open()as f:header=f.readline().lower().split()
        assert header==['time',*vectors]
        wave=np.loadtxt(native/'wave.dat',skiprows=1);t=wave[:,0];assert wave.shape[1]==len(vectors)+1 and np.isfinite(wave).all()and t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=STEP*1.00001
        d={n:wave[:,i+1]for i,n in enumerate(vectors)};active=t>=START
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
        r['status']='PASS_WHOLE_MIM_PD394_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF'if passed else'REJECTED_WHOLE_MIM_PD394_LOADED'
        assert passed,'Actual whole-wire retimed sampling, loaded phase/current or device gate failed'
    except BaseException as error:
        if r['status']in ('RUNNING','RUNNING_ACTUAL_WHOLE_WIRE_TRANSIENT'):r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save();print(r['status'],flush=True)
if __name__=='__main__':main()
