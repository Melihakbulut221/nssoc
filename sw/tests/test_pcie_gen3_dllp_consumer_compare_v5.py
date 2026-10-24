# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual old/new public-port comparison and three non-equivalent controls."""
import json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_dllp_consumer_v5.v'
FAULTS=[('raw_destination',"13'd0: begin","13'd4: begin",'sustained_two_dllps_per_cycle_and_sequence_wrap'),('count_overflow','if(count_sum[13]) local_entry_error=1;',"if(1'b0) local_entry_error=1;",'full_received_counter_overflow_via_public_body'),('release_omitted','if(released[entry]) begin',"if(1'b0) begin",'exact_id_full_replace_and_held_generation')]

def run(tmp,rtl=None,case=None):
 tool=shutil.which('iverilog');assert tool and shutil.which('vvp')
 cmd=[sys.executable,str(ROOT/'scripts/check_pcie_gen3_dllp_consumer_compare_v5.py'),'--out',str(tmp/'capture'),'--iverilog-dir',str(Path(tool).parent)]
 if rtl:cmd+=['--rtl',str(rtl)]
 if case:cmd+=['--test',case]
 with (tmp/'launch.log').open('w') as log:p=subprocess.run(cmd,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT)
 return p,json.loads((tmp/'capture/result.json').read_text()),(tmp/'capture/simulation.log').read_text()

def test_actual_all_nine_public_comparisons(tmp_path):
 p,r,log=run(tmp_path)
 assert p.returncode==0 and r['tests']=={'passed':9,'failed':0,'skipped':0}
 assert 'Public v1/v2/v3/v4/v5 mismatch' not in log

@pytest.mark.parametrize('name,before,after,case',FAULTS,ids=[x[0] for x in FAULTS])
def test_actual_non_equivalent_static_entries_rejected(tmp_path,name,before,after,case):
 source=SOURCE.read_text();assert source.count(before)==1
 mutant=tmp_path/'mutant.v';mutant.write_text(source.replace(before,after))
 p,r,log=run(tmp_path,mutant,case)
 assert p.returncode!=0 and r['status']=='FAIL'
 assert 'Public v1/v2/v3/v4/v5 mismatch' in log, 'Compile, launch or unrelated assertion is not equivalence rejection'
