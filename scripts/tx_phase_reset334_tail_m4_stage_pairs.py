#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact current parent-stage contacts; diagnostic pairs never replace acceptance pairs."""
import copy,json
from pathlib import Path
import tx_phase_reset334_saved_diagnosis as original
ROOT=Path(__file__).resolve().parents[1]
DESCRIPTOR='scripts/tx-phase-reset334-tail-m4-stage-pairs.json'
DESCRIPTOR_SHA='281adf61e07645f535546479f66857b9c975245cf0c9fa7b3f0360f733371739'
HBT_TERMS=('C','B','E','S')

def descriptor():
    raw=original.pin(ROOT/DESCRIPTOR,DESCRIPTOR_SHA)
    d=json.loads(raw)
    assert d['schema']=='exact-current-tail-M4-parent-stage-pairs-v1'
    assert d['diagnostic_only']is True and d['acceptance_thresholds_changed']is False
    assert (d['expected_original_pairs'],d['expected_additional_pairs'],d['expected_total_pairs'])==(24,12,36)
    assert len(d['original_pairs'])==24 and len(d['added_pairs'])==12
    assert not set(d['original_pairs'])&set(d['added_pairs'])
    assert set(d['endpoint_provenance'])==set(d['added_pairs'])
    original.pin(ROOT/d['source_note']['path'],d['source_note']['sha256'])
    probe=json.loads(original.pin(ROOT/d['prior_probe_inventory']['path'],d['prior_probe_inventory']['sha256']))
    assert probe['contract_sha256']==d['contract_sha256']
    assert probe['native_pair_nodes']==d['original_pairs']
    assert len(probe['all_native_HBT_roles'])==318 and len(probe['added_source_bound_topology']['passive_accesses'])==168
    return d,probe

def check_pairmap(c,pairmap):
    d,_=descriptor()
    expected=dict(d['original_pairs'],**d['added_pairs'])
    assert type(pairmap)is dict and pairmap==expected,'Stage pair names/order/polarity or endpoints changed'
    assert original.pairs(c)==d['original_pairs'],'Original24 pair mapping changed'
    assert len(pairmap)==36
    for name,pair in pairmap.items():
        assert type(name)is str and type(pair)is list and len(pair)==2 and pair[0]!=pair[1]
        assert all(type(node)is str and 'v('+node+')'in c['vectors']for node in pair),'Missing stage voltage vector'
    return copy.deepcopy(pairmap)

def bind(c,topology):
    d,probe=descriptor()
    assert c['binding_summary_sha256']==d['binding_summary_sha256']
    assert c['hbt']==probe['all_native_HBT_roles'],'Current native HBT role inventory changed'
    assert topology==probe['added_source_bound_topology'],'Current source-bound topology changed'
    instances={s['instance']:s for s in c['instances']}
    assert len(c['instances'])==len(instances)==3 and set(instances)=={'xdut','xloadm','xloadq'}
    for instance,variant in (('xdut','p'),('xloadm','n'),('xloadq','p')):
        spec=instances[instance]
        assert spec['variant']==variant and spec['model_sha256']==d['model_sha256'][variant]
    result=check_pairmap(c,dict(d['original_pairs'],**d['added_pairs']))
    endpoint_proofs={}
    for name,pair in d['added_pairs'].items():
        entries=d['endpoint_provenance'][name]
        assert len(entries)==2 and [r['node']for r in entries]==pair
        proofs=[]
        for endpoint in entries:
            node=endpoint['node'];binding=endpoint['source_binding'];source=binding['source_instance']
            assert node.startswith('xdut.') and source.startswith('PHASE__')
            if 'native'in binding:
                native=binding['native'];terminal=binding['terminal'];assert terminal in HBT_TERMS
                role=c['hbt'][native]
                assert native=='xdut.xd'+str(role['native_id'])
                assert role['source_instance']==source and role['fixture_instance']=='xdut'and role['physical_preset']=='p'
                assert role['terminals'][HBT_TERMS.index(terminal)]==node
                assert binding['contract_pointer']=='/contract_hbt_roles/'+native
                proofs.append(dict(kind='native_HBT_contact',node=node,native=native,terminal=terminal,role=role))
            else:
                key='xdut:'+source;terminal=binding['terminal'];row=topology['passive_accesses'][key]
                assert row['source_instance']==source and row['native_id']==binding['native_id']
                assert terminal in ('rppd_1','rppd_2','rppd_sub')
                actual=row['terminals'][terminal]
                assert actual==binding['source_bound_terminal'] and actual['node']==node
                assert binding['topology_pointer']=='/source_bound_tail_topology/passive_accesses/'+key+'/terminals/'+terminal
                proofs.append(dict(kind='source_bound_rppd_contact',node=node,native_id=row['native_id'],terminal=terminal,source_instance=source,record=actual))
        endpoint_proofs[name]=proofs
    return result,dict(descriptor_sha256=DESCRIPTOR_SHA,source_capture_sha256=d['capture_sha256'],
      current_models=d['model_sha256'],contract_sha256=d['contract_sha256'],
      original_pairs=24,added_pairs=12,total_pairs=36,exact_endpoint_bindings=endpoint_proofs,
      original_acceptance_pairs_unchanged=True,added_pairs_are_diagnostic_only=True,
      physical_cause_established=False,native_simulation=False)
