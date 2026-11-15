import pathlib,subprocess,json,hashlib
p=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_credit_tx.v');original=p.read_text()
old='b_dd_negative<=sign12(class_dd[a_class]);';assert original.count(old)==1
out=pathlib.Path('credit-mutation-evidence');out.mkdir()
try:
    p.write_text(original.replace(old,'b_dd_negative<=!sign12(class_dd[a_class]);'))
    run=subprocess.run(['bash','scripts/check_pcie_credit_pick.sh','credit-mutant','20000'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (out/'runner.log').write_bytes(run.stdout)
    logs=list(pathlib.Path('credit-mutant').glob('*.log'))
    detected=any('CREDIT_DATA_SIGN_MISMATCH' in log.read_text() for log in logs)
    record=dict(returncode=run.returncode,detected=detected,accepted_mutation=False,source_sha256=hashlib.sha256(original.encode()).hexdigest(),logs={log.name:hashlib.sha256(log.read_bytes()).hexdigest() for log in logs})
    (out/'result.json').write_text(json.dumps(record,indent=2))
    assert run.returncode!=0 and detected
finally:
    p.write_text(original)
assert p.read_text()==original
