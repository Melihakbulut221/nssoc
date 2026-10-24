#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind exact observed transient and OP tables; never normalize captured column identities."""
import copy,hashlib,json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import read_pll_rhi120_c8_all_native as reader
import read_pll845_full_native_op as full_op
ROOT=Path(__file__).resolve().parents[1]
CONTRACT_SHA='fc36b8aec35974c35c5dd3f5041f87d6667a0d76e60a3dbac7d47cd8728b79f8'
OP_SHA='980d4fd6eb4915bf6b02f8b2ef43ff5fbe383bb2f9f8e4c90f3eea613f75d769'
PREFIX_SHA='cbcbebbfab317af540122073e04be40ac2a6272d30bdabfe5b2b60398280dd8a'
AUDIT_SUMMARY='8a6526930af37675f23ed4c7937d27e4ae492246ecfaeb831da15496eff521d1'
AUDIT_PARTS='1587bd4482f64ec65e3ecf468ae3b64628fe97ac33215a4ce7a51de230c05527'
def digest(b):return hashlib.sha256(b).hexdigest()
def op_table(raw):
    assert digest(raw)==OP_SHA
    text=raw[:raw.index(reader.MARKER)].decode('ascii')
    table=[line.split()for line in text.split('Variables:\n',1)[1].splitlines()]
    assert len(table)==5105 and all(len(row)==3 for row in table)
    assert [row[0]for row in table]==list(map(str,range(5105)))
    return table
def check_tables(table,op,reference):
    contract=reference['contract']
    assert digest((json.dumps(contract,indent=2)+'\n').encode())==CONTRACT_SHA
    assert table==reader.contract_check(contract),'Different actual transient table'
    assert op==op_table(reference['op_raw']),'Different actual OP table'
    # The captured tables remain byte-for-byte named and ordered as observed.
    # This mapping explains the original assertion failure; it does not authorize
    # new names or normalize a raw capture accepted by read()/capture().
    t={(row[1],row[2])for row in table[1:]};o={(row[1],row[2])for row in op}
    assert len(t)==len(o)==5105
    assert len({(n.lower(),u)for n,u in t})==len({(n.lower(),u)for n,u in o})==5105
    assert {(n.lower(),u)for n,u in t}=={(n.lower(),u)for n,u in o}
    td=sorted(t-o);od=sorted(o-t)
    assert len(td)==len(od)==939
    assert [list(x)for x in td]==reference['audit']['transient_only']
    assert [list(x)for x in od]==reference['audit']['op_only']
    pairs={n.lower():(n,u)for n,u in od}
    for name,unit in td:
        other,u=pairs[name.lower()]
        assert unit==u=='voltage'and '#'in name and '#'in other
        assert name.rsplit('#',1)[0]==other.rsplit('#',1)[0]
        assert name.rsplit('#',1)[1].lower()==other.rsplit('#',1)[1]
    return dict(exact_transient_table=True,exact_op_table=True,case_spelling_pairs=939,
      collision_free_identity_bijection=True,raw_columns_renamed=False,columns=5106,
      required_terminal_vectors=1694,dropped_columns=0)
def load_reference(out):
    out=Path(out);reports.OUT=out
    audit,proof=reports.restore_report('pll-rhi120-c8-header-audit',39937306316,
      AUDIT_SUMMARY,AUDIT_PARTS,out/'audit',
      ['actual-native-prefix.bin','actual-op.raw','observed-column-contract.json'])
    assert audit['status']=='COMPLETE_ORIGINAL_ARCHIVE_AND_NATIVE_TABLE_DIAGNOSIS_NOT_RESUME_OR_ACCEPTANCE'
    assert audit['source_head']=='3096cdb182190ed6572e1705c1e0feb2bb9553bf'
    assert audit['whole_archive_verified']and audit['every_original_member_hash_verified']
    assert audit['source_run']==39925042125 and audit['observed_member_count']==1857
    assert audit['original_width_assertion']and not audit['original_op_identity_assertion']
    assert audit['original_required_vector_assertion']and not audit['required_missing']
    base=out/'audit';cb=(base/'observed-column-contract.json').read_bytes()
    prefix=(base/'actual-native-prefix.bin').read_bytes();op=(base/'actual-op.raw').read_bytes()
    assert digest(cb)==CONTRACT_SHA and digest(prefix)==PREFIX_SHA and digest(op)==OP_SHA
    ref=dict(contract=json.loads(cb),op_raw=op,prefix=prefix,audit=audit,restore_proof=proof)
    table,meta=reader.parse(prefix);check_tables(table,op_table(op),ref)
    assert meta['columns']==5106
    return ref
def controls(reference):
    table=reference['contract']['raw_table'];op=op_table(reference['op_raw'])
    positive=check_tables(table,op,reference);rejected=[]
    for label in ('renamed-transient','casefolded-transient','wrong-unit','duplicate-transient','reordered-transient','missing-op','casefolded-op'):
        t,o=copy.deepcopy((table,op))
        if label=='renamed-transient':t[1][1]='v(unrecognized_terminal)'
        elif label=='casefolded-transient':
            row=next(r for r in t if '#GP)'in r[1]);row[1]=row[1].lower()
        elif label=='wrong-unit':t[1][2]='current'
        elif label=='duplicate-transient':t[2]=copy.deepcopy(t[1])
        elif label=='reordered-transient':t[1],t[2]=t[2],t[1]
        elif label=='missing-op':o.pop()
        else:
            row=next(r for r in o if '#gp)'in r[1]);row[1]=row[1].replace('#gp)','#GP)')
        try:check_tables(t,o,reference)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted changed actual table: '+label)
    assert len(rejected)==7
    return dict(positive=positive,rejected=rejected)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'cloud-pll-rhi120-c8-column-qualification';out.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_started=False,checkpoint_resumed=False,
      full_capture_accepted=False,acquisition_accepted=False,full_phy_accepted=False)
    try:
        ref=load_reference(out)
        r['source_audit']=ref['restore_proof'];r['table_controls']=controls(ref)
        r['reader_controls']=reader.controls(ref['contract'],ref['prefix'],out/'reader-controls')
        r['op_controls']=full_op.controls(ref['op_raw'],ref['contract']['required_vectors'])
        assert len(r['reader_controls']['controls'])==16 and len(r['op_controls'])==12
        r['native_position']=ref['audit']['native_position']
        r['original_failure_preserved']=True
        r['status']='PASS_EXACT_ACTUAL_TABLES_ALL_COLUMNS_AND35_CONTROLS_NOT_CAPTURE_OR_RECOVERY'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        def file_sha(p):
            with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
        r['outputs']={str(p.relative_to(out)):file_sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
        (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
