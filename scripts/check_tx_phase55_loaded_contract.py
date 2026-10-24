#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud source controls only. No DUT transient or physical qualification."""
import ast,collections,copy,hashlib,json,re
from pathlib import Path
import tx_phase55_loaded_contract as bench
ROOT=Path(__file__).resolve().parents[1]
RESET='hw/soc/analog/pcie/clock_div2_reset_feedback_candidate_v1.spice'
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def definitions(text):
    out={};current=None
    for row in bench.compact.statements(text):
        if row[0].lower()=='.subckt':
            assert current is None and row[1]not in out
            current=row[1];out[current]=dict(ports=row[2:],cards=[])
        elif row[0].lower()=='.ends':
            assert current==row[1];current=None
        else:
            assert current and row[0].startswith('X'),'Only physical X-model primitives or defined subcircuits are allowed'
            out[current]['cards'].append(row)
    assert current is None
    return out
def reset_validate(text):
    d=definitions(text)
    latch=definitions((ROOT/'hw/soc/analog/pcie/rx_sampler_hbt_v2.spice').read_text())['nssoc_cml_latch']
    tail=definitions((ROOT/'hw/soc/analog/pcie/clock_div4_hbt_v10.spice').read_text())['nssoc_clock_div2_tail_v10']
    front=definitions((ROOT/'hw/soc/analog/pcie/clock_div2_high_input_v1.spice').read_text())['nssoc_clock_div2_high_input_v1']
    expected={'nssoc_phase_reset_feedback_selector_v1','nssoc_phase_reset_sync2_v1','nssoc_phase_reset_level_v1','nssoc_clock_div2_tail_reset_candidate_v1'}
    assert set(d)==expected
    core=d['nssoc_clock_div2_tail_reset_candidate_v1'];cards={r[0]:r for r in core['cards']}
    assert core['ports']==['clkp','clkn','mp','mn','qp','qn','reqp','reqn','avdd','avss','sub']
    assert set(cards)=={'XBIAS','XREF','XM','XS','XSEEDP','XSEEDN','XRSYNC','XRLEVEL','XRMUX'}
    for row in tail['cards']:
        want=list(row)
        if row[0]=='XM':want[1:3]=['rp','rn']
        assert cards[row[0]]==want,'Original latch/tail geometry or clock polarity changed'
    assert cards['XRSYNC']==['XRSYNC','reqp','reqn','clkp','clkn','rs_p','rs_n','avdd','avss','sub','nssoc_phase_reset_sync2_v1']
    assert cards['XRLEVEL']==['XRLEVEL','rs_p','rs_n','runp','runn','avdd','avss','sub','nssoc_phase_reset_level_v1']
    assert cards['XRMUX']==['XRMUX','qn','qp','runp','runn','rp','rn','avdd','avss','sub','nssoc_phase_reset_feedback_selector_v1']
    # Exact original limiter/real MIM feed-forward, with only its public names changed.
    mapping={'clkp':'ip','clkn':'in','ckp':'cp','ckn':'cn'}
    level_expected=[[mapping.get(x,x)for x in r]for r in front['cards']if r[0]!='XSECOND']
    assert d['nssoc_phase_reset_level_v1']['cards']==level_expected
    sync=d['nssoc_phase_reset_sync2_v1'];s={r[0]:r for r in sync['cards']}
    assert sync['ports']==['reqp','reqn','clkp','clkn','qp','qn','avdd','avss','sub']
    assert set(s)=={'XBIAS','XREF','XM1','XS1','XM2','XS2'}
    for n in ('XBIAS','XREF'):assert s[n]==cards[n]
    for n,ports in [
      ('XM1','reqp reqn m1p m1n clkn clkp'),
      ('XS1','m1p m1n q1p q1n clkp clkn'),
      ('XM2','q1p q1n m2p m2n clkn clkp'),
      ('XS2','m2p m2n qp qn clkp clkn')]:
        assert s[n]==[n,*ports.split(),'avdd','avss','sub','ref','nssoc_cml_latch']
    selector=d['nssoc_phase_reset_feedback_selector_v1']
    assert selector['ports']==['fbp','fbn','runp','runn','outp','outn','avdd','avss','sub']
    a={r[0]:r for r in selector['cards']}
    # Existing latch current levels and two-stage stack; no added series enable.
    assert a['XT']==['XT','tail','ref','avss','sub','npn13G2','Nx=4']
    for n,term in [('XAP','outn fbp ea'),('XAN','outp fbn ea'),('XBP','outn seedp eb'),('XBN','outp seedn eb')]:
        assert a[n]==[n,*term.split(),'sub','npn13G2','Nx=2']
    for n,term in [('XSA','ea runp tail'),('XSB','eb runn tail')]:
        assert a[n]==[n,*term.split(),'sub','npn13G2','Nx=4']
    for n in ('XBIAS','XREF'):assert a[n]==cards[n]
    all_d={**d,'nssoc_cml_latch':latch}
    def count(name,stack=()):
        assert name not in stack
        result=collections.Counter()
        for row in all_d[name]['cards']:
            called=next((v for v in row[1:]if v in ('npn13G2','rppd','cap_cmim')or v in all_d),None)
            assert called,'Unknown or nonphysical device'
            if called in all_d:result.update(count(called,(*stack,name)))
            else:result[called]+=1
        return result
    census=count('nssoc_clock_div2_tail_reset_candidate_v1')
    assert census=={'npn13G2':56,'rppd':46,'cap_cmim':4},census
    return dict(schematic_primitives=dict(census),added_schematic_primitives=dict(npn13G2=41,rppd=37,cap_cmim=2),
      original_latch_cards_unchanged=True,original_core_except_master_data_unchanged=True,
      level_network_exact_original=True,no_internal_ideal_sources=True,
      no_new_layout_or_electrical_acceptance=True,full_tree_reset_implemented=False)
def main():
    methods=json.loads((ROOT/'scripts/tx-phase55-loaded-source-methods.json').read_text())
    for path,digest in methods['protected'].items():assert sha((ROOT/path).read_text())==digest,path
    # Import only these two original source functions; no native program or preparation.
    source=ast.parse((ROOT/'scripts/run_cloud_tx_mux4.py').read_text())
    wanted=[n for n in source.body if isinstance(n,ast.FunctionDef)and n.name in ('tree_plan','pwl')]
    assert len(wanted)==2
    original=dict(UI=bench.UI,START=bench.START,STOP=bench.STOP)
    exec(compile(ast.Module(body=wanted,type_ignores=[]),'<original clock contract>','exec'),original)
    plan=original['tree_plan'](32)
    assert len(plan['clocks'])==31
    assert collections.Counter(x['period']/bench.UI for x in plan['clocks'])=={1.:1,2.:2,4.:4,8.:8,16.:16}
    byname={x['name']:x for x in plan['clocks']}
    assert byname['sa']['origin']==bench.START-bench.UI and byname['sb']['origin']==bench.START
    for invert in (False,True):
        rendered=original['pwl']([i%2==0 for i in range(257)],2.,.1,bench.UI,bench.START,invert)
        numbers=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',rendered)))
        original_points=list(zip(numbers[::2],numbers[1::2],strict=True))
        generated=bench.clock_points(2.,.1,invert)
        assert len(original_points)==len(generated)
        assert all(abs(a-c)<1e-20 and abs(b-d)<1e-14 for (a,b),(c,d)in zip(original_points,generated,strict=True))
    result=bench.controls()
    boundary=dict(source_run=40084454916,summary_sha256='0'*64,measurement_pair='div1_first_div2',
      saved_vectors=['v(xloop.w_t398_c)','v(xloop.w_t389_c)'],common_mode_v=2.,single_ended_amplitude_v=.1,
      observed_window_s=[0.,1e-6],exact_observer_field_paths={'common_mode_v':'fixture.cm','single_ended_amplitude_v':'fixture.amplitude'},
      frequency_hz=4e9,use='isolated_fixed_frequency_test_not_PLL_replay')
    bench.validate_boundary(boundary)
    rejected=[]
    for name,key,value in [
      ('wrong_observer','source_run',0),('wrong_pair','measurement_pair','vco'),
      ('reversed_pair','saved_vectors',boundary['saved_vectors'][::-1]),
      ('frequency_relaxed','frequency_hz',2e9),('missing_provenance','exact_observer_field_paths',{}),
      ('overrail','common_mode_v',2.49),('nan_amplitude','single_ended_amplitude_v',float('nan')),
      ('bad_window','observed_window_s',[1e-6,0]),('infinite_window','observed_window_s',[0,float('inf')]),
      ('claims_PLL','use','PLL_connected')]:
        b=copy.deepcopy(boundary);b[key]=value
        try:bench.validate_boundary(b)
        except (AssertionError,ValueError,TypeError):rejected.append(name)
        else:raise AssertionError(name)
    # A syntactically complete boundary is explicitly not verified provenance.
    try:bench.prepare('not exact native model','not exact summary',boundary,'model.spice','models','r3.osdi')
    except AssertionError:rejected.append('unqualified_model_summary')
    else:raise AssertionError('Unqualified model accepted')
    reset=(ROOT/RESET).read_text();positive=reset_validate(reset);reset_faults=[]
    for name,old,new in [
      ('master_clock_polarity','XM rp rn mp mn clkn clkp','XM rp rn mp mn clkp clkn'),
      ('wrong_seed','w=2.2u l=2u','w=2u l=2u'),
      ('feedback_reversed','XRMUX qn qp','XRMUX qp qn'),
      ('request_hardwired','XRSYNC reqp reqn','XRSYNC avdd avss'),
      ('extra_tail_stack','XT tail ref avss','XT tail ref extra'),
      ('changed_real_MIM','XCP lp cp cap_cmim w=24u','XCP lp cp cap_cmim w=22u'),
      ('ideal_internal_source','XREF ref ref avss sub npn13G2 Nx=1','BREF ref avss V=0.8')]:
        assert old in reset
        try:reset_validate(reset.replace(old,new,1))
        except (AssertionError,ValueError,KeyError):reset_faults.append(name)
        else:raise AssertionError(name)
    print(json.dumps(dict(status='PASS_SOURCE_ONLY_PHASE_OBSERVER_AND_RESET_TOPOLOGY_CONTROLS',
      observer=result,exact_original_31_clock_plan=True,exact_original_root_PWL=True,
      boundary_negative_controls=rejected,reset_topology=positive,reset_negative_controls=reset_faults,
      actual_new_native_electrical_run=False,actual_reset_layout=False,PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
