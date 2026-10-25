#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact external-interface census independent of native circuit matching."""
import re
def ports(text,top):
 logical=re.sub(r'\n[ \t]*\+[ \t]*',' ',text)
 rows=[line.split()for line in logical.splitlines()if line.strip()and line.split()[0].lower()=='.subckt'and len(line.split())>=2 and line.split()[1].upper()==top.upper()]
 assert len(rows)==1,'Missing or ambiguous top subcircuit'
 names=[n.upper()for n in rows[0][2:]]
 assert len(names)==len(set(names)),'Repeated public port'
 assert all(re.fullmatch(r'[A-Z0-9_]+',n)for n in names),'Aliased or malformed public port'
 return names
def compare(reference,extracted,top,expected_count=163):
 assert isinstance(expected_count,int) and expected_count>1
 expected=ports(reference,top);assert len(expected)==expected_count,f'Reference interface is not{expected_count} pins'
 try:
  actual=ports(extracted,top)
 except AssertionError as e:return dict(passed=False,reason=str(e),expected_count=expected_count)
 missing=sorted(set(expected)-set(actual));extra=sorted(set(actual)-set(expected))
 return dict(passed=len(actual)==expected_count and not missing and not extra,expected_count=expected_count,actual_count=len(actual),missing=missing,extra=extra)
def controls(expected_count=163):
 top='fixture';ref='.subckt fixture '+' '.join('p'+str(i)for i in range(expected_count))+'\n.ends fixture\n'
 assert compare(ref,ref.upper(),top,expected_count=expected_count)['passed']
 bads={
  'extra_internal_port':ref.replace('\n.ends',' internal\n.ends'),
  'missing_external_port':ref.replace(f' p{expected_count-1}\n','\n'),
  'alias_external_port':ref.replace(' p0 ',' p0|din '),
  'renamed_external_port':ref.replace(' p0 ',' wrong '),
  'duplicate_external_port':ref.replace(' p1 ',' p0 ')}
 for name,text in bads.items():assert not compare(ref,text,top,expected_count=expected_count)['passed'],name
 try:compare(ref,ref,top,expected_count=expected_count+1)
 except AssertionError:pass
 else:raise AssertionError('Wrong declared interface count accepted')
 return dict(wrong_declared_count_rejected=True,case_insensitive_native_spice_names=True,all_expected_ports_required=True,expected_count=expected_count,rejected=list(bads))
if __name__=='__main__':print(controls())
