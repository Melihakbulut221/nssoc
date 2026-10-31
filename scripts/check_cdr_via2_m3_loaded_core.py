#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only full loaded-body fixtures; no actual model acquisition or engine execution."""
import ast,copy,ctypes,hashlib,io,json,os,shutil,socket,sys,traceback,types,unittest
from pathlib import Path
import numpy as np
import cdr_via2_m3_loaded_core as c

class Fixture:
    def __init__(self,out):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
        self.config,self.records=c.current_configuration();self.contract=copy.deepcopy(self.records['readback/actual/mim/composition/composition.json']);self.planes=copy.deepcopy(self.records['readback/actual/binding/inputs/native-planes.json'])
        self.projection=self.records['derived-loaded-vector-projection.json']
        self.context=dict(source=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),attempt=1)
        self.inputs=self.out/'synthetic-inputs';self.inputs.mkdir();self.paths={k:self.inputs/(k+'.json'if k!='model'else'synthetic-not-native.spice')for k in ('model','composition','planes')}
        cards=['* SYNTHETIC SOURCE FIXTURE; NOT THE NATIVE RC MODEL','.subckt nssoc_cdr_pd500_resistor_mim_wire_v59 '+' '.join(self.contract['interface'])]
        for d in self.contract['device_records']:
            cards.append(' '.join([d['instance'],*[t['node']for t in d['terminals']],d['model'],*[k+'='+v for k,v in d['parameters'].items()]]))
        cards += ['RTEST%05d avdd avss 1'%i for i in range(self.contract['counts']['R'])]
        cards += ['CTEST%05d avdd avss 1f'%i for i in range(self.contract['counts']['C'])]
        cards.append('.ends nssoc_cdr_pd500_resistor_mim_wire_v59')
        self.paths['model'].write_text('\n'.join(cards)+'\n');c.write_exclusive(self.paths['composition'],self.contract);c.write_exclusive(self.paths['planes'],self.planes)
        self.input_pins={k:c.file_pin(p)for k,p in self.paths.items()}
        self.runtime={k:self.inputs/k for k in ('lib','engine','source_pin','models_summary')};lib=self.runtime['lib'];lib.mkdir()
        for name in ('models/r3_cmc.osdi','models/psp103.osdi','models/psp103_nqs.osdi','models/models/cornerHBT.lib','models/models/cornerRES.lib','models/models/cornerCAP.lib','models/models/cornerMOSlv.lib'):
            p=lib/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('SYNTHETIC NONEXECUTABLE SOURCE FIXTURE\n')
        self.runtime['engine'].write_text('SYNTHETIC NEVER EXECUTED ENGINE PLACEHOLDER\n')
        c.write_exclusive(self.runtime['source_pin'],dict(scope='SYNTHETIC_FIXTURE_NOT_RUNTIME',preparation=dict(model_sources={str(p.relative_to(lib)):c.sha(p)for p in lib.rglob('*')if p.is_file()})))
        c.write_exclusive(self.runtime['models_summary'],dict(scope='SYNTHETIC_FIXTURE_NOT_RUNTIME'))
        self.runtime_pins={k:c.file_pin(p)for k,p in self.runtime.items()if k!='lib'}
        self.case=self.out/'case';self.raw_reads=0;self.capture_mode='zero';self.captured=None
        c.write_exclusive(self.out/'fixture-scope.json',dict(scope='SYNTHETIC_ISOLATED_SAME_CODE_CORE_API',current_native_model_acquired=False,actual_engine_executed=False,production_admission_exercised=False,actual_run_context=self.context))
    def current(self,paths,root=c.ROOT):
        assert {k:str(v)for k,v in paths.items()}=={k:str(v)for k,v in self.paths.items()}
        assert all(c.file_pin(paths[k])==pin for k,pin in self.input_pins.items())
        return copy.deepcopy(self.config),copy.deepcopy(self.records),copy.deepcopy(self.contract),copy.deepcopy(self.planes)
    def runtime_check(self,runtime,root=c.ROOT):
        assert {k:str(v)for k,v in runtime.items()}=={k:str(v)for k,v in self.runtime.items()}
        assert all(c.file_pin(runtime[k])==pin for k,pin in self.runtime_pins.items())
        return dict(scope='SYNTHETIC_RUNTIME_BYTE_IDENTITY_ONLY',paths={k:str(v)for k,v in runtime.items()},pins=self.runtime_pins)
    def fixture_writer(self,out,report):
        report.update(test_fixture_only=True,native_model_validation_is_synthetic=True,actual_engine_executed=False)
        return c.snapshot_writer(out,report)
    def clone(self,fn,**overrides):
        namespace=dict(fn.__globals__,verify_current_inputs=self.current,verify_runtime=self.runtime_check,snapshot_writer=self.fixture_writer,**overrides)
        clone=types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__);clone.__kwdefaults__=fn.__kwdefaults__
        assert clone.__code__ is fn.__code__ and fn.__globals__ is not namespace
        return clone
    def prepare(self):
        # The real production native-file verifier must reject these source fixtures.
        try:c.verify_current_inputs(self.paths)
        except ValueError:pass
        else:raise AssertionError('Synthetic cards passed production native model pin')
        result=self.clone(c.prepare_case)(self.case,self.paths,self.runtime,self.context)
        self.prepared_pin=result['plan']['prepared_state'];self.prepared=json.loads((self.case/'prepared-state.json').read_bytes())
        return result
    def setup_measurement(self,mode='zero'):
        self.capture_mode=mode;report=self.prepared['report'];native=self.case/'native'
        block='KLU\nreltol (current) = 0.0001\nabstol (current) = 1e-12\nvntol (voltage) = 1e-6\ntrtol = 7\nmaxorder = 2\nitl4 (transient iterations) = 10\nIntegration method = trapezoidal\n'
        log=''.join('NSSOC_NATIVE_FLAG_BEGIN q.'+n+'.qnpn13g2\n off 1\nNSSOC_NATIVE_FLAG_END\n'for n in report['devices'])
        (native/'native.log').write_text(log+'NSSOC_BACKEND_OPTIONS_BEGIN\n'+block+'NSSOC_BACKEND_OPTIONS_END\n')
        (native/'op.dat').write_text('SYNTHETIC ZERO OP\n'+' '.join(['0']*(len(report['vectors'])+1))+'\n')
    def reader(self,path,vectors,stop,step):
        self.raw_reads+=1;assert Path(path)==self.case/'native'/'wave.raw';assert vectors==self.projection['vectors']
        assert stop==2e-9+258*125e-12 and step==.3125e-12
        # The fake transport is explicit. The real frozen raw reader is separately
        # exercised below on a small complete binary fixture, never native data.
        t=np.linspace(0,stop,110001);zero=np.zeros(len(t));values={v:zero for v in vectors}
        report=self.prepared['report'];constants={}
        if self.capture_mode=='vi':
            constants['v(vip)']=.02
            for name,dev in report['devices'].items():constants['@q.'+name+'.qnpn13g2[ic]']=.0001*dev['nx']
            for name in report['mos_devices']:constants['@n.'+name+'.nsg13_lv_nmos[ids]']=.0002
            for role,current in dict(xxp=.0002,xxn=.0001,xyp=.00015,xyn=.0003,xtx=.0002,xty=.0003).items():constants['@q.'+report['binding']['vi_names'][role]+'.qnpn13g2[ic]']=current
        for name,value in constants.items():assert name in values;values[name]=np.full(len(t),value)
        self.captured=dict(t=t,values=values,constants=constants)
        return t,values,dict(scope='SYNTHETIC_NUMERICAL_FIXTURE_NOT_NATIVE_TRANSPORT',columns=len(vectors)+1,complete_unmodified_rows=False,actual_wave_acquired=False)
    def namespace(self,root=c.ROOT,numpy=None):
        ns=c.numerical_namespace(root,numpy)
        ns['stream']=types.SimpleNamespace(**{**vars(ns['stream']),'read_streamed_wave':self.reader})
        return ns
    def measure(self,returncode=0,prepared_pin=None):
        return self.clone(c.measure_case,numerical_namespace=self.namespace)(self.case,self.context,returncode,prepared_pin or self.prepared_pin)

class LoadedCoreControls(unittest.TestCase):
    base=None
    def setUp(self):
        self.work=self.base/self._testMethodName;self.work.mkdir()
    def fixture(self):return Fixture(self.work/'fixture')
    def copied_config_root(self):
        root=self.work/'source-copy';root.mkdir()
        names=[c.INPUTS,*[v['path']for v in c.current_configuration()[0]['records'].values()],c.current_configuration()[0]['transport_prerequisite']['path']]
        for name in names:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,target)
        return root
    def test_01_full_frozen_catalog(self):
        cat=c.catalog();self.assertEqual(len(cat['definitions']),29);self.assertEqual(len(cat['blocks']),6)
        self.assertEqual(cat['files'][c.WORKER]['sha256'],'add45d0ef874ec93fc9078d99bbb5cb0e684b667ec2f5699121eadb821ec5392')
        for record in cat['definitions'].values():c.extract(record)
        for record in cat['blocks'].values():c.extract(record,dedented=True)
    def test_02_disabled_entry_and_old_runtime(self):
        with self.assertRaises(SystemExit):c.main()
        for name in ('main','historical_runtime_reference','restore','native_export'):
            with self.assertRaises(ValueError):c.block(name,{})
    def test_03_independent_helper_namespaces(self):
        single={};c.definition(single,'scripts/cloud_cdr_pd_vi.py','UI')
        self.assertEqual(single['UI'],125e-12)
        self.assertTrue(all(name not in single for name in ('START','STOP','STEP')))
        for text in ('UI=1;UI=2','START=1','UI=1;import os','UI=START=1'):
            with self.assertRaises(ValueError):c.select_definition(ast.parse(text),'UI','Assign')
        a=c.numerical_namespace();b=c.numerical_namespace()
        self.assertIsNot(a['bind_native'].__globals__,b['bind_native'].__globals__)
        self.assertEqual(a['legacy'].UI,125e-12);self.assertEqual(b['pump'].CORNERS['nominal']['temperature'],27)
        a['pump'].CORNERS['nominal']['temperature']=999
        self.assertEqual(b['pump'].CORNERS['nominal']['temperature'],27)
        for forbidden in ('main','current_inputs','fetch','reports','subprocess'):self.assertNotIn(forbidden,a)
    def test_04_changed_frozen_source_rejected(self):
        root=self.work/'source';cat=c.catalog()
        for name in [c.CATALOG,*cat['files']]:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,p)
        path=root/c.WORKER;path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaises(ValueError):c.numerical_namespace(root)
    def test_05_current_complete_derived_contract(self):
        config,records=c.current_configuration();contract=records['readback/actual/mim/composition/composition.json']
        self.assertEqual(contract['counts'],dict(devices=500,R=24360,C=15568))
        self.assertEqual(sum(len(d['terminals'])for d in contract['device_records']),1446)
        self.assertLess(contract['interface'].index('yn'),contract['interface'].index('yp'))
        self.assertFalse(config['native_execution_authorized']);self.assertFalse(config['wave_execution_authorized'])
        self.assertEqual(records['derived-loaded-vector-projection.json']['counts']['total'],1151)
    def test_06_missing_transport_refused(self):
        root=self.copied_config_root();p=root/c.current_configuration()[0]['transport_prerequisite']['path'];p.unlink()
        with self.assertRaises(ValueError):c.current_configuration(root)
    def test_07_corrupt_transport_refused(self):
        root=self.copied_config_root();p=root/c.current_configuration()[0]['transport_prerequisite']['path'];p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):c.current_configuration(root)
    def test_08_changed_current_record_refused(self):
        root=self.copied_config_root();p=root/c.current_configuration()[0]['records']['readback/actual/binding/inputs/native-planes.json']['path'];p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):c.current_configuration(root)
    def test_09_context_shape_and_actual_identity(self):
        good=dict(source=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),attempt=1);self.assertEqual(c.actual_context(good),good)
        for changed in (dict(good,source='0'*40),dict(good,run_id=good['run_id']+1),dict(good,attempt=2),dict(good,extra=True)):
            with self.assertRaises(ValueError):c.actual_context(changed)
    def test_10_all_native_binding_and_13_original_refusals(self):
        f=self.fixture();ns=c.numerical_namespace();text=f.paths['model'].read_text()
        bound=ns['bind_native'](text,f.contract,f.planes);result=ns['binding_controls'](text,f.contract,f.planes)
        self.assertEqual(result['equivalent_unit_spellings'],2);self.assertEqual(len(set(result['rejected'])),13)
        self.assertEqual({k:len(v)for k,v in bound['groups'].items()},dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221))
        self.assertEqual(bound['aliases'],{k:v['loaded_node']for k,v in f.projection['aliases'].items()})
        self.assertEqual(len(bound['sampler_points']),8);self.assertEqual(len(bound['mos_tail_groups']),16)
        c.write_exclusive(self.work/'binding-control-result.json',dict(scope='SYNTHETIC_NATIVE_CARD_TEXT_NOT_ACTUAL_MODEL',controls=result,all500devices=True,all1446terminals=True))
    def test_11_synthetic_model_never_passes_production_pin(self):
        f=self.fixture()
        with self.assertRaises(ValueError):c.verify_current_inputs(f.paths)
        with self.assertRaises(ValueError):c.verify_runtime(f.runtime)
        self.assertFalse(f.case.exists())
    def test_12_full_same_code_preparation_and_deck(self):
        f=self.fixture();result=f.prepare();r=result['report'];deck=(f.case/'native'/'original-bench.cir').read_text();stream=(f.case/'native'/'bench.cir').read_text()
        self.assertEqual(result['status'],c.PREPARED_STATUS);self.assertFalse(r['transient_executed']);self.assertEqual(r['case'],'nominal_late')
        self.assertEqual(r['data_offset_s'],.15*125e-12);self.assertEqual(r['corner'],'nominal');self.assertEqual(len(r['source_bits']),256)
        self.assertEqual(r['vector_census']['total'],1151);self.assertEqual(r['vector_census']['voltage_nodes'],977)
        self.assertEqual(r['vectors'],f.projection['vectors'])
        expected=['0'if p in ('avss','sub','wire_cref')else p for p in f.contract['interface']]
        self.assertIn('XPD '+' '.join(expected)+' nssoc_cdr_pd500_resistor_mim_wire_v59\n',deck)
        self.assertEqual(sum(line.endswith(' 0 150f')for line in deck.splitlines()),8)
        self.assertEqual(sum(line.endswith(' 0 50f')for line in deck.splitlines()),4)
        self.assertEqual(len([line for line in deck.splitlines()if line.startswith('alter @q.')]),124)
        self.assertIn('.options reltol=1e-4 abstol=1e-12 klu\n',deck)
        self.assertIn('tran 3.125e-13 3.425e-08 0 3.125e-13\n',deck)
        self.assertIn('.tran 3.125e-13 3.425e-08 0 3.125e-13\n',stream);self.assertIn('run wave.raw\n',stream)
        self.assertEqual(result['plan']['argv'],[str(f.runtime['engine']),'-n','-b','bench.cir'])
        self.assertEqual(r['readback_controls']['positive'],2);self.assertEqual(len(r['readback_controls']['negative']),7)
        self.assertIn(str(c.ROOT/c.current_configuration()[0]['transport_prerequisite']['path']),r['protected_inputs'])
        self.assertTrue(all(c.sha(Path(p))==digest for p,digest in r['protected_inputs'].items()))
    def test_13_case_workspace_exclusive_and_case_scope(self):
        f=self.fixture();f.prepare()
        with self.assertRaises(FileExistsError):f.prepare()
        with self.assertRaises(ValueError):f.clone(c.prepare_case)(self.work/'other',f.paths,f.runtime,f.context,case='nominal_early')
    def test_14_real_backend_refusal_controls(self):
        ns=c.numerical_namespace();result=ns['readback_controls']()
        self.assertEqual(result['positive'],2);self.assertEqual(len(result['negative']),7)
    def test_15_full_zero_measurement_expected_rejection(self):
        f=self.fixture();f.prepare();f.setup_measurement()
        with self.assertRaises(AssertionError):f.measure()
        r=json.loads((f.case/'measurement-result.json').read_bytes())
        self.assertEqual(r['status'],'REJECTED_WHOLE_MIM_PD500_LOADED');self.assertEqual(f.raw_reads,1)
        self.assertEqual(len(r['device_checks']),124);self.assertEqual(len(r['mos_checks']),50);self.assertEqual(len(r['native_cap_voltage_checks']),7)
        self.assertEqual(r['native_flags_verified'],124);self.assertEqual(r['zero_source_op_maximum'],0)
        self.assertEqual(r['phase_average_v'],0);self.assertFalse(r['phase_passed']);self.assertFalse(r['data_passed']);self.assertFalse(r['devices_passed'])
        self.assertFalse(r['vi']['passed']);self.assertEqual(len(r['minimum_active_stage_tail_current_a']),16)
        self.assertTrue(r['sources_unchanged']);self.assertFalse(r['actual_fault_detected'])
        for name in ('accepted','cdr_accepted','full_phy_accepted','qualified_pex','closed_loop'):self.assertFalse(r[name])
        self.assertIn('SYNTHETIC',r['raw_capture']['scope'])
    def test_16_independent_native_current_and_stage_oracles(self):
        f=self.fixture();f.prepare();f.setup_measurement('vi')
        with self.assertRaises(AssertionError):f.measure()
        r=json.loads((f.case/'measurement-result.json').read_bytes());constants=f.captured['constants']
        self.assertEqual(r['status'],'REJECTED_WHOLE_MIM_PD500_LOADED');self.assertFalse(r['data_passed']);self.assertTrue(r['vi']['passed'])
        self.assertAlmostEqual(r['vi']['mean_signed_current_a'],.00025,places=14);self.assertAlmostEqual(r['vi']['mean_output_difference_v'],.02,places=14)
        for name,dev in r['devices'].items():
            expected=abs(constants['@q.'+name+'.qnpn13g2[ic]'])/dev['nx'];self.assertAlmostEqual(r['device_checks'][name]['maximum_alltime_abs_ic_per_emitter_a'],expected,places=14)
        for name,names in r['binding']['mos_tail_groups'].items():self.assertAlmostEqual(r['minimum_active_stage_tail_current_a'][name],len(names)*.0002,places=14)
        self.assertEqual(r['stage_tail_current_gate_a'],.0005);self.assertEqual(r['vi']['phase_limits']['minimum_signed_current_a'],50e-6)
        self.assertFalse(any('[ib]'in n or '[ie]'in n for n in r['vectors']))
    def test_17_failed_engine_preserved_before_wave(self):
        f=self.fixture();f.prepare();f.setup_measurement()
        with self.assertRaises(AssertionError):f.measure(returncode=7)
        r=json.loads((f.case/'measurement-result.json').read_bytes());self.assertEqual(r['returncode'],7);self.assertEqual(f.raw_reads,0);self.assertEqual(r['status'],'FAIL_OR_ERROR')
    def test_18_native_flag_failure_before_wave(self):
        f=self.fixture();f.prepare();f.setup_measurement();p=f.case/'native'/'native.log';p.write_text(p.read_text().replace(' off 1',' off 0',1))
        with self.assertRaises(AssertionError):f.measure()
        r=json.loads((f.case/'measurement-result.json').read_bytes());self.assertEqual(f.raw_reads,0);self.assertEqual(r['status'],'FAIL_OR_ERROR')
    def test_19_nonfinite_op_refused_before_wave(self):
        f=self.fixture();f.prepare();f.setup_measurement();p=f.case/'native'/'op.dat';p.write_text(p.read_text().replace('\n0 ','\nnan ',1))
        with self.assertRaises(AssertionError):f.measure()
        self.assertEqual(f.raw_reads,0)
    def test_20_prepared_pin_and_command_tampering(self):
        f=self.fixture();f.prepare();f.setup_measurement()
        with self.assertRaises(ValueError):f.measure(prepared_pin=dict(f.prepared_pin,sha256='0'*64))
        p=f.case/'transient-command.json';plan=json.loads(p.read_bytes());plan['argv']=['/bin/true'];p.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):f.measure()
        self.assertEqual(f.raw_reads,0)
    def test_21_protected_source_mutation_preserves_primary(self):
        f=self.fixture();f.prepare();f.setup_measurement();p=f.case/'native'/'bench.cir';p.write_text(p.read_text()+'* changed\n')
        with self.assertRaises(ValueError):f.measure()
        r=json.loads((f.case/'measurement-result.json').read_bytes());self.assertIn('unchanged pre-transient inputs',r['error']);self.assertEqual(f.raw_reads,0)
    def test_22_exclusive_reports_and_secondary_save_failure(self):
        path=self.work/'result.json';c.write_exclusive(path,dict(original=True));pin=c.file_pin(path)
        with self.assertRaises(FileExistsError):c.write_exclusive(path,dict(replaced=True))
        self.assertEqual(c.file_pin(path),pin)
        primary=RuntimeError('primary numerical failure');sink=io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(sink):c.finish_report(path,dict(status='REJECTED',error=repr(primary)),primary)
        self.assertIn('primary numerical failure',sink.getvalue());self.assertEqual(c.file_pin(path),pin)
        with redirect_stdout(sink):
            with self.assertRaises(FileExistsError):c.finish_report(path,dict(status='PASS'),None)
    def test_23_snapshot_sequence_never_overwrites(self):
        out=self.work/'outputs';out.mkdir();r=dict(status='first');save=c.snapshot_writer(out,r);save();p=out/'numerical-observations'/'000000.json';pin=c.file_pin(p)
        r['status']='second';save();self.assertEqual(c.file_pin(p),pin);self.assertEqual(json.loads((p.parent/'000001.json').read_bytes())['status'],'second')
    def test_24_frozen_raw_reader_complete_fixture_and_refusals(self):
        ns=c.numerical_namespace();vectors=['v(a)','@q.x.qnpn13g2[ic]'];stop=3e-12;step=1e-12
        header='Title: synthetic only\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 3\nNo. Points: 4\nVariables:\n0 time time\n1 v(a) voltage\n2 i(@q.x.qnpn13g2[ic]) current\nBinary:\n'
        data=np.array([[0,1,.1],[1e-12,2,.2],[2e-12,3,.3],[3e-12,4,.4]],dtype='<f8').tobytes();path=self.work/'synthetic.raw';path.write_bytes(header.encode()+data)
        t,values,report=ns['stream'].read_streamed_wave(path,vectors,stop,step)
        self.assertEqual(list(values['v(a)']),[1,2,3,4]);self.assertEqual(list(values[vectors[1]]),[.1,.2,.3,.4]);self.assertTrue(report['complete_unmodified_rows'])
        for i,changed in enumerate((header.encode()+data[:-1],header.encode()+data+b'x',header.replace('v(a) voltage','v(b) voltage').encode()+data,header.replace('Flags: real','Flags: complex').encode()+data)):
            p=self.work/('refuse%d.raw'%i);p.write_bytes(changed)
            with self.assertRaises(AssertionError):ns['stream'].read_streamed_wave(p,vectors,stop,step)
    def test_25_fixed_measurement_thresholds_and_current_scope(self):
        ns=c.numerical_namespace();source,tree=c.extract(c.catalog()['blocks']['measurement'],dedented=True)
        for literal in ("x['minimum_active_vce_v']>=.4","x['maximum_alltime_abs_vce_v']<=1.6","x['maximum_alltime_abs_ic_per_emitter_a']<.003","min(stage_tail_currents.values())>=.0005","direction*mean_current>=50e-6","direction*mean_output>=.005"):
            self.assertIn(literal,source)
        self.assertEqual(ns['STOP'],ns['START']+258*ns['UI']);self.assertEqual(ns['STEP'],.3125e-12)
    def test_27_active_external_effect_barrier(self):
        def fork(pty=False):
            result=os.forkpty()if pty else os.fork();pid=result[0]if pty else result
            if pid==0:os._exit(97)
            if pty:os.close(result[1])
            os.waitpid(pid,0);raise AssertionError('Process audit barrier allowed fork')
        for action in (lambda:os.system('true'),lambda:socket.socket(),lambda:ctypes.CDLL(None),lambda:fork(),lambda:fork(True)):
            with self.assertRaisesRegex(RuntimeError,'SOURCE_FIXTURE_EXTERNAL_EFFECT_REFUSED'):action()
    def test_26_production_namespaces_unchanged_after_clones(self):
        self.assertIs(c.prepare_case.__globals__['verify_current_inputs'],c.verify_current_inputs)
        self.assertIs(c.measure_case.__globals__['numerical_namespace'],c.numerical_namespace)
        self.assertEqual(c.current_configuration()[0]['allowed_cases'],['nominal_late'])

def controls(out):
    out=Path(out).absolute();out.mkdir(parents=True,exist_ok=False)
    LoadedCoreControls.base=out/'fixtures';LoadedCoreControls.base.mkdir()
    # Numeric package initialization precedes the source fixture barrier. No
    # project native archive or engine is loaded; only installed NumPy is used.
    active=[True];denied=[]
    def audit(event,args):
        if active[0]and(event.startswith('socket.')or event in ('subprocess.Popen','os.system','os.posix_spawn','os.posix_spawnp','os.exec','os.fork','os.forkpty','ctypes.dlopen')):
            denied.append(event);raise RuntimeError('SOURCE_FIXTURE_EXTERNAL_EFFECT_REFUSED '+event)
    sys.addaudithook(audit)
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(LoadedCoreControls)
    try:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    finally:active[0]=False
    record=dict(schema='nssoc-current-loaded-core-source-controls-v1',scope='SYNTHETIC_SOURCE_ONLY_NO_NATIVE_ACQUISITION_OR_ENGINE',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),successful=result.wasSuccessful()and result.testsRun==27 and not result.skipped,stdout=stream.getvalue(),denied_external_effects=denied,python=sys.version,numpy=np.__version__,source=os.environ.get('GITHUB_SHA'),run=os.environ.get('GITHUB_RUN_ID'),native_model_card_validation_executed=False,actual_engine_executed=False,loaded_simulation_executed=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)
    c.write_exclusive(out/'result.json',record);print(json.dumps(record,sort_keys=True),flush=True)
    if not record['successful']:raise AssertionError('Loaded numerical source controls require exactly27 tests and zero failures/errors/skips')
    return record

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();controls(a.out)
