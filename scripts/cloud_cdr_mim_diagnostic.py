#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native sensitivity experiment; scaled wires are NEVER a physical repair.

All394 devices, allnodes, initial conditions, original data and every measurement
threshold remain unchanged. Changes only explicit measured R/C values according
to the selected diagnostic, retaining original model and a complete edit ledger.
"""
import argparse,hashlib,importlib.util,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='53eb709f4d3b27503f01d8b70abcf5743ee196c4e16d0b6c102a9788eac4d85b'

def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=['low_r','low_c','low_rc'],required=True);p.add_argument('--case',choices=['nominal_early','nominal_late'],required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    source=ROOT/'scripts/cloud_cdr_mim_loaded.py';text=source.read_text();assert hashlib.sha256(text.encode()).hexdigest()==BASE_SHA
    original=text;ledger=[]
    def edit(a,b):
        nonlocal text
        assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b);ledger.append(dict(before=a,after=b))
    edit("out=ROOT/('cloud-cdr-mim-loaded-'+args.case)","out=ROOT/('cloud-cdr-mim-diagnostic-__VARIANT__-'+args.case)".replace('__VARIANT__',args.variant))
    anchor="        pp=ROOT/'docs/evidence/cdr-retimed-planes-pass-20261018.json'"
    replacement=r"""        original_model=model
        original_text=model.read_text();rows=parser.statements(original_text);changes=[]
        factors={'R':Decimal('__RSCALE__'),'C':Decimal('__CSCALE__')}
        for row in rows[1:-1]:
            if row[0][0]not in factors:continue
            assert len(row)==4
            factor=factors[row[0][0]]
            if factor==1:continue
            before=row[3];after=str(parser.number(before)*factor)
            assert parser.number(before)>0 if row[0].startswith('R')else parser.number(before)>=0
            row[3]=after;changes.append(dict(element=row[0],nodes=row[1:3],before=before,after=after,factor=str(factor)))
        expected=8956 if '__VARIANT__'=='low_r'else 7660 if '__VARIANT__'=='low_c'else 16616
        assert len(changes)==expected
        original_rows=parser.statements(original_text)
        for before,after in zip(original_rows,rows,strict=True):
            if before[0][0]in factors:assert before[:3]==after[:3]and parser.number(after[3])==parser.number(before[3])*factors[before[0][0]]
            else:assert before==after
        model=out/'diagnostic-model.spice';model.write_text('\n'.join(' '.join(row)for row in rows)+'\n')
        (out/'wire-value-changes.json').write_text(json.dumps(changes,indent=2)+'\n')
        r['wire_diagnostic']=dict(variant='__VARIANT__',R_factor=str(factors['R']),C_factor=str(factors['C']),original_model_sha256=sha(original_model),diagnostic_sha256=sha(model),unchanged_intrinsic_devices=394,changed_wire_values=len(changes),physical_layout_matches=False,adoption_prohibited=True)
        r['scope']='ARTIFICIALLY SCALED WIRE DIAGNOSTIC ONLY. '+r['scope']
        pp=ROOT/'docs/evidence/cdr-retimed-planes-pass-20261018.json'"""
    replacement=replacement.replace('__VARIANT__',args.variant).replace('__RSCALE__','0.001'if args.variant in ('low_r','low_rc')else'1').replace('__CSCALE__','0.001'if args.variant in ('low_c','low_rc')else'1')
    edit(anchor,replacement)
    edit("[Path(__file__),Path(legacy.__file__),model,pinpath,pp,","[Path(__file__),ROOT/'scripts/cloud_cdr_mim_loaded.py',Path(legacy.__file__),original_model,model,pinpath,pp,")
    edit("        assert passed,'Actual whole-wire retimed sampling, loaded phase/current or device gate failed'","        r['diagnostic_gates_passed']=passed\n        r['status']='COMPLETE_NATIVE_WIRE_SENSITIVITY_NOT_PHYSICAL_REPAIR'\n        assert sha(original_model)==prior['outputs']['pd394-mim-wire.spice']")
    target=ROOT/'scripts/_cloud_cdr_mim_diagnostic_method.py';assert not target.exists();target.write_text(text)
    spec=importlib.util.spec_from_file_location('cdr_mim_diagnostic_method',target);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sys.argv=[str(target),'--case',args.case]
    module.main()
    out=ROOT/('cloud-cdr-mim-diagnostic-'+args.variant+'-'+args.case)
    (out/'method-changes.json').write_text(json.dumps(dict(source_sha256=BASE_SHA,private_sha256=hashlib.sha256(text.encode()).hexdigest(),edits=ledger),indent=2)+'\n')
    # Add post-run controller receipt to published manifest without touching waves.
    r=json.loads((out/'result.json').read_text());r['outputs']['method-changes.json']=hashlib.sha256((out/'method-changes.json').read_bytes()).hexdigest()
    (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    assert source.read_text()==original
if __name__=='__main__':main()
