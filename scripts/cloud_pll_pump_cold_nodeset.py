#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cold pump DC convergence study with independent seeds and all physical nodes.

Reference: https://ngspice.sourceforge.io/docs/ngspice-manual.pdf section11.2.1.
NODESET is a preliminary guess, not an initial-condition/transient waiver.
No full PLL capture or its original zero-source startup is changed.
"""
import json,os,subprocess,shutil
from pathlib import Path
import numpy as np
import cloud_pll_pump_current as base
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-pump-cold-nodeset'
LIB=ROOT/'cloud-pll-snapshot'
SOURCE_SHA='d5eed10a190213d552fa410db5eece05cd2c39f0b8c5e8266ecee050c3ba4025'
PARTS_SHA='791cd593eac42eae8b9bf629b9ec90355b167a557910dcb5be4a441d30e01961'
BASE_SHA='0ec3faf3820264560f195cab1e7371b16a066eac2ffa59682145b4a089c9688f'
def compare(a,b):
    assert a.shape==b.shape and np.isfinite(a).all()and np.isfinite(b).all()
    assert np.max(np.abs(a[:,0:2]-b[:,0:2]))<1e-10
    current=float(np.max(np.abs(a[:,2:10]-b[:,2:10])))
    voltage=float(np.max(np.abs(a[:,10:]-b[:,10:])))
    assert current<1e-9,('Independent DC current mismatch',current)
    assert voltage<1e-6,('Independent physical node mismatch',voltage)
    return dict(maximum_source_current_delta_a=current,maximum_physical_node_delta_v=voltage)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert sha(base.__file__)==BASE_SHA
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
       full_phy_accepted=False,qualified_pex=False,acquisition_accepted=False,
       scope='Diagnostic coldhigh static native30pump only. Baseline warnings remain recorded. Require both declared NODESET guesses, all four logic states, forward/reverse and all physical nodes to agree; no altered physical equations, waveform startup or acquisition gate.',
       reference='https://ngspice.sourceforge.io/docs/ngspice-manual.pdf#page=327',
       guesses_v=[.25,1.25],baseline_no_nodeset_retained=True)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=dict(parser=base.parser_controls(),readback=base.readback_controls())
        url=base.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json'
        fetch(url,SOURCE_SHA,OUT/'prior-pin.json');pin=json.loads((OUT/'prior-pin.json').read_text())
        assert pin['source_head']=='e29107296dc3abe0bcb15c57de0a7cbac67dc0e7'
        assert pin['status']=='FAIL_OR_ERROR'and 'dynamic gmin' in pin['error']
        selected=[n for n in pin['outputs']if n.startswith('source/model-sources/')]
        selected+=['source-pin.json','source/runtime/patched-ngspice','source/case/circuit.cir','pump/pump30-wire01.spice']
        prior,proof=reports.restore_report('pll-pump-current',39029337682,SOURCE_SHA,PARTS_SHA,OUT/'restored',selected)
        assert prior==pin;r['source']=proof
        restored=OUT/'restored'
        original=json.loads((restored/'source-pin.json').read_text())
        assert sha(restored/'source-pin.json')==base.SUMMARY
        assert not LIB.exists();shutil.copytree(restored/'source/model-sources',LIB)
        assert all(sha(LIB/p)==d for p,d in original['preparation']['model_sources'].items())
        engine=restored/'source/runtime/patched-ngspice';engine.chmod(0o755)
        assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        pump=restored/'pump/pump30-wire01.spice'
        assert sha(pump)=='33fa7b1eb4fe3cd3017a3ce6ffc0a411d364e19100d696351970a021317c0df5'
        rows=[l.split()for l in pump.read_text().splitlines()if l and not l.startswith('*')]
        header=next(f for f in rows if f[0]=='.subckt')
        assert header[2:]==['sub','vctrl','div_avdd','vco_avdd','up','avss','down','wire_cref']
        nodes=set();device_terminals=0
        for f in rows:
            if f[0].startswith('XD'):
                at=next((i for i,v in enumerate(f)if '='in v),len(f))-1
                nodes.update(n.lower()for n in f[1:at]);device_terminals+=len(f[1:at])
            elif f[0].startswith(('R','C')):nodes.update(n.lower()for n in f[1:3])
        public=set(header[2:]);assert public<=nodes
        observed=sorted('v('+n+')'if n in public else'v(xpump.'+n+')'for n in nodes)
        vectors=base.VECTORS+observed
        r['physical_observations']=dict(nodes=len(nodes),intrinsic_terminals=device_terminals,vectors=observed,
            includes_all_device_and_wire_nodes=True,scope='Native physical model nodes; no claim to observe every hidden compact-model internal variable.')
        body=(restored/'source/case/circuit.cir').read_text()
        libs=[l for l in body.splitlines()if l.startswith('.lib ')]
        osdi=[l for l in body.splitlines()if l.startswith('pre_osdi ')]
        assert len(libs)==5 and len(osdi)==3 and all(str(LIB)in l for l in libs+osdi)
        c=base.CORNERS['cold_high']
        libraries=[]
        for line in libs:
            p=line.split('"')[1]
            corner='hbt_typ'if p.endswith('cornerHBT.lib')else c['res']if p.endswith('cornerRES.lib')else c['cap']if p.endswith('cornerCAP.lib')else c['mos']
            libraries.append(f'.lib "{p}" {corner}')
        protected={str(p):sha(p)for p in [Path(__file__),Path(base.__file__),pump,engine,*LIB.rglob('*')]if p.is_file()}
        data={};r['cases']={};plain_decks={}
        for guess in (None,.25,1.25):
            for up,down in ((0,0),(1,0),(0,1),(1,1)):
                for reverse in (False,True):
                    label=('unseeded'if guess is None else'seed'+str(guess))+f'-u{up}d{down}-'+('reverse'if reverse else'forward')
                    dest=OUT/label;dest.mkdir()
                    lines=['NSSOC native cold pump independent DC guesses',*libraries,
                      f'.include "{pump}"','.temp -40','.options reltol=1e-6 abstol=1e-12 klu itl1=1000',
                      'VDIV div_avdd 0 2.625','VCO vco_avdd 0 2.415',
                      f'VUP up 0 {2.625*up:.12g}',f'VDOWN down 0 {2.625*down:.12g}',
                      'VSS avss 0 0','VSUB sub 0 0','VCREF wire_cref 0 0','VCLAMP vctrl 0 .4',
                      'XPUMP sub vctrl div_avdd vco_avdd up avss down wire_cref nssoc_pump30_wire_v1']
                    if guess is not None:lines.append(f'.nodeset all={guess}')
                    lines+=['.control',*osdi,'set wr_singlescale','set wr_vecnames','set numdgt=16',
                      'dc VCLAMP .7 .4 -.005'if reverse else'dc VCLAMP .4 .7 .005',
                      'wrdata dc.dat '+' '.join(vectors),
                      'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
                    plain='\n'.join(l for l in lines if not l.startswith('.nodeset '))
                    key=(up,down,reverse)
                    if key in plain_decks:assert plain==plain_decks[key]
                    else:plain_decks[key]=plain
                    assert not any(l.lower().startswith('.ic ')for l in lines)
                    (dest/'bench.cir').write_text('\n'.join(lines)+'\n');(dest/'spinit').write_text('set num_threads=1\n')
                    case=dict(nodeset_guess_v=guess,up=up,down=down,reverse=reverse,passed=False)
                    r['cases'][label]=case;save()
                    try:
                        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
                        env.update(SPICE_SCRIPTS=str(dest),OMP_NUM_THREADS='1')
                        with(dest/'native.log').open('w')as f:
                            proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=dest,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
                        case['returncode']=proc.returncode;assert proc.returncode==0
                        options,diagnostics,_=base.backend_readback((dest/'native.log').read_text(),'klu')
                        case.update(native_options=options,diagnostics=diagnostics)
                        columns=(dest/'dc.dat').read_text().splitlines()[0].lower().split()
                        assert columns[1:]==vectors
                        a=np.loadtxt(dest/'dc.dat',skiprows=1)
                        assert a.shape==(61,len(vectors)+1)and np.isfinite(a).all()
                        case['checks']=base.table_checks(a[:,:10],reverse)
                        data[(guess,up,down,reverse)]=a[::-1]if reverse else a
                        case.update(passed=not diagnostics,table_valid=True,raw_table_sha256=sha(dest/'dc.dat'))
                    except BaseException as error:case.update(error=repr(error),passed=False)
                    save()
        # Completeness and acceptance are explicit; a rejected native case never disappears.
        assert len(data)==24,'Incomplete actual native DC tables'
        comparisons=[]
        for up,down in ((0,0),(1,0),(0,1),(1,1)):
            ref=data[(None,up,down,False)]
            for guess in (None,.25,1.25):
                for rev in (False,True):
                    comparisons.append(dict(guess=guess,up=up,down=down,reverse=rev,**compare(ref,data[(guess,up,down,rev)])))
        r['independent_path_comparisons']=comparisons
        # Actual captured-table mutations exercise both current and internal-voltage guards.
        reference=data[(.25,0,0,False)];faults=[]
        for kind in ('current','physical_node'):
            bad=reference.copy();bad[0,2 if kind=='current'else 10]+=.001
            try:compare(reference,bad)
            except AssertionError:faults.append(kind)
            else:raise AssertionError('Altered actual measured table accepted')
        r['actual_table_faults_rejected']=faults
        assert all(sha(Path(p))==d for p,d in protected.items())
        seeded=[v for v in r['cases'].values()if v['nodeset_guess_v']is not None]
        clean=all(v['passed']for v in seeded)
        r.update(status='PASS_TWO_INDEPENDENT_NATIVE_NODESET_DC_PATHS_NOT_PLL_STARTUP_OR_PHY_ACCEPTANCE'if clean else'REJECTED_NATIVE_NODESET_DC_DIAGNOSTICS_RETAINED',
          clean_seeded_static_dc_passed=clean,original_unseeded_diagnostics_retained=True,
          final_equations_identical_across_guesses=True,protected_inputs_unchanged=True,protected_inputs=protected)
        assert clean,'At least one declared seeded path still has native diagnostics'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
