#!/usr/bin/env python3
"""Full real replay RTL sequential equivalence; no memory blackboxing."""
import pathlib,subprocess,json,hashlib
out=pathlib.Path('out');out.mkdir(exist_ok=True)
rtl=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')
s=rtl.read_text()
# The golden implementation is the default build of exactly this source.
# No original branches are edited: only the default-off alternate write path.
# Keep both preprocessing products and proof logs on the runner.
rows=[]
for depth,size in [(2,22),(4,38)]:
    commands=[]
    for name,flags in [('gold',''),('gate','-D SOC_PCIE_REPLAY_WRITE_PREDECODE')]:
        commands += [f'read_verilog -sv {flags} hw/soc/rtl/pcie/soc_pcie_crc32_byte.v {rtl}',
          f'chparam -set DEPTH {depth} -set MAX_BYTES {size} soc_pcie_replay_tx',
          'prep -top soc_pcie_replay_tx -flatten', 'memory_map', 'opt', 'async2sync', 'opt',
          f'rename soc_pcie_replay_tx {name}',f'design -stash {name}']
    commands += ['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate',
      'equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple','equiv_induct -seq 4','equiv_status -assert']
    script=out/f'equiv-d{depth}-b{size}.ys';script.write_text(';\n'.join(commands)+'\n')
    log=out/f'equiv-d{depth}-b{size}.log'
    with log.open('w') as stream:
        result=subprocess.run(['yosys','-Q','-T','-s',str(script)],stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
    text=log.read_text()
    rows.append(dict(depth=depth,max_bytes=size,returncode=result.returncode,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),passed=result.returncode==0 and 'Equivalence successfully proven!' in text))
    (out/'equivalence.json').write_text(json.dumps(dict(rtl_sha256=hashlib.sha256(s.encode()).hexdigest(),cases=rows),indent=2)+'\n')
    assert rows[-1]['passed'], text[-5000:]
