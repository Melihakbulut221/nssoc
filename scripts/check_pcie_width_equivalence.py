# SPDX-License-Identifier: Apache-2.0
"""Check default-parameter sequential equivalence of width-only changes.
Not a timing, CDC, analog, or full-chip signoff. Unknown/undefined semantics
follow Yosys equiv rules; the simulation regressions remain required.
"""
import json,pathlib,subprocess,sys,time,re,hashlib
from pcie_reference_x import normalize
BASE='e6e887d858f30730da11fbe575c4b07550225257'
MODULES=['soc_pcie_lcrc_rx','soc_pcie_packet_endpoint','soc_pcie_credit_tx','soc_pcie_lcrc_tx','soc_pcie_replay_tx','soc_pcie_rx_credit','soc_pcie_tlp_integrity']
FLAGS=['SOC_PCIE_RX_READ2','SOC_PCIE_RESET_COPIES','SOC_PCIE_REPLAY_INBANK','SOC_PCIE_TX_WORD_REG','SOC_PCIE_REPLAY_AHEAD','SOC_PCIE_CREDIT_PICK','SOC_PCIE_SEQ_RX_REG','SOC_PCIE_RX_COMMIT_COPIES']
cfg=sys.argv[1];assert cfg in ('default','cut10')
direction=sys.argv[2];assert direction in ('forward','reverse')
out=pathlib.Path('out');out.mkdir(exist_ok=True)
gold=out/'gold';gold.mkdir(exist_ok=True)
rawgold=out/'gold-raw';rawgold.mkdir(exist_ok=True)
normalization=[]
subprocess.run(['git','fetch','--depth=1','origin',BASE],check=True)
files=sorted(pathlib.Path('hw/soc/rtl/pcie').glob('*.v'));assert files
for p in files:
    content=subprocess.check_output(['git','show',BASE+':'+str(p)])
    (rawgold/p.name).write_bytes(content)
    normalized=normalize(p.name,content.decode()).encode()
    (gold/p.name).write_bytes(normalized)
    if content!=normalized:normalization.append(dict(file=p.name,raw_sha256=hashlib.sha256(content).hexdigest(),normalized_sha256=hashlib.sha256(normalized).hexdigest()))
(out/'reference-normalization.json').write_text(json.dumps(dict(base=BASE,rules='Explicit out-of-range X only; no address assumptions',changes=normalization),indent=2))
def design(folder,top,name):
    flags=' -D SYNTHESIS '+(' '.join('-D '+x for x in FLAGS) if cfg=='cut10' else '')
    # Parse all definitions, elaborate only the selected top and dependencies.
    # Eager elaboration previously spent the entire budget on unrelated variants.
    return f'read_verilog -defer -sv {flags} {folder}/*.v; hierarchy -check -top {top}; proc; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; flatten; opt -keepdc; memory_map; opt -keepdc; async2sync; opt -keepdc; rename {top} {name}; design -stash {name};'
subprocess.run([sys.executable,'scripts/check_pcie_selector_semantics.py',str(rawgold),'hw/soc/rtl/pcie'],check=True)
results=[]
for top in MODULES:
    ys=design(gold,top,'gold')+design('hw/soc/rtl/pcie',top,'gate')
    pair='gold gate' if direction=='forward' else 'gate gold'
    ys+=f'design -copy-from gold -as gold gold; design -copy-from gate -as gate gate; equiv_make {pair} equiv; hierarchy -top equiv; equiv_simple -undef; equiv_induct -undef -seq 4; equiv_status -assert;'
    # Separate every command explicitly; adjacent fragments are not Yosys tokens.
    ys = chr(10).join(cmd.strip() for cmd in ys.split(';') if cmd.strip()) + chr(10)
    script = out/(top+'.ys')
    script.write_text(ys)
    began=time.monotonic()
    with (out/(top+'.log')).open('w') as log:
        try:
            rc=subprocess.run(['yosys','-s',str(script)],stdout=log,stderr=subprocess.STDOUT,timeout=600).returncode
        except subprocess.TimeoutExpired:rc=124
    text=(out/(top+'.log')).read_text()
    passed=rc==0 and 'Equivalence successfully proven!' in text
    stages=re.findall(r'^.*Executing ([A-Z_]+) pass.*$',text,re.M)
    row=dict(module=top,configuration=cfg,direction=direction,explicit_undef=True,returncode=rc,passed=passed,seconds=time.monotonic()-began,last_pass=stages[-1] if stages else None,equivalence_make_reached='EQUIV_MAKE' in stages,equivalence_status_reached='EQUIV_STATUS' in stages)
    results.append(row);print(json.dumps(row),flush=True)
    (out/'result.json').write_text(json.dumps(dict(base=BASE,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),configuration=cfg,direction=direction,explicit_undef=True,requires_both_directions=True,reference_normalization=normalization,results=results,passed=len(results)==len(MODULES) and all(x['passed'] for x in results)),indent=2))
sys.exit(0 if all(x['passed'] for x in results) else 1)
