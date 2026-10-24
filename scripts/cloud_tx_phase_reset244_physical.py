#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh P/N244 circuits plus90 real body contacts: native physical gates only."""
import argparse,ast,hashlib,json,os,subprocess,sys,tarfile,traceback
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
from cloud_tx_exact_external_ports import compare as compare_ports
from cloud_tx_phase_divider_physical import clock_contract
import tx_phase_reset244_native_wires as wires
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset244-physical'
METHOD=ROOT/'scripts/tx-phase-reset244-native-methods.json'
GROUP='tx-phase-reset244-physical'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
SCHEMATIC_FAULTS=('wrong_feedback','wrong_seed','wrong_offset_length','wrong_hbt','missing_hbt')
PHYSICAL_FAULTS=('master_access_open','master_slave_short','missing_body_contact','offgrid')
def host():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def prerequisite():
    r=api('actions/runs/40118554214')
    assert r['head_sha']=='7c5d1177873428bb4f35ba097174e359e246582d'and r['run_attempt']==1
    assert r['path']=='.github/workflows/tx-phase-reset244-source-cloud.yml'and r['head_branch']=='codex/tx-clock-phase-parent'
    assert r['status']=='completed'and r['conclusion']=='success'
    j=api('actions/jobs/120944928730')
    assert j['run_id']==40118554214 and j['name']=='source-controls'and j['conclusion']=='success'
    b=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/Melihakbulut221/nssoc/actions/jobs/120944928730/logs'])
    assert len(b)==30021 and hashlib.sha256(b).hexdigest()=='ad152a27343bfbef642f85dd0788f97e4202b367bef2e611f81ae90d7eda58f3'
    return dict(run=40118554214,source=r['head_sha'],job=j['id'],exact_original_log_sha256=hashlib.sha256(b).hexdigest())
def schematic_fault(text,name):
    rows=text.splitlines()
    target={'wrong_feedback':'QPHASE__XM__XDATA__XAP','wrong_seed':'CPHASE__XSEEDP',
      'wrong_offset_length':'RPHASE__XRUN__XAND_SKEW','wrong_hbt':'QPHASE__XREF','missing_hbt':'QPHASE__XREF'}[name]
    found=[i for i,row in enumerate(rows)if row.startswith(target+' ')];assert len(found)==1
    i=found[0];words=rows[i].split()
    if name=='wrong_feedback':assert words[2]=='QN';words[2]='QP'
    elif name=='wrong_seed':assert words.count('w=2.2u')==1;words[words.index('w=2.2u')]='w=2.4u'
    elif name=='wrong_offset_length':assert words.count('l=20u')==1;words[words.index('l=20u')]='l=32u'
    elif name=='wrong_hbt':assert words.count('Nx=1')==1;words[words.index('Nx=1')]='Nx=2'
    if name=='missing_hbt':rows.pop(i)
    else:rows[i]=' '.join(words)
    result='\n'.join(rows)+'\n';assert result!=text
    return result
def controls():
    host();m=pins();pre=prerequisite()
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    import make_pcie_tx_phase_reset244_v1 as g
    source=[];faults=[]
    for pol in ('p','n'):
        g.configure(pol);text=g.m.physical_reference(ROOT);assert len(g.source_rows(ROOT,pol))==244
        for name in SCHEMATIC_FAULTS:
            changed=schematic_fault(text,name);assert changed!=text
            faults.append(dict(polarity=pol,name=name,exact_source_fault_created=True))
        top='nssoc_tx_phase_reset244_'+pol+'_v1'
        gs,gp=wires.graph_source(top,'a'*64);an,ap=wires.anchor_source(top,39)
        ast.parse(gs);ast.parse(an)
        source.append(dict(polarity=pol,graph=gp,anchors=ap,synthetic_components_not_native_prediction=True))
    # Inherited derivation rejects an ambiguous edit instead of changing an ownership gate.
    try:wires.derive('same same',[('same','other',1)])
    except AssertionError:pass
    else:raise AssertionError('Ambiguous native derivation accepted')
    pub=publication.controls();assert len(pub['rejected'])==17
    pins()
    return dict(status='PASS_NEW334_PHYSICAL_SOURCE_AND_EXACT_PLANNING_PREREQUISITE_NO_NATIVE_EXECUTION',
      prerequisite=pre,source_derivations=source,schematic_fault_controls=faults,publication_controls=pub,
      native_execution=False,physical_accepted=False,full_phy_accepted=False)
def main():
    host();m=pins();pre=prerequisite()
    tag,source=publication.context(GROUP,os.environ)
    release=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,source)
    OUT.mkdir(parents=True,exist_ok=False)
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],planning_prerequisite=pre,release_prerequisite=release,
      accepted=False,qualified_pex=False,electrical_accepted=False,physical_reset_qualified=False,
      all31_clock_tree_accepted=False,PLL_connected=False,full_phy_accepted=False,variants={})
    def save():(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        report['clock_contract']=clock_contract()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'fixture.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed);assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        pins();app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']==APP_SHA
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_ihp_drc import record_result
        from prepare_ihp_drc import validate_lock,verify
        import make_pcie_tx_phase_reset244_v1 as generator
        bound={ROOT/p:h for p,h in m['protected'].items()};bound[app]=APP_SHA
        for kind in ('drc','lvs'):
            path=ROOT/f'hw/soc/pnr/ihp-{kind}.lock.json';lock=json.loads(path.read_text());validate_lock(lock)
            assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6';bound[path]=sha(path)
            for row in lock['files']:
                p=ROOT/f'hw/soc/tools/ihp-{kind}-5e6d592'/row['path'];verify(p.read_bytes(),row);bound[p]=row['sha256']
        pcells=[ROOT/n for n in manifest['files']if n.endswith('/ihp/npn13G2_code.py')];assert len(pcells)==1
        assert sha(pcells[0])=='634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729'
        errors=[]
        for polarity in ('p','n'):
            out=OUT/polarity;out.mkdir();top='nssoc_tx_phase_reset244_'+polarity+'_v1'
            variant=dict(status='RUNNING',steps={},executions={});report['variants'][polarity]=variant;save()
            def execute(command,directory,label,allow_failure=False):
                log=directory/(label+'.log')
                with log.open('w')as f:code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
                e=dict(returncode=code,log_sha256=sha(log));variant['executions'][str(log.relative_to(out))]=e;save()
                if code:print(log.read_text(errors='replace')[-16000:],flush=True)
                if not allow_failure:assert code==0,(polarity,label,code)
                return e
            try:
                execute([app,'python',ROOT/'hw/soc/flow/make_pcie_tx_phase_reset244_v1.py','--pdk',ROOT/'pdk','--out',out/'layout','--preset',polarity],out,'generation')
                layout=out/'layout';generated=json.loads((layout/'result.json').read_text())
                gds=layout/(top+'.gds');reference=layout/'schematic.cir';original_hashes={gds:sha(gds),reference:sha(reference),layout/'result.json':sha(layout/'result.json')}
                generator.configure(polarity);expected=generator.source_rows(ROOT,polarity)
                assert generated['explicit_source_device_map']==expected and generated['preset_polarity']==polarity
                assert generated['candidate_source_sha256']==generator.CIRCUIT_SHA and generated['exactly243_other_compact_devices_unchanged']
                assert len(generated['instances'])==334 and generated['actual_expected_LVS_devices']==334 and set(generated['ports'])==wires.PORTS
                assert reference.read_text()==generator.m.physical_reference(ROOT)
                variant['generation']=generated;save()
                for name in ('drc','deep_lvs','flat_lvs',*PHYSICAL_FAULTS,*SCHEMATIC_FAULTS):
                    directory=out/name;directory.mkdir();physical=gds;schematic=reference;positive=name in ('drc','deep_lvs','flat_lvs')
                    if name in PHYSICAL_FAULTS:
                        physical=directory/'wrong.gds';script=directory/'mutate.py'
                        head='import pya\nl=pya.Layout();l.read('+repr(str(gds))+');c=l.cell('+repr(top)+')\n'
                        if name=='master_access_open':
                            b=generated['ports']['MP']['rect_um'];y=(b[1]+b[3])/2
                            body='i=l.layer(67,0);r=pya.Region(c.shapes(i));r-=pya.Region(pya.DBox(3,'+repr(y-1.1)+',4,'+repr(y+1.1)+').to_itype(l.dbu));c.shapes(i).clear();c.shapes(i).insert(r)\n'
                        elif name=='master_slave_short':
                            ys=[sum(generated['ports'][k]['rect_um'][i]for i in (1,3))/2 for k in ('MP','QP')]
                            body='c.shapes(l.layer(67,0)).insert(pya.DBox(.5,'+repr(min(ys)-.5)+',1.5,'+repr(max(ys)+.5)+'))\n'
                        elif name=='missing_body_contact':
                            tap=next(v for v in generated['instances']if v['name']=='TAP0')
                            xy=[a+b for a,b in zip(tap['placement_um'],generated['origin_translation_um'],strict=True)]
                            body='want=pya.DTrans('+repr(xy[0])+','+repr(xy[1])+')\nitems=[i for i in c.each_inst()if i.cell.name.split("$")[0]=="ptap1"and str(i.dtrans)==str(want)]\nassert len(items)==1\nc.erase(items[0])\n'
                        else:body='c.shapes(l.layer(8,0)).insert(pya.DBox(1.001,1.001,1.101,1.101))\n'
                        script.write_text(head+body+'l.write('+repr(str(physical))+')\n')
                        execute([app,'python',script],directory,'mutation');assert sha(physical)!=sha(gds)
                    if name in SCHEMATIC_FAULTS:
                        schematic=directory/'wrong.cir';schematic.write_text(schematic_fault(reference.read_text(),name));assert sha(schematic)!=sha(reference)
                    drc=name in ('drc','offgrid');kind='drc'if drc else'lvs'
                    deck=ROOT/f'hw/soc/tools/ihp-{kind}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/kind/('ihp-sg13g2.drc'if drc else'sg13g2.lvs')
                    options={'input':physical,'topcell':top,'log':directory/'deck.log','run_mode':'deep'if name=='deep_lvs'or drc else'flat'}
                    if drc:options.update(report=directory/'drc.lyrdb',threads=2,no_recommended='False',precheck_drc='False')
                    else:options.update(schematic=schematic,report=directory/'result.lvsdb',target_netlist=directory/'extracted.cir',thr=2,no_simplify='true',top_lvl_pins='true',combine_devices='false')
                    command=[app,'klayout','-b','-zz','-r',deck]
                    for k,v in options.items():command+=['-rd',str(k)+'='+str(v)]
                    entry=execute(command,directory,'run');step=dict(execution=entry,positive=positive);variant['steps'][name]=step;save()
                    if drc:
                        result=record_result(directory,top,0,bound);step['measurement']=result;save()
                        assert result['category_count']==560
                        if positive:assert result['status']=='PASS'and result['markers']==0
                        else:assert result['status']=='FAIL'and result['categories'].get('metal1_drw_Offgrid',0)>0
                    else:
                        audit=directory/'audit.json'
                        e=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',directory/'result.lvsdb','--top',top,'--deck-log',directory/'deck.log','--output',audit],directory,'audit',allow_failure=True)
                        result=json.loads(audit.read_text());step.update(audit=result,audit_execution=e);save();assert not result['extraction_diagnostics']
                        if positive:
                            assert e['returncode']==0 and result['status']=='PASS within comparison scope'
                            assert result['circuits'][0]['layout_devices_recursive']==result['circuits'][0]['schematic_devices_recursive']==334
                            step['ports']=compare_ports(reference.read_text(),(directory/'extracted.cir').read_text(),top,expected_count=11);assert step['ports']['passed']
                        else:assert e['returncode']==1 and result['status']=='FAIL'
                    step['expected_verdict_observed']=True;save()
                variant['wires']=wires.run(out,top,app,execute,pcells[0])
                assert all(sha(p)==h for p,h in original_hashes.items())
                variant.update(status='PASS_FRESH334_DRC_DEEP_FLAT_LVS9_FAULTS_AND1010_NATIVE_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_AND_LOADED_RESET',sources_unchanged=True)
            except BaseException as e:
                variant.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());errors.append(dict(polarity=polarity,error=repr(e)));save()
            finally:
                variant['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()};save()
        report['validation_errors']=errors
        assert all(sha(p)==h for p,h in bound.items())and all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items());pins()
        assert not errors,errors
        assert set(report['variants'])=={'p','n'}and all(v['sources_unchanged']for v in report['variants'].values())
        report.update(status='PASS_BOTH_FRESH334_PHYSICAL_AND1010_TERMINAL_GATES_REQUIRES_MIM_RC_AND_LOADED_RESET',sources_unchanged=True)
    except BaseException as e:report.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args()
    if a.controls:print(json.dumps(controls(),indent=2))
    else:main()
