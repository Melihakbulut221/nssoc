#!/usr/bin/env python3
"""Consume completed native DRT and exact inputs; never rerun routing."""
import argparse,base64,hashlib,json,math,os,re,shutil,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_mainchip_postroute_geometry as geometry
def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
from check_final_native_antenna_counts import validate as antenna_counts
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-postroute-review'
CORNERS=('nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C')
TIMING_KEYS=('timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count',
 'design__max_cap_violation__count','design__max_slew_violation__count','design__max_fanout_violation__count')
def timing_gate(metrics,corner):
    values={k:float(metrics[k+'__corner:'+corner])for k in TIMING_KEYS}
    assert all(math.isfinite(v)for v in values.values()),'Non-finite native timing metric'
    assert all(values[k]>=0 and values[k].is_integer()for k in TIMING_KEYS[2:]),'Invalid violation count'
    return all(values[k]>=0 for k in TIMING_KEYS[:2])and all(values[k]==0 for k in TIMING_KEYS[2:])
def controls():
    metrics={k+'__corner:'+CORNERS[0]:0 for k in TIMING_KEYS}
    assert timing_gate(metrics,CORNERS[0])
    rejected=[]
    for key in TIMING_KEYS:
        bad=dict(metrics);bad[key+'__corner:'+CORNERS[0]]=-.001 if key in TIMING_KEYS[:2]else 1
        assert not timing_gate(bad,CORNERS[0]);rejected.append(key)
    for value in (float('inf'),float('nan')):
        bad=dict(metrics);bad[TIMING_KEYS[0]+'__corner:'+CORNERS[0]]=value
        try:timing_gate(bad,CORNERS[0])
        except AssertionError:pass
        else:raise AssertionError('Accepted non-finite slack')
    return dict(status='PASS_POSTROUTE_DECISION_CONTROLS_NOT_NATIVE_ANALYSIS',nonzero_or_negative_rejected=rejected)
def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def source_hash(path,ref):
    data=api('contents/'+path+'?ref='+ref)
    if data.get('encoding')!='base64':data=api('git/blobs/'+data['sha'])
    return hashlib.sha256(base64.b64decode(data['content'])).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preflight-inputs',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
      final_timing_complete=False,full_phy_accepted=False,qualified_pex=False,
      native_routing_started=False,scope='Completed native DRT topology, antenna/disconnect, fresh nominal RC and original-clock three-corner STA. Does not establish foundry RC-min/max, transistor LVS, full DRC or full serial PHY.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        methods=json.loads((ROOT/'scripts/mainchip-postroute-review-methods.json').read_text())
        assert all(sha(ROOT/p)==v for p,v in methods.items())
        r['decision_controls']=controls()
        descriptor=json.loads(os.environ['NSSOC_INPUT_PACKAGE'])
        assert set(descriptor)=={'run','attempt','group','source_head','controller_sha256','summary_sha256','parts_sha256'}
        assert descriptor['attempt']==1 and descriptor['group']=='mainchip-postroute-inputs'
        assert type(descriptor['run'])is int and descriptor['run']>0
        assert re.fullmatch('[0-9a-f]{40}',descriptor['source_head'])
        assert all(re.fullmatch('[0-9a-f]{64}',descriptor[k])for k in ('summary_sha256','parts_sha256','controller_sha256'))
        expected=methods['scripts/cloud_mainchip_postroute_inputs.py']
        assert descriptor['controller_sha256']==expected
        live=api('actions/runs/'+str(descriptor['run']))
        assert live['status']=='completed'and live['conclusion']=='success'and live['run_attempt']==1
        assert live['head_sha']==descriptor['source_head']and live['path']=='.github/workflows/mainchip-postroute-inputs-cloud.yml'
        assert source_hash('scripts/cloud_mainchip_postroute_inputs.py',descriptor['source_head'])==expected
        assert source_hash('scripts/prepare_mainchip_postroute_pdk.py',descriptor['source_head'])==methods['scripts/prepare_mainchip_postroute_pdk.py']
        # The proved package explicitly excludes completed route and stale SPEF/metrics.
        reports.OUT=OUT
        # Obtain the immutable summary through the existing report reader before
        # selecting only package members; no unrelated old native output is inherited.
        import cloud_replay_onehot_logic as logic
        logic.OUT=OUT
        summary,digest,parts=logic.summary(descriptor['group'],live)
        assert digest==descriptor['summary_sha256']and parts==descriptor['parts_sha256']
        assert summary['source_head']==descriptor['source_head']and summary['sources_unchanged']
        assert summary['status']=='PASS_EXACT_CURRENT_CANDIDATE_POSTROUTE_INPUT_PACKAGE_NOT_ROUTED_OR_TIMING_ACCEPTANCE'
        names=sorted(n for n in summary['outputs']if n.startswith('postroute-inputs/'))
        assert names and 'postroute-inputs/input-contract.json'in names
        actual,proof=reports.restore_report(descriptor['group'],descriptor['run'],digest,parts,OUT/'inputs',names)
        assert actual==summary
        package=OUT/'inputs/postroute-inputs';contract=json.loads((package/'input-contract.json').read_text())
        assert contract==summary['postroute_input_package']
        assert contract['original_root']==str(ROOT)and contract['clocks_ns']==[20,4,8,8]and contract['derating_percent']==5
        assert contract['completed_route_not_included']and contract['fresh_spef_required']and contract['inherited_metrics_discarded']
        assert contract['nominal_rc_only']and not contract['qualified_rc_minmax']and not contract['native_routing_started']
        assert contract['original_pdk_revision']=='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
        for name,row in contract['input_files'].items():
            rel=Path(name);assert not rel.is_absolute()and '..'not in rel.parts
            src=package/'files'/rel;dst=ROOT/rel
            assert sha(src)==row['sha256']and src.stat().st_size==row['bytes']
            if dst.exists():assert dst.is_file()and sha(dst)==row['sha256'],('Existing input differs',name)
            else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
            assert sha(dst)==row['sha256']
        for row in contract['tool_input_files'].values():
            p=package/row['exported'];assert sha(p)==row['sha256']and p.stat().st_size==row['bytes']
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        toolcheck="import hashlib,json,pathlib,sys; d=json.loads(sys.argv[1]); assert d; assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==v['sha256'] and pathlib.Path(p).stat().st_size==v['bytes'] for p,v in d.items())"
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        subprocess.run([str(app),'python','-c',toolcheck,json.dumps(contract['tool_input_files'])],cwd=ROOT,env=env,check=True)
        r.update(input_package_source=proof,input_package_descriptor=descriptor,input_contract=contract);save()
        config_root=OUT/'native-config'
        with(OUT/'native-config.log').open('w')as log:
            code=subprocess.call([str(app),'python',str(ROOT/'scripts/check_mainchip_postroute_config.py'),str(package),str(config_root)],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        if code:print((OUT/'native-config.log').read_text(errors='replace')[-12000:],flush=True)
        if(config_root/'result.json').is_file():r['native_configuration']=json.loads((config_root/'result.json').read_text());save()
        assert code==0,'Actual native postroute configuration differs'
        assert r['native_configuration']['status']=='PASS_ORIGINAL_NATIVE_POSTROUTE_CONFIG_NOT_ROUTED_ANALYSIS'
        assert r['native_configuration']['original_sha256']==contract['resolved_configuration_sha256']
        if args.preflight_inputs:
            assert not os.environ.get('NSSOC_COMPLETED_DRT','').strip(),'Do not misclassify a completed route as input-only preflight'
            assert all(sha(ROOT/n)==v['sha256']for n,v in contract['input_files'].items())
            r.update(status='PASS_NATIVE_POSTROUTE_INPUT_CONFIG_PREFLIGHT_NOT_ROUTED',
                sources_unchanged=True,native_routing_started=False,final_timing_complete=False,
                next_action='Require genuinely completed DRT descriptor before antenna/RC/STA; this only validates original input restoration and native flow configuration.')
            save();return
        assert os.environ.get('NSSOC_COMPLETED_DRT','').strip(),'Completed native route descriptor is mandatory'
        geometry.OUT=OUT/'geometry'
        geometry.main()
        g=json.loads((geometry.OUT/'result.json').read_text())
        assert g['status']=='PASS_COMPLETED_NATIVE_ROUTE_GEOMETRY_REQUIRES_DRC_ANTENNA_RC_STA'
        assert g['route_complete']and g['sources_unchanged']
        r['completed_geometry']=g;save()
        route=geometry.OUT/'routed/work/detailed-route.odb'
        assert sha(route)in g['protected_inputs'].values()
        counts=g['reported_native_drt_violation_counts'];assert counts and all(type(v)is int and v>=0 for v in counts)
        r['native_drt_reported_final_violations']=counts[-1]
        raw=package/'trial-config.json';state_path=package/'candidate-state.json'
        assert sha(raw)==contract['configuration_sha256']and sha(state_path)==contract['state_sha256']
        cfg=json.loads(raw.read_text());state=json.loads(state_path.read_text())
        assert not state['metrics']and all(state[k]is None for k in ('spef','def','pnl','sdf'))
        assert sha(state['odb'])==contract['candidate_odb_sha256']=='c005764c949e088b96cea5583f3a86fe901772b5e0eafc9d93bba506a151f2b7'
        assert sha(state['nl'])==contract['candidate_netlist_sha256']=='b6c0547b1f1995ecc62b3cebef88b4ceeb0ca63372da3d66a4f1d9608144eda0'
        assert sha(state['sdc'])==contract['candidate_sdc_sha256']=='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
        state['odb']=str(route)
        export_root=OUT/'native-def'
        with(OUT/'native-def.log').open('w')as log:
            subprocess.run([str(app),'openroad','-exit','-python',str(ROOT/'scripts/export_mainchip_completed_def.py')],
                cwd=ROOT,env=dict(env,NSSOC_EXPORT_ODB=str(route),NSSOC_EXPORT_SHA256=sha(route),NSSOC_EXPORT_OUT=str(export_root)),
                stdout=log,stderr=subprocess.STDOUT,check=True)
        exported=json.loads((export_root/'result.json').read_text())
        assert exported['status']=='PASS_NATIVE_ODB_DEF_EXPORT_ONLY'and exported['odb_sha256']==sha(route)
        deffile=export_root/'completed.def';assert sha(deffile)==exported['def_sha256']
        state['def']=str(deffile);r['native_def_export']=exported;save()
        trial=OUT/'trial-config.json';trial.write_bytes(raw.read_bytes())
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        protected={str(ROOT/n):v['sha256']for n,v in contract['input_files'].items()}
        protected.update({str(ROOT/n):v for n,v in methods.items()})
        protected.update({str(p):sha(p)for p in (route,deffile,trial,initial)})
        flow=ROOT/'hw/soc/pnr/mainchip_completed_postroute_flow.py'
        # Pinned LibreLane3.0.5 CLI validates --force-run-dir as an existing
        # directory before native flow execution. Require a fresh empty folder.
        run_dir=OUT/'run';run_dir.mkdir(exist_ok=False)
        assert run_dir.is_dir()and not any(run_dir.iterdir())
        cmd=[str(app),'python',str(flow),'--flow','MainchipCompletedPostroute',
          '--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell',
          '--force-run-dir',str(run_dir),'--with-initial-state',str(initial),str(trial)]
        r.update(status='RUNNING_NATIVE_COMPLETED_ROUTE_ANTENNA_RC_STA',command=cmd,protected_inputs=protected);save()
        with(OUT/'native.log').open('w')as log:
            code=subprocess.call(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=code;save()
        if code:print((OUT/'native.log').read_text(errors='replace')[-16000:],flush=True)
        assert code==0,'Native completed-route analysis failed; all evidence retained'
        def step(pattern):
            found=list((OUT/'run').glob(pattern));assert len(found)==1,(pattern,len(found));return found[0]
        ar=step('*-openroad-checkantennas');pr=step('*-odb-reportdisconnectedpins')
        rc=step('*-nssoc-onehotroutercx');sta=step('*-nssoc-onehotroutedsta')
        av=json.loads((ar/'state_out.json').read_text());pv=json.loads((pr/'state_out.json').read_text())
        r['antenna']=antenna_counts((ar/'reports/antenna.rpt').read_text(),av['metrics'])
        disconnect=pv['metrics']['design__critical_disconnected_pin__count']
        assert type(disconnect)is int and disconnect>=0
        r['critical_disconnected_pins']=disconnect
        r['native_spef_integrity']=json.loads((rc/'native-spef-integrity.json').read_text())
        r['native_sta_script_proof']=json.loads((sta/'native-sta-script-proof.json').read_text())
        measured=json.loads((sta/'state_out.json').read_text());measurements={}
        # Analysis must not silently mutate the routed ODB or netlist.
        assert sha(measured['odb'])==sha(route)and sha(measured['nl'])==contract['candidate_netlist_sha256']
        for corner in CORNERS:
            folder=sta/corner
            assert not(folder/'unpropagated.rpt').read_text().strip()
            assert 'NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED'in(folder/'sta.log').read_text()
            metrics={k:v for k,v in measured['metrics'].items()if k.endswith('__corner:'+corner)}
            passed=timing_gate(metrics,corner)
            for name in ('max.rpt','min.rpt','checks.rpt','violator_list.rpt','clock.rpt','ws.max.rpt','ws.min.rpt'):assert(folder/name).is_file()
            measurements[corner]=dict(metrics=metrics,timing_and_electrical_counts_met=passed,directory=str(folder.relative_to(OUT)))
        physical=counts[-1]==0 and r['antenna']['passed']and disconnect==0
        timing=all(v['timing_and_electrical_counts_met']for v in measurements.values())
        assert all(sha(p)==v for p,v in protected.items())
        r.update(status='PASS_NATIVE_POSTROUTE_NOMINAL_GATES_REQUIRES_SIGNOFF'if physical and timing else'COMPLETE_NATIVE_POSTROUTE_WITH_UNCLOSED_GATES',
          measurements=measurements,native_physical_gates_met=physical,
          all_reported_timing_and_electrical_gates_met=timing,sources_unchanged=True,
          next_action='Fix any measured violations on this exact route; nominal RC results do not close RC-min/max, full-chip LVS/DRC or full serial PHY.')
        save()
    except BaseException as error:
        r.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
