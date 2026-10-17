#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native source-bound pump DC current balance; no acquisition or PHY approval."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
from cloud_vbic_tree32_backend import native_diagnostics
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-pump-current'
LIB=ROOT/'cloud-pll-snapshot'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
SUMMARY='436914ae3ef1e1727b31e799317cfd92354cf00a00839527f49fcb079b9da1a6'
PARTS='52b00bf1ee020974a7da752a52b19f460dfbf7d495892aab0f48e915a8a108ae'
VECTORS=['v(vctrl)','i(vclamp)','i(vdiv)','i(vco)','i(vup)','i(vdown)','i(vss)','i(vsub)','i(vcref)']
CORNERS={
 'nominal':dict(temperature=27,scale=1.,res='res_typ',cap='cap_typ',mos='mos_tt'),
 'hot_low':dict(temperature=125,scale=.95,res='res_wcs',cap='cap_wcs',mos='mos_ss'),
 'cold_high':dict(temperature=-40,scale=1.05,res='res_bcs',cap='cap_bcs',mos='mos_ff')}
def table_checks(a,reverse=False):
    assert a.shape==(61,10) and np.isfinite(a).all(),'Missing/invalid native DC rows'
    expected=np.linspace(.4,.7,61)
    if reverse:expected=expected[::-1]
    assert np.max(np.abs(a[:,0]-expected))<1e-10,'Changed native sweep'
    assert np.max(np.abs(a[:,1]-expected))<1e-8,'Clamp not at commanded voltage'
    residual=np.max(np.abs(a[:,2:].sum(axis=1)))
    assert residual<1e-8,'External source currents violate KCL'
    return dict(points=61,maximum_external_kcl_residual_a=float(residual))
def parser_controls():
    a=np.zeros((61,10));a[:,0]=a[:,1]=np.linspace(.4,.7,61);a[:,2]=-.001*a[:,1];a[:,7]=.001*a[:,1]
    table_checks(a);table_checks(a[::-1],True);rejected=[]
    cases={'missing_point':a[:-1].copy(),'nonfinite':a.copy(),'wrong_clamp':a.copy(),'wrong_current_sign':a.copy(),'wrong_sweep':a.copy()}
    cases['nonfinite'][0,2]=np.nan;cases['wrong_clamp'][0,1]+=.01
    cases['wrong_current_sign'][:,2]*=-1;cases['wrong_sweep'][0,0]+=.001
    for name,bad in cases.items():
        try:table_checks(bad)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Corrupt DC table accepted')
    return dict(known_resistor_source_sign_and_kcl=True,forward_and_reverse=True,rejected=rejected)
# Diagnostic-specific stricter tolerance. Original acquisition readers remain unchanged.
def option_values(text,backend):
    assert ('KLU' in text) if backend=='klu' else ('Sparse 1.3' in text)
    numeric={}
    for label,pattern in {'reltol':r'reltol(?:\s+\(current\))?','abstol':r'abstol(?:\s+\(current\))?','vntol':r'vntol(?:\s+\(voltage\))?','trtol':'trtol','maxord':r'(?:maxord|maxorder)','itl4':r'itl4(?:\s+\(transient iterations\))?'}.items():
        values=re.findall(r'(?mi)^\s*'+pattern+r'\s*=\s*(\S+)\s*$',text);assert len(values)==1,(label,values);numeric[label]=float(values[0])
    assert numeric['reltol']==1e-6 and numeric['abstol']==1e-12
    method=re.findall(r'(?mi)^\s*(?:method|integration method)\s*=\s*(\S+)\s*$',text);assert len(method)==1
    return dict(backend=backend,numeric=numeric,method=method[0],native_readback_sha256=hashlib.sha256(text.encode()).hexdigest())

def options(path,backend):
    return option_values(path.read_text(),backend)

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
    block='Sparse 1.3\nreltol (current) = 0.000001\nabstol (current) = 1e-12\nvntol (voltage) = 1e-6\ntrtol = 7\nmaxorder = 2\nitl4 (transient iterations) = 10\nIntegration method = trapezoidal\nTruncation error correction, charge based, is selected:\ndiaggmin (stepping) = 0\n'
    good='NSSOC_BACKEND_OPTIONS_BEGIN\n'+block+'NSSOC_BACKEND_OPTIONS_END\n'
    assert not backend_readback(good,'sparse')[1]
    assert not backend_readback(good.replace('Sparse 1.3','KLU'),'klu')[1]
    rejected=[]
    for name,bad in [('outside_label','diaggmin (stepping) = 0\n'+good),('inside_warning',good.replace('Sparse 1.3','Sparse 1.3\nWarning: genuine failure')),('changed_tolerance',good.replace('0.000001','0.01')),('duplicate',good+good),('missing_marker',good.replace('NSSOC_BACKEND_OPTIONS_END','')),('wrong_backend',good.replace('Sparse 1.3','KLU')),('missing_numeric',good.replace('trtol = 7\n',''))]:
        try:failed=bool(backend_readback(bad,'sparse')[1])
        except AssertionError:failed=True
        assert failed,name;rejected.append(name)
    return dict(positive=2,negative=rejected,only_verified_option_labels_exempted=True)


def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
      full_phy_accepted=False,qualified_pex=False,acquisition_accepted=False,
      scope='Exact native30device/84R155C C8 pump only. Static imposed public supplies/UP/DOWN/VCTRL. Measures source current including native bias resistors; excludes dynamic PFD edges, VCO loading, parent RC and closed-loop acquisition. No current inferred from logic duty.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=dict(parser=parser_controls(),native_readback=readback_controls())
        fetch(BASE+'cloud-results-39007535633-1-pll-c8-v2-native-acquisition-continuation/pll-c8-v2-native-acquisition-continuation-39007535633-1.summary.json',SUMMARY,OUT/'source-pin.json')
        pin=json.loads((OUT/'source-pin.json').read_text())
        assert pin['full_capture'] and pin['source_head']=='1b0abf2140259b6f75d192893dcfd980418ef245'
        wanted=['model-sources/'+p for p in pin['preparation']['model_sources']]
        wanted+=['case/circuit.cir','runtime/patched-ngspice']
        source,proof=reports.restore_report('pll-c8-v2-native-acquisition-continuation',39007535633,SUMMARY,PARTS,OUT/'source',wanted)
        r['models_source']=proof
        assert source==pin
        assert not LIB.exists();shutil.copytree(OUT/'source/model-sources',LIB)
        assert all(sha(LIB/p)==d for p,d in source['preparation']['model_sources'].items())
        engine=OUT/'source/runtime/patched-ngspice'
        assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        engine.chmod(0o755)
        spec=json.loads((ROOT/'docs/evidence/pll-filter-c8-compose-pass-20261017.json').read_text())
        prior,proof=reports.restore_report(spec['group'],spec['run'],spec['summary_sha256'],spec['parts_sha256'],OUT/'pump',('pump30-wire01.spice',))
        r['physical_source']=proof
        assert prior['status']=='PASS_ACTUAL_C8_PUMP_PHYSICAL_MODEL_AND_FAULTS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
        assert prior['source_unchanged'] and len(prior['composition_controls']['actual_rejected_mutants'])==6
        pump=OUT/'pump/pump30-wire01.spice'
        assert sha(pump)==spec['outputs'][pump.name]=='33fa7b1eb4fe3cd3017a3ce6ffc0a411d364e19100d696351970a021317c0df5'
        rows=[l.split()for l in pump.read_text().splitlines()if l and not l.startswith('*')]
        header=next(f for f in rows if f[0]=='.subckt')
        assert header==['.subckt','nssoc_pump30_wire_v1','sub','vctrl','div_avdd','vco_avdd','up','avss','down','wire_cref']
        assert sum(f[0].startswith('XD')for f in rows)==30
        assert sum(f[0].startswith('R')for f in rows)==84 and sum(f[0].startswith('C')for f in rows)==155
        original=(OUT/'source/case/circuit.cir').read_text()
        libs=[l for l in original.splitlines()if l.startswith('.lib ')]
        osdi=[l for l in original.splitlines()if l.startswith('pre_osdi ')]
        assert len(libs)==5 and len(osdi)==3
        assert all(str(LIB)in l for l in libs+osdi)
        protected={str(p):sha(p)for p in [Path(__file__),pump,engine,*LIB.rglob('*')]if p.is_file()}
        def run_case(corner,up,down,reverse=False,swap=False):
            c=CORNERS[corner];name=f'{corner}-u{up}d{down}-'+('reverse'if reverse else'forward')+('-swap'if swap else'')
            dest=OUT/name;dest.mkdir()
            library=[]
            for l in libs:
                path=l.split('"')[1]
                suffix='hbt_typ'if path.endswith('cornerHBT.lib')else c['res']if path.endswith('cornerRES.lib')else c['cap']if path.endswith('cornerCAP.lib')else c['mos']
                library.append(f'.lib "{path}" {suffix}')
            actual_up,actual_down=(down,up)if swap else(up,down)
            deck=['NSSOC actual C8 pump static source-current diagnostic',*library,
                f'.include "{pump}"',f'.temp {c["temperature"]}',
                '.options reltol=1e-6 abstol=1e-12 klu',
                f'VDIV div_avdd 0 {2.5*c["scale"]:.12g}',f'VCO vco_avdd 0 {2.3*c["scale"]:.12g}',
                f'VUP up 0 {2.5*c["scale"]*actual_up:.12g}',f'VDOWN down 0 {2.5*c["scale"]*actual_down:.12g}',
                'VSS avss 0 0','VSUB sub 0 0','VCREF wire_cref 0 0','VCLAMP vctrl 0 .4',
                'XPUMP sub vctrl div_avdd vco_avdd up avss down wire_cref nssoc_pump30_wire_v1',
                '.control',*osdi,'set wr_singlescale','set wr_vecnames','set numdgt=16',
                'dc VCLAMP .7 .4 -.005'if reverse else'dc VCLAMP .4 .7 .005',
                'wrdata dc.dat '+' '.join(VECTORS),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option',
                'echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
            (dest/'bench.cir').write_text('\n'.join(deck)+'\n');(dest/'spinit').write_text('set num_threads=1\n')
            env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
            env.update(SPICE_SCRIPTS=str(dest),OMP_NUM_THREADS='1')
            with(dest/'native.log').open('w')as f:
                done=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=dest,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
            assert done.returncode==0,(name,done.returncode)
            log=(dest/'native.log').read_text()
            options,diagnostics,_=backend_readback(log,'klu')
            assert options['numeric']['reltol']==1e-6 and options['numeric']['abstol']==1e-12
            assert not diagnostics,(name,diagnostics)
            text=(dest/'dc.dat').read_text();columns=text.splitlines()[0].lower().split()
            assert columns[1:]==VECTORS,(name,columns)
            a=np.loadtxt(dest/'dc.dat',skiprows=1);checks=table_checks(a,reverse)
            r.setdefault('cases',{})[name]=dict(corner=c,requested_up=up,requested_down=down,actual_up=actual_up,actual_down=actual_down,
                reverse=reverse,actual_input_swap=swap,native_options=options,diagnostics=diagnostics,checks=checks,
                columns=columns,rows=a.tolist(),inputs_sha256=sha(dest/'bench.cir'),raw_table_sha256=sha(dest/'dc.dat'))
            save();return a[::-1]if reverse else a
        r['current_balance']={}
        for corner in CORNERS:
            states={}
            for up,down in [(0,0),(1,0),(0,1),(1,1)]:
                a=run_case(corner,up,down);b=run_case(corner,up,down,True)
                error=float(np.max(np.abs(a[:,2:]-b[:,2:])))
                assert error<1e-9,('DC forward/reverse mismatch',corner,up,down,error)
                states[str(up)+str(down)]=a
            i00=states['00'][:,2];i10=states['10'][:,2];i01=states['01'][:,2];i11=states['11'][:,2]
            gainup=i10-i00;gaindown=i01-i00
            assert np.all(gainup>0)and np.all(gaindown<0),('Pump direction unexpected',corner)
            r['current_balance'][corner]=dict(vctrl_v=states['00'][:,1].tolist(),baseline_injection_a=i00.tolist(),
                up_increment_a=gainup.tolist(),down_increment_a=gaindown.tolist(),
                both_active_injection_a=i11.tolist(),interaction_a=(i11-i10-i01+i00).tolist(),
                baseline_finite_difference_siemens=(np.diff(i00)/np.diff(states['00'][:,1])).tolist(),
                sign_convention='Positive I(VCLAMP) is net pump injection into externally clamped VCTRL; negative is net sink. UP/DOWN increments subtract same-voltage00 bias state.')
            if corner=='nominal':
                mutant=run_case(corner,1,0,swap=True)
                assert np.max(np.abs(mutant[:,2]-i01))<1e-9
                assert np.all(mutant[:,2]-i00<0),'Real UP/DOWN swap did not reverse measured current'
                r['actual_native_fault']=dict(swapped_logic_inputs_rejected_by_current_direction=True,swapped_equals_independent_down_case_within_a=1e-9)
            save()
        assert all(sha(Path(p))==d for p,d in protected.items())
        r.update(status='COMPLETE_SOURCE_BOUND_PHYSICAL_PUMP_DC_CURRENT_AND_ACTUAL_SWAP_CONTROL_NOT_PLL_ACCEPTANCE',
                 protected_inputs_unchanged=True,protected_inputs=protected)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
