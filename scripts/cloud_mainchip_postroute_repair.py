#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only native repair of the exact measured routed chip; no timing waiver."""
import hashlib,json,math,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-mainchip-postroute-repair'
CORNERS=['nom_typ_1p20V_25C','nom_slow_1p08V_125C','nom_fast_1p32V_m40C']
SUMMARY='39ddb8633e57072ce21d12fbe2c30c8a78a8d0f9b5c544724edc2ecdfc77635a'
PARTS='e10f42775e7ead514d4ca2701f6fa6e5266090329913a7d61522e12e05f1c237'
def quote(s):
    assert not any(c in str(s)for c in '\n\r\0{}')
    return '{'+str(s)+'}'
def worst(text):
    values=[float(x)for x in re.findall(r'(?m)^\s*([-+0-9.eE]+)\s+slack\s+\((?:VIOLATED|MET)\)',text)]
    assert values and all(math.isfinite(v)for v in values),'Incomplete native timing report'
    return min(values)
def baseline_gate(measured,expected):
    assert set(measured)==set(expected)==set(CORNERS)
    for c in CORNERS:
        for mode in ('max','min'):
            assert math.isfinite(measured[c][mode])
            assert abs(measured[c][mode]-expected[c][mode])<=.001,('Native baseline differs by >1ps',c,mode,measured[c][mode],expected[c][mode])
def controls():
    expected={c:dict(max=-10.,min=-.5)for c in CORNERS};baseline_gate(expected,expected)
    rejected=[]
    for label,value in [('optimistic',0.),('nonfinite',float('nan')),('wrong-corner',-12.)]:
        bad={c:dict(v)for c,v in expected.items()};bad[CORNERS[0]]['max']=value
        try:baseline_gate(bad,expected)
        except AssertionError:rejected.append(label)
    try:worst('empty')
    except AssertionError:rejected.append('empty-report')
    assert len(rejected)==4
    return rejected
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        full_phy_accepted=False,final_timing_complete=False,detailed_route_complete=False,
        optimizer_parasitics='placement-Steiner candidate estimates; not routed signoff',
        qualified_pex=False,scope='Source-bound native electrical repair, setup buffering/sizing and positive hold-buffer candidate. '
        'Original routed nominal SPEF, 20/4/8/8ns propagated clocks, 5 percent derate, twenty SRAMs. '
        'Baseline must reproduce all six original worst slacks within 1ps before mutation. '
        'After the exact baseline and router guards, use placement-Steiner estimates only for candidate optimization. '
        'Optimizer estimates are not final timing; new route/RC/all-corner STA required.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label,extra=None,required=True):
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        env.update(NSSOC_RESIZER_OUT=str(OUT),NSSOC_CORNERS=' '.join(CORNERS),NSSOC_ROUTER_INIT_TCL=str(ROOT/'hw/soc/flow/onehot_native_router_init.tcl'))
        if extra:env.update(extra)
        start=time.monotonic()
        with(OUT/(label+'.log')).open('w')as f:
            code=subprocess.call(list(map(str,cmd)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code,elapsed_s=time.monotonic()-start));save()
        if code:print((OUT/(label+'.log')).read_text(errors='replace')[-10000:],flush=True)
        if required:assert code==0,(label,code)
        return code
    save()
    try:
        from check_mainchip_postroute_repair_sources import check
        check()
        r['baseline_gate_controls']=controls()
        pin=json.loads((ROOT/'docs/evidence/mainchip-completed-postroute-unclosed-gates-20261021.json').read_text())
        assert pin['run']==39654204345 and pin['summary_sha256']==SUMMARY and pin['parts_sha256']==PARTS
        live=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/39654204345']))
        assert live['status']=='completed'and live['conclusion']=='success'and live['run_attempt']==1
        assert live['head_sha']=='59297d93106c4401d94213ee94d048d7c839d7a3'
        assert live['path']=='.github/workflows/mainchip-postroute-review-cloud.yml'
        names=['inputs/postroute-inputs/trial-config.json','native-config/resolved.json',
            'run/4-nssoc-onehotroutedsta/state_out.json','geometry/routed/work/detailed-route.odb',
            'inputs/postroute-inputs/files/hw/soc/out/cloud-onehot-native-fanout/candidate.v',
            'inputs/postroute-inputs/files/hw/soc/out/cloud-onehot-native-fanout/source/run/1-openroad-detailedrouting/soc_top.sdc',
            'run/3-nssoc-onehotroutercx/native-spef-integrity.json',
            'run/3-nssoc-onehotroutercx/nom/soc_top.nom.spef']
        original,proof=reports.restore_report('mainchip-postroute-review',pin['run'],SUMMARY,PARTS,OUT/'source',names)
        assert original['source_head']==live['head_sha']and original['returncode']==0
        assert original['status']=='COMPLETE_NATIVE_POSTROUTE_WITH_UNCLOSED_GATES'and original['sources_unchanged']
        assert original['native_drt_reported_final_violations']==original['critical_disconnected_pins']==0
        assert original['antenna']['final_violating_nets']==563 and original['antenna']['final_violating_pins']==626
        assert original['measurements']==pin['measurements']
        assert original['completed_geometry']['route_complete']and original['completed_geometry']['sources_unchanged']
        assert original['native_spef_integrity']==pin['native_spef_integrity']
        integrity=original['native_spef_integrity']['spefs']['nom_*']['audit']
        assert integrity['nets']==143338 and integrity['inconsistent_nets']==0
        measurements={c:{'timing__'+k+'__ws':original['measurements'][c]['metrics']['timing__'+k+'__ws__corner:'+c]
            for k in ('setup','hold')}for c in CORNERS}
        source=OUT/'source';db=source/names[3];nl=source/names[4];sdc=source/names[5];spef=source/names[7]
        assert sha(db)=='6a7bbf7bb871fa6037d26d0f60c2979ae5a3bb13caf8c84459a518c5fb0ca633'
        assert sha(nl)=='b6c0547b1f1995ecc62b3cebef88b4ceeb0ca63372da3d66a4f1d9608144eda0'
        assert sha(sdc)=='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
        assert sha(spef)=='a945642b3df7b61eb1c57250d7794d0134ba6c57bb0987721731be2414a13c9d'
        assert sha(source/names[1])=='0fc8159beefd0a013aea99b34a92322248ae3f3ead58db7648ff0d1f39948293'
        cfg=json.loads((source/names[1]).read_text())
        assert cfg['PNR_CORNERS']==CORNERS and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['CLOCK_PERIOD']==20 and cfg['CLOCK_UNCERTAINTY_CONSTRAINT']==.25
        assert cfg['RT_MIN_LAYER']=='Metal2'and cfg['RT_MAX_LAYER']=='TopMetal2'
        # Fetch immutable native PDK blobs and verify Git object identity and length.
        lockpath=ROOT/'scripts/onehot-native-resizer-pdk-lock.json';lock=json.loads(lockpath.read_text())
        assert lock['commit']=='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'and len(lock['files'])==19
        pdk=OUT/'pdk';model_hashes={}
        for row in lock['files']:
            path=Path(row['path']);assert not path.is_absolute()and '..'not in path.parts
            url='https://raw.githubusercontent.com/'+lock['repository']+'/'+lock['commit']+'/'+row['path']
            with urllib.request.urlopen(url,timeout=120)as response:raw=response.read()
            assert len(raw)==row['bytes']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob']
            target=pdk/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            model_hashes[str(target)]=sha(target)
        def model(path):
            target=pdk/'ihp-sg13g2'/str(path).rsplit('/ihp-sg13g2/',1)[1]
            assert str(target)in model_hashes
            return target
        tcl=['set_thread_count 1','define_corners '+' '.join(CORNERS)]
        for c in CORNERS:
            libs=list(cfg['LIB'][c])
            libs += [p for m in cfg['MACROS'].values()for p in m['lib'][c]]
            assert len(libs)==6
            tcl += ['read_liberty -corner '+c+' '+quote(model(p))for p in libs]
        tcl += ['read_db '+quote(db),'read_sdc '+quote(sdc),
            'set_timing_derate -early 0.95','set_timing_derate -late 1.05',
            'set_propagated_clock [all_clocks]']
        # Native layer settings are only used to estimate changed nets during
        # optimization. Exact extracted source SPEF is loaded after these settings.
        for c in CORNERS:
            for layer,rc in cfg['LAYERS_RC']['*'].items():
                tcl.append('set_layer_rc -corner '+c+' -layer '+layer+' -resistance '+str(rc['res'])+' -capacitance '+str(rc['cap']))
            for via,rc in cfg['VIAS_R']['*'].items():
                tcl.append('set_layer_rc -corner '+c+' -via '+via+' -resistance '+str(rc['res']))
            for kind in ('signal','clock'):
                tcl.append('set_wire_rc -'+kind+' -corner '+c+' -layers {Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}')
            tcl.append('read_spef -corner '+c+' '+quote(spef))
        exclude=model(cfg['PNR_EXCLUDED_CELL_FILE']).read_text()
        for line in exclude.splitlines():
            pattern=line.split('#',1)[0].strip()
            if pattern:tcl.append('set_dont_use [get_lib_cells '+quote(pattern)+']')
        native=ROOT/'hw/soc/flow/mainchip_postroute_repair.tcl'
        tcl.append('source '+quote(native))
        script=OUT/'native.tcl';script.write_text('\n'.join(tcl)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        protected={str(p):sha(p)for p in [Path(__file__),native,ROOT/'hw/soc/flow/onehot_native_router_init.tcl',script,lockpath,ROOT/'scripts/check_mainchip_postroute_repair_geometry.py',*[source/n for n in names]]}
        protected.update(model_hashes)
        r.update(source=proof,verified_postroute_run=pin['run'],previous_antenna=original['antenna'],
            original_measurements=measurements,model_hashes=model_hashes,protected_inputs=protected,
            source_odb_sha256=sha(db),source_spef_sha256=sha(spef),source_sdc_sha256=sha(sdc))
        save()
        run([app,'openroad','-version'],'native-version')
        r['native_version']=(OUT/'native-version.log').read_text().strip()
        print(r['native_version'],flush=True);save()
        run([app,'openroad','-exit',script],'native-baseline',{'NSSOC_RESIZER_STAGE':'baseline'})
        actual={c:{m:worst((OUT/('before-'+c+'-'+m+'.rpt')).read_text())for m in ('max','min')}for c in CORNERS}
        expected={c:{m:measurements[c]['timing__'+key+'__ws']for m,key in [('max','setup'),('min','hold')]}for c in CORNERS}
        r.update(native_baseline=actual,expected_baseline=expected);save();baseline_gate(actual,expected)
        r['status']='RUNNING_NATIVE_SETUP_HOLD_REPAIR_AFTER_MATCHED_BASELINE';save()
        run([app,'openroad','-exit',script],'native-repair',{'NSSOC_RESIZER_STAGE':'repair'})
        a=(OUT/'router-init-before.def').read_text();b=(OUT/'router-init-after.def').read_text()
        normalize=lambda s:re.sub(r'(?m)^GCELLGRID[^\n]*\n','',s)
        assert normalize(a)==normalize(b)
        assert normalize(a)!=normalize('X'+b[1:])
        reports_match={}
        for corner in CORNERS:
            for mode in ('max','min'):
                p=OUT/('router-init-before-'+corner+'-'+mode+'.rpt')
                q=OUT/('router-init-after-'+corner+'-'+mode+'.rpt')
                assert p.read_bytes()==q.read_bytes()
                reports_match[corner+'/'+mode]=sha(p)
        r['routing_initialization']=dict(physical_def_preserved_excluding_gcellgrid=True,
            six_native_reports_literal_identity=reports_match,changed_def_rejected=True,
            source_guides_sha256=sha(OUT/'router-init-source.guide'))
        run([app,'openroad','-exit','-python',ROOT/'scripts/check_mainchip_postroute_repair_geometry.py'],'native-geometry')
        r['geometry']=json.loads((OUT/'geometry.json').read_text())
        env=dict(NSSOC_TOPOLOGY_BEFORE=str(db),NSSOC_TOPOLOGY_AFTER=str(OUT/'candidate.odb'),
            NSSOC_CLOCK_ROUTE_PROOF_OUT=str(OUT/'fixed-clock.json'))
        run([app,'openroad','-exit','-python',ROOT/'scripts/check_onehot_fixed_clock_route.py'],'native-fixed-clock',env)
        r['fixed_clock']=json.loads((OUT/'fixed-clock.json').read_text())
        run([sys.executable,ROOT/'hw/soc/flow/prepare_ihp_native_boot.py'],'native-logic-models')
        models=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'
        lib=models/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        assert sha(lib)=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
        checker=ROOT/'hw/soc/flow/check_eco_logic_clones.py'
        run([app,'python',ROOT/'sw/tests/eco_logic_native.py','--checker',checker,'--liberty',lib,'--output',OUT/'controls'],'logic-controls')
        r['logic_controls']=json.loads((OUT/'controls/result.json').read_text())
        assert r['logic_controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
        cmd=[app,'python',checker,nl,OUT/'candidate.v','--liberty',lib,'--output',OUT/'proof','--macro-verilog-define','FUNCTIONAL']
        for name in ('RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_2P_256x16_c2_bm_bist.v'):
            cmd+=['--macro-verilog',models/'libs.ref/sg13g2_sram/verilog'/name]
        run(cmd,'native-equation-proof');r['proof']=json.loads((OUT/'proof/result.json').read_text())
        assert r['proof']['status']=='PASS within scope'and r['proof']['unobserved_output_port_changes']==0
        # Corrupt a real candidate positive buffer and rerun the native proof.
        text=(OUT/'candidate.v').read_text()
        match=re.search(r'\bsg13g2_buf_\d+\s+(\S+)\s*\((.*?)\);',text,re.S);assert match
        bad=text[:match.start()]+'sg13g2_inv_1 '+match[1]+' ('+re.sub(r'\.X\s*\(','.Y(',match[2])+');'+text[match.end():]
        (OUT/'inverted.v').write_text(bad)
        neg=list(cmd);neg[neg.index(OUT/'candidate.v')]=OUT/'inverted.v';neg[neg.index(OUT/'proof')]=OUT/'negative-proof'
        code=run(neg,'actual-buffer-inversion-control',required=False)
        assert code!=0;r['actual_inversion_control_rejected']=True
        assert all(sha(Path(p))==v for p,v in protected.items())
        r.update(status='PASS_NATIVE_RESIZER_CANDIDATE_REQUIRES_ROUTE_FRESH_RC_ALL_CORNER_STA',
            sources_unchanged=True,candidate_odb_sha256=sha(OUT/'candidate.odb'),
            candidate_netlist_sha256=sha(OUT/'candidate.v'))
    except BaseException as e:r.update(status='FAIL_NATIVE_RESIZER_STAGE_NO_ACCEPTANCE',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
