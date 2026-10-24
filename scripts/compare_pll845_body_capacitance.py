#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare complete conductor-collapsed C for identical geometry, changed probes."""
import copy,math
def compare(before,after):
    for r in (before,after):
        assert r['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert r['physical_wire_components']==235 and r['complete_collapsed_capacitance_conserved']
        assert not r['disconnected_probes']
    def rows(r):
        d={}
        for x in r['capacitance_edges_af']:
            k=(x['a'],x['b'])
            assert 0<=k[0]<k[1]<=235 and k not in d
            assert all(math.isfinite(x[n])and x[n]>=0 for n in ('source','baseline','distributed'))
            d[k]=x
        assert len(d)==r['collapsed_capacitance_edge_count']
        return d
    a,b=rows(before),rows(after)
    assert a.keys()==b.keys(),'Changed conductor capacitance edge identities'
    max_delta={}
    for field in ('source','baseline','distributed'):
        for k in a:
            assert math.isclose(a[k][field],b[k][field],rel_tol=3e-6,abs_tol=1e-4),('Same-geometry collapsed capacitance changed',k,field,a[k][field],b[k][field])
        max_delta[field]=max(abs(a[k][field]-b[k][field])for k in a)
    return dict(status='PASS_SAME_GEOMETRY_COMPLETE_COLLAPSED_C_MATRIX',edges=len(a),max_delta_af=max_delta,relative_tolerance=3e-6,absolute_tolerance_af=1e-4,point_distribution_claimed_equal=False)
def controls(before,after):
    cases=[]
    bad=copy.deepcopy(after);bad['capacitance_edges_af'].pop();cases.append(('missing_edge',bad))
    bad=copy.deepcopy(after);bad['capacitance_edges_af'][0]['distributed']+=1;cases.append(('changed_distributed_value',bad))
    bad=copy.deepcopy(after);bad['capacitance_edges_af'][0]['a']=236;cases.append(('wrong_conductor',bad))
    result=[]
    for name,bad in cases:
        try:compare(before,bad)
        except AssertionError as e:result.append(dict(name=name,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted matrix fault '+name)
    return result
