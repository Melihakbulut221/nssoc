#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native compile/zero-source OP preflight for whole845+4-contact RC.

The full1us transient remains in the prepared circuit but is not executed by
this preflight. Zero-source OP does not prove biased operation or PLL lock.
"""
import json,os,re,shutil,time
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_companion_replay as engines
import run_cloud_pll865_snapshot as pll
import read_pll845_full_native_op as full_op
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-op'
SOURCE=ROOT/'cloud-pll-snapshot'
RUN=39920519407
SUMMARY='63c6b8d34ecf277dce223427c72bdb943ed0dc010c80f496d8feb33f268f94dd'
PARTS='92a85edae348ad4e3ebfb62b372f627dde16ef9aadb4fcb55cedc1422a9d4657'
HEAD='efe9885e87bce9eb82a1c6decc4ed85ab2d65160'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(Path(__file__)),
      accepted=False,full_phy_accepted=False,loaded_simulation_passed=False,
      closed_loop_accepted=False,qualified_pex=False,zero_source_op_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        base=f'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{RUN}-1-pll-rhi120-c8-preparation/'
        fetch(base+f'pll-rhi120-c8-preparation-{RUN}-1.summary.json',SUMMARY,OUT/'preparation-summary.json')
        prepared=json.loads((OUT/'preparation-summary.json').read_text())
        assert prepared['status']=='PASS_WHOLE_PLL_LOADED_DECK_AND2737_TERMINAL_INSTRUMENTATION_REQUIRES_NATIVE_EXECUTION'
        assert prepared['source_head']==HEAD and prepared['sources_unchanged']
        assert prepared['all_original_stimuli_loads_solver_duration_unchanged']and prepared['terminal_probes']==2737
        files=['candidate-circuit.cir','terminal-instrumentation.json','composition/pll845-mim-wire.spice','composition/composition.json']
        files+=['model-sources/'+n for n in prepared['source_inputs']]
        prior,proof=reports.restore_report('pll-rhi120-c8-preparation',RUN,SUMMARY,PARTS,OUT/'prepared',files)
        assert prior==prepared;r['preparation_source']=proof;save()
        assert not SOURCE.exists();SOURCE.mkdir()
        for n,digest in prepared['source_inputs'].items():
            p=OUT/'prepared/model-sources'/n;assert sha(p)==digest
            dest=SOURCE/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        case=OUT/'case';case.mkdir()
        shutil.copy2(OUT/'prepared/candidate-circuit.cir',case/'circuit.cir')
        shutil.copy2(OUT/'prepared/composition/pll845-mim-wire.spice',case/'parent865.spice')
        coverage=json.loads((OUT/'prepared/terminal-instrumentation.json').read_text())
        contract=json.loads((OUT/'prepared/composition/composition.json').read_text())
        assert not contract['uncontacted_body_groups']and len(contract['device_records'])==845
        assert contract['counts']==dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
        assert len(coverage['native_terminal_probes'])==2737 and coverage['full_native_terminal_coverage']
        assert len(coverage['auxiliary_contact_probes'])==4 and len(coverage['native_hbt_off_targets'])==102
        deck=(case/'circuit.cir').read_text()
        assert deck.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1
        assert [l[5:].split()for l in deck.splitlines()if l.startswith('save ')]==[coverage['vectors']]
        # This wrapper invokes only OP. No shortened transient is substituted.
        wrapper='NSSOC whole845 physical RC zero-source OP preflight\n.include "circuit.cir"\n.control\nop\nwrite op.raw all\necho NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\nquit\n.endc\n.end\n'
        (case/'op-only.cir').write_text(wrapper);(case/'spinit').write_text('set num_threads=1\n')
        engines.OUT=OUT;paths,proof=engines.restore_engines()
        assert sha(paths['patched'])=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        r['runtime_provenance']=proof;r['controls']=dict(op_reader=pll.pfd_op_controls(),backend=readback_controls())
        protected={str(p):sha(p)for p in [*case.iterdir(),*SOURCE.rglob('*')]if p.is_file()}
        r['protected_inputs']=protected;save()
        log=pll.native_run(paths['patched'],case,'op-only.cir',time.monotonic()+1200,r,save)
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
        wanted={l.split()[1].split('[off]')[0].removeprefix('@')for l in coverage['native_hbt_off_targets']}
        assert len(flags)==len(wanted)==102 and {n for n,b in flags}==wanted
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1']for _,body in flags)
        r['native_hbt_off_readback']=dict(devices=102,all_readback_one=True)
        options,diagnostics,block=backend_readback(log,'klu')
        r['native_options']=options;r['native_diagnostics']=diagnostics;save()
        assert not diagnostics
        raw_op=(case/'op.raw').read_bytes()
        r['operating_point']=pll.zero_source_operating_point(raw_op,coverage['vectors'])
        r['all_native_operating_point']=full_op.read(raw_op,coverage['vectors'])
        r['all_native_op_controls']=full_op.controls(raw_op,coverage['vectors'])
        assert len(r['all_native_op_controls'])==12 and all(c['rejected']for c in r['all_native_op_controls'])
        assert all(sha(Path(p))==h for p,h in protected.items())
        assert all(sha(OUT/'prepared'/n)==prepared['outputs'][n]for n in files)
        assert sha(Path(__file__))==r['controller_sha256']
        r.update(status='PASS_WHOLE_PLL_NATIVE_COMPILE_AND_ZERO_SOURCE_OP_REQUIRES_FULL_LOADED_TRANSIENT',
          zero_source_op_passed=True,sources_unchanged=True,native_devices=845,auxiliary_contacts=4,
          terminal_probes=2737,vectors=len(coverage['vectors']),full1us_deck_preserved=True,
          biased_operating_point_accepted=False,native_full_transient_executed=False)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
