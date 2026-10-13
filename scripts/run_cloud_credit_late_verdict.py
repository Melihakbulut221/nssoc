#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-bound factoring of the final credit update verdict."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-credit-late-verdict'
SOURCE_SHA = 'ba8adb6fe529df4480a1b526d57a7d75b34a6c74ceed2e4a85ab8777521de7b9'
ARCHIVE_SHA = '3b639453fc6b011703961c444b8a06e6f7823714d9b22db331017d3bcf8f53eb'
URL = 'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38466891418-1-ack-map-physical_idle/ack-map-physical_idle-38466891418-1.tar.gz'
MEMBER = 'cloud-ack-map/physical_idle/inputs/root/hw/soc/out/pcie-metadata-late-select-20261010/candidate02/soc_pcie_credit_tx.v'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def candidate(text):
    old = """        wire h_update_ok=hi[bank] ? fc_header_i==0 :
            (!h_step[7] && (!h_idle_remaining[7] || (bank_consume && !h_debit_remaining[7])));
        wire d_update_ok=di[bank] ? fc_data_i==0 :
            (!step_sign && (!idle_sign || (bank_consume && !update_sign)));
        assign class_update_ok[bank]=h_update_ok && d_update_ok;"""
    new = """        // Evaluate both joint verdicts before the late reservation enable.
        // This is exact Boolean distribution, including simultaneous FC/debit.
        (* keep = "true" *) wire update_idle_header=hi[bank] ? fc_header_i==0 :
            (!h_step[7] && !h_idle_remaining[7]);
        (* keep = "true" *) wire update_idle_data=di[bank] ? fc_data_i==0 :
            (!step_sign && !idle_sign);
        (* keep = "true" *) wire update_consume_header=hi[bank] ? fc_header_i==0 :
            (!h_step[7] && (!h_idle_remaining[7] || !h_debit_remaining[7]));
        (* keep = "true" *) wire update_consume_data=di[bank] ? fc_data_i==0 :
            (!step_sign && (!idle_sign || !update_sign));
        (* keep = "true" *) wire update_idle_joint=update_idle_header && update_idle_data;
        (* keep = "true" *) wire update_consume_joint=update_consume_header && update_consume_data;
        assign class_update_ok[bank]=update_idle_joint || (bank_consume && update_consume_joint);"""
    assert text.count(old) == 1
    return text.replace(old, new)

def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    OUT.mkdir(exist_ok=False)
    record = dict(status='RUNNING', adopted=False, production_rtl_modified=False,
        scope='Exact physical credit RTL candidate, all outputs and explicit clock/reset. Frozen-reference and direct equivalence plus complete port tests and actual wrong-verdict control. No mapped timing or chip/PHY acceptance.')
    def save():
        (OUT/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    def execute(cmd, label, cwd=None):
        with (OUT/(label+'.log')).open('w') as log:
            p=subprocess.run(list(map(str,cmd)),cwd=cwd,stdout=log,stderr=subprocess.STDOUT)
        return p.returncode,(OUT/(label+'.log')).read_text(errors='replace')
    try:
        packed=OUT/'source.tar.gz'
        subprocess.run(['curl','--fail','--location','--retry','4',URL,'-o',str(packed)],check=True)
        assert packed.stat().st_size==16909757 and sha(packed)==ARCHIVE_SHA
        with tarfile.open(packed) as tar:
            raw=tar.extractfile(MEMBER).read()
        assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
        packed.unlink()
        original=raw.decode(); altered=candidate(original)
        anchor='assign class_update_ok[bank]=update_idle_joint || (bank_consume && update_consume_joint);'
        assert altered.count(anchor)==1
        wrong=altered.replace(anchor,'assign class_update_ok[bank]=!(update_idle_joint || (bank_consume && update_consume_joint));')
        dirs={}
        for name,text in [('baseline',original),('candidate',altered),('wrong_verdict',wrong)]:
            d=OUT/(name+'-rtl');d.mkdir();(d/'soc_pcie_credit_tx.v').write_text(text);dirs[name]=d
        record['source_binding']=dict(archive_url=URL,archive_sha256=ARCHIVE_SHA,member=MEMBER,source_sha256=SOURCE_SHA,
            candidate_sha256=sha(dirs['candidate']/'soc_pcie_credit_tx.v'),wrong_sha256=sha(dirs['wrong_verdict']/'soc_pcie_credit_tx.v'))
        yosys=shutil.which('yosys');iverilog=shutil.which('iverilog')
        assert yosys and iverilog
        record['runtime']=dict(yosys=subprocess.check_output([yosys,'-V'],text=True).strip())
        record['direct_proofs']=[]
        for name,text in [('candidate',altered),('wrong_verdict',wrong)]:
            d=OUT/('direct-'+name);d.mkdir()
            for module,source in [('gold',original),('gate',text)]:
                assert source.count('module soc_pcie_credit_tx (')==1
                (d/(module+'.v')).write_text(source.replace('module soc_pcie_credit_tx (','module '+module+' ('))
            (d/'proof.ys').write_text('\n'.join([
                'read_verilog -sv gold.v gate.v','proc','memory_map','opt',
                'clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv',
                'equiv_simple','equiv_induct -seq 4','equiv_status -assert','']))
            code,log=execute([yosys,'-s','proof.ys'],'direct-'+name,d)
            counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
            passed=code==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!' in log
            rejected=code!=0 and bool(counts) and int(counts[-1][1])>0
            record['direct_proofs'].append(dict(case=name,returncode=code,counts=counts,passed=passed,negative_rejected=rejected,log_sha256=sha(OUT/('direct-'+name+'.log'))))
            save()
        record['reference_proofs']=[]
        for name in ['baseline','candidate']:
            out=OUT/('frozen-'+name)
            code,log=execute([sys.executable,ROOT/'scripts/check_pcie_credit_equivalence.py',
                '--candidate',dirs[name]/'soc_pcie_credit_tx.v','--out',out,'--yosys',yosys],'frozen-'+name)
            result=json.loads((out/'result.json').read_text())
            record['reference_proofs'].append(dict(case=name,returncode=code,result=result));save()
        record['ports']=[]
        for name in ['baseline','candidate','wrong_verdict']:
            out=OUT/('ports-'+name)
            code,log=execute([sys.executable,ROOT/'scripts/check_pcie_flow.py',
                '--out',out,'--rtl-dir',dirs[name],'--iverilog-dir',Path(iverilog).parent],'ports-'+name)
            result=json.loads((out/'result.json').read_text())
            from cocotb_results import count_results
            xml=out/'results.xml';assert xml.is_file()
            passed,failed,skipped=count_results([xml])
            record['ports'].append(dict(case=name,returncode=code,result=result,
                actual_tests=dict(passed=passed,failed=failed,skipped=skipped),xml_sha256=sha(xml)))
            save()
            assert skipped==0 and passed+failed==result['expected_tests']
            if name=='wrong_verdict':
                assert code!=0 and failed>0 and 'AssertionError' in (out/'simulation.log').read_text(errors='replace')
            else:
                assert code==0 and failed==0 and result['status']=='PASS_PORT_ONLY_PCIE_CREDITS'
        assert record['direct_proofs'][0]['passed'] and record['direct_proofs'][1]['negative_rejected']
        assert all(p['returncode']==0 and p['result']['status']=='PASS_SEQUENTIAL_EQUIVALENCE' for p in record['reference_proofs'])
        record['status']='PASS_PHYSICAL_CREDIT_VERDICT_EQUIVALENCE_AND_COMPLETE_CONTROLS_NOT_TIMING'
    except BaseException as error:
        record.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        save()

if __name__=='__main__':
    main()
