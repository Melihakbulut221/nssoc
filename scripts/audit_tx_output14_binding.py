#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the actual TX bench output stage to its native unsimplified physical reference."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import copy,hashlib,json,sys
from build_pcie_local_vco_hybrid_v6 import statements,number
from cloud_tx_lane_boundaries import definitions
PORTS='inp inn outp outn avdd avss sub iref'.split()
def audit(source,generated,inventory):
    source_def=definitions(source)
    assert set(source_def)=={'nssoc_tx_cml_rsil'}
    core=source_def['nssoc_tx_cml_rsil']
    actual=next(x for x in inventory['top_instances']if x['instance']=='xtx')
    assert actual['header']==core['header']and actual['external_body_cards']==core['body']
    assert actual['ports']==dict(inp='mp',inn='mn',outp='op',outn='on',avdd='tvdd',avss='0',sub='0',iref='tr')
    assert core['formal']==PORTS
    defaults=dict(x.lower().split('=',1)for x in core['header']if '='in x)
    assert defaults==dict(load_w='10u',load_l='70.215u',load_heat='1')
    probes=[r for r in core['body']if r[0].lower().startswith('v')]
    assert probes==[['VTAIL','tailmon','avss','0'],['VRP','avdd','loadp','0'],['VRN','avdd','loadn','0']]
    alias=dict(tailmon='avss',loadp='avdd',loadn='avdd')
    def sig(row,source_kind):
        row=[s.lower()for s in row];matches=[i for i,s in enumerate(row)if s in ('npn13g2','rsil','ptap1')]
        assert len(matches)==1
        i=matches[0];model=row[i];nodes=row[1:i]
        pairs=[s.split('=',1)for s in row[i+1:]];p=dict(pairs);assert len(p)==len(pairs)
        for k,v in p.items():
            if v.startswith('{'):assert source_kind and v.endswith('}')and v[1:-1]in defaults;p[k]=defaults[v[1:-1]]
        if model=='ptap1':
            assert not source_kind and nodes==['sub','bulk']and set(p)=={'a','p'}
            assert number(p['a'])==number('4p')and number(p['p'])==number('8u')
            return model,tuple(nodes),number(p['a']),number(p['p'])
        assert len(nodes)=={'npn13g2':4,'rsil':3}[model]
        if source_kind:
            assert nodes[-1]=='sub';nodes=[alias.get(n,n)for n in nodes[:-1]]+['bulk']
        assert nodes[-1]=='bulk'and 'sub'not in nodes
        assert number(p.get('m','1'))==1
        if model=='npn13g2':
            assert set(p)<={'nx','we','le','m'}and 'nx'in p
            assert number(p.get('we','0.07u'))==number('0.07u')
            assert number(p.get('le','0.9u'))==number('0.9u')
            return model,tuple(nodes),number(p['nx']),number('0.07u'),number('0.9u')
        assert {'w','l'}<=set(p)<={'w','l','m','sw_et'}
        assert number(p.get('sw_et','1'))==1
        return model,tuple(nodes),number(p['w']),number(p['l'])
    expected=Counter(sig(r,True)for r in core['body']if r not in probes)
    assert Counter(k[0]for k in expected.elements())==dict(npn13g2=4,rsil=2)
    defs=definitions(generated);assert set(defs)=={'nssoc_tx_cml_layout'}
    physical=defs['nssoc_tx_cml_layout'];assert physical['formal']==PORTS
    got=Counter(sig(r,False)for r in physical['body'])
    assert Counter(k[0]for k in got.elements())==dict(npn13g2=4,rsil=2,ptap1=8)
    expected[('ptap1',('sub','bulk'),number('4p'),number('8u'))]=8
    assert got==expected,'Actual output core connectivity or device geometry differs'
    return dict(status='PASS_ACTUAL_TX_OUTPUT_TO_NATIVE14_REFERENCE_WITH_EXPLICIT_BULK_CONTACT_ADAPTATION',
        native_hbts=4,native_rsil=2,native_contacts=8,ideal_probes_removed=probes,
        actual_instance_ports=actual['ports'],body_mapping='Ideal source SUB becomes internal BULK connected through eight native ptap1 cells to physical SUB. This change requires new extracted electrical simulation.',
        mainchip_integrated=False,parent_tree_integrated=False,qualified_pex=False)
def check(source,generated,inventory):
    r=audit(source,generated,inventory);faults=[]
    changes={
      'wrong_load_length':('l=70.215u','l=71u'),
      'wrong_finger_count':('Nx=8','Nx=7'),
      'missing_contact':('RTAP0 SUB BULK ptap1 A=4p P=8u\n',''),
      'bulk_short':('BULK npn13G2','AVSS npn13G2'),
      'wrong_input':('OUTN INP TAIL','OUTN INN TAIL')}
    for name,(a,b)in changes.items():
        assert a in generated
        mutant=generated.replace(a,b,1)
        try:audit(source,mutant,inventory)
        except (AssertionError,ValueError,KeyError):faults.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    wrong=copy.deepcopy(inventory)
    next(x for x in wrong['top_instances']if x['instance']=='xtx')['ports']['inp']='mn'
    try:audit(source,generated,wrong)
    except AssertionError:faults.append(dict(name='wrong_actual_parent_endpoint',rejected=True))
    else:raise AssertionError('Accepted wrong parent endpoint')
    r['controls']=faults;assert len(faults)==6
    return r
if __name__=='__main__':
    source,generated,inventory,out=map(Path,sys.argv[1:])
    r=check(source.read_text(),generated.read_text(),json.loads(inventory.read_text()))
    out.write_text(json.dumps(r,indent=2)+'\n')
