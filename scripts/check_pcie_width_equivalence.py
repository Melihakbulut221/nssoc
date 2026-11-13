# SPDX-License-Identifier: Apache-2.0
"""Check default-parameter sequential equivalence of width-only changes.
Not a timing, CDC, analog, or full-chip signoff. Unknown/undefined semantics
follow Yosys equiv rules; the simulation regressions remain required.
"""
import json,pathlib,subprocess,sys,time
BASE='e6e887d858f30730da11fbe575c4b07550225257'
MODULES=['soc_pcie_lcrc_rx','soc_pcie_packet_endpoint','soc_pcie_credit_tx','soc_pcie_lcrc_tx','soc_pcie_replay_tx','soc_pcie_rx_credit','soc_pcie_tlp_integrity']
FLAGS=['SOC_PCIE_RX_READ2','SOC_PCIE_RESET_COPIES','SOC_PCIE_REPLAY_INBANK','SOC_PCIE_TX_WORD_REG','SOC_PCIE_REPLAY_AHEAD','SOC_PCIE_CREDIT_PICK','SOC_PCIE_SEQ_RX_REG','SOC_PCIE_RX_COMMIT_COPIES']
cfg=sys.argv[1];assert cfg in ('default','cut10')
out=pathlib.Path('out');out.mkdir(exist_ok=True)
gold=out/'gold';gold.mkdir(exist_ok=True)
subprocess.run(['git','fetch','--depth=1','origin',BASE],check=True)
files=sorted(pathlib.Path('hw/soc/rtl/pcie').glob('*.v'));assert files
for p in files:
    content=subprocess.check_output(['git','show',BASE+':'+str(p)])
    (gold/p.name).write_bytes(content)
def design(folder,top,name):
    flags=' -D SYNTHESIS '+(' '.join('-D '+x for x in FLAGS) if cfg=='cut10' else '')
    return f'read_verilog -sv {flags} {folder}/*.v; hierarchy -check -top {top}; proc; flatten; opt; memory_map; opt; async2sync; opt; rename {top} {name}; design -stash {name};'
results=[]
for top in MODULES:
    ys=design(gold,top,'gold')+design('hw/soc/rtl/pcie',top,'gate')
    ys+='design -copy-from gold -as gold gold; design -copy-from gate -as gate gate; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 4; equiv_status -assert;'
    (out/(top+'.ys')).write_text(ys)
    began=time.monotonic()
    with (out/(top+'.log')).open('w') as log:
        try:
            rc=subprocess.run(['yosys','-p',ys],stdout=log,stderr=subprocess.STDOUT,timeout=600).returncode
        except subprocess.TimeoutExpired:rc=124
    text=(out/(top+'.log')).read_text()
    passed=rc==0 and 'Equivalence successfully proven!' in text
    row=dict(module=top,configuration=cfg,returncode=rc,passed=passed,seconds=time.monotonic()-began)
    results.append(row);print(json.dumps(row),flush=True)
    (out/'result.json').write_text(json.dumps(dict(base=BASE,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),configuration=cfg,results=results,passed=len(results)==len(MODULES) and all(x['passed'] for x in results)),indent=2))
sys.exit(0 if all(x['passed'] for x in results) else 1)
