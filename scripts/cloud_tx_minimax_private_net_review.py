#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Infer private mux net identities from actual HBTs with independently anchored bases."""
import copy,hashlib,json,os
from collections import defaultdict
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-minimax-private-net-review'
def infer(report):
    native=report['native'];reference=report['schematic_reference']
    assert not native['shorted_logical_groups']and not native['opened_logical_nets']
    anchors=defaultdict(set)
    for a in native['anchors']:
        assert a['native_cluster']is not None
        anchors[a['native_cluster']].add(a['logical_net'])
    assert all(len(v)==1 for v in anchors.values())
    logical={c:next(iter(v))for c,v in anchors.items()}
    expected=defaultdict(list);actual=defaultdict(list)
    for line in reference.splitlines():
        f=line.split()
        if f and f[0].startswith('Q'):
            assert f[5]=='npn13G2'
            nx=int(next(x.split('=')[1]for x in f[6:]if x.startswith('Nx=')))
            expected[(f[2],nx,f[1]==f[2])].append(dict(name=f[0],C=f[1],B=f[2],E=f[3],S=f[4]))
    hbts=[d for d in native['devices']if d['model']=='npn13G2']
    assert len(hbts)==589==sum(map(len,expected.values()))
    for d in hbts:
        t=d['terminals'];assert t['B']['cluster']in logical,('Unbound actual HBT base',d['id'])
        key=(logical[t['B']['cluster']],int(d['parameters']['Nx']),t['C']['cluster']==t['B']['cluster'])
        actual[key].append(d)
    assert set(expected)==set(actual)
    assignments=defaultdict(list)
    for cluster,name in logical.items():assignments[name].append(dict(cluster=cluster,source='independent_native_macro_pin_probe'))
    witnesses=[]
    for key,refs in sorted(expected.items()):
        devices=actual[key];assert len(devices)==len(refs),(key,len(refs),len(devices))
        # Every group is a real set of symmetric parallel HBTs. Do not assign
        # individual device identity by ID order or fit a schematic equivalence.
        for term in ('C','E','S'):
            nets={r[term]for r in refs};assert len(nets)==1,(key,term,nets)
            net=next(iter(nets));clusters={d['terminals'][term]['cluster']for d in devices}
            for cluster in sorted(clusters):
                assignments[net].append(dict(cluster=cluster,source='native_hbt_anchored_base_group',
                    base=key[0],nx=key[1],diode_connected=key[2],terminal=term,
                    reference_devices=[r['name']for r in refs],
                    native_devices=[d['id']for d in devices if d['terminals'][term]['cluster']==cluster]))
        witnesses.append(dict(base=key[0],nx=key[1],diode_connected=key[2],reference_count=len(refs),native_count=len(devices)))
    groups=defaultdict(set);opens={}
    for name,proof in assignments.items():
        clusters={p['cluster']for p in proof}
        if len(clusters)!=1:opens[name]=sorted(clusters)
        for cluster in clusters:groups[cluster].add(name)
    merges={str(c):sorted(names)for c,names in groups.items()if len(names)>1}
    assert len(assignments)==378,'Every original metal/body net must be assigned independently'
    assert not opens,('Private net open or ambiguous identity',opens)
    return dict(native_hbts=589,reference_hbts=589,derived_net_identities=len(assignments),
                native_clusters=len(groups),merged_private_or_public_nets=merges,opened_private_nets=opens,
                assignments=dict(assignments),group_witnesses=witnesses,
                method='Group native HBTs by independently probed base net, Nx and diode-connected C=B role. Parallel devices share C/E/S reference nets, yielding private net identities without using the failing LVS equivalence mapping. All589 native HBTs and378 intended nets are covered.')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-v5-minimax-second-native-lvs-diagnosis-20261019.json').read_text())
        assert pin['run']==39262021607 and pin['summary_sha256']=='3647994d9356633193e6b2be2ce2f17baec66fca2758a6589d48453ad1e405c4'
        url=f"https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{pin['run']}-1-tx-v5-minimax-lvs-review/tx-v5-minimax-lvs-review-{pin['run']}-1.summary.json"
        path=OUT/'original-native-review.json';fetch(url,pin['summary_sha256'],path)
        original=json.loads(path.read_text());assert original==pin['report']
        proof=infer(original);controls=[]
        bad=copy.deepcopy(original);i=next(i for i,d in enumerate(bad['native']['devices'])if d['model']=='npn13G2');bad['native']['devices'].pop(i)
        try:infer(bad)
        except AssertionError:controls.append('missing_native_hbt')
        else:raise AssertionError('Accepted missing HBT')
        bad=copy.deepcopy(original);d=next(d for d in bad['native']['devices']if d['model']=='npn13G2');d['parameters']['Nx']=999
        try:infer(bad)
        except AssertionError:controls.append('changed_native_emitter_count')
        else:raise AssertionError('Accepted wrong Nx')
        bad=copy.deepcopy(original);d=next(d for d in bad['native']['devices']if d['model']=='npn13G2');d['terminals']['B']['cluster']=-999
        try:infer(bad)
        except AssertionError:controls.append('unbound_native_base')
        else:raise AssertionError('Accepted unbound base')
        assert sha(path)==pin['summary_sha256']
        r.update(status='COMPLETE_ALL589_NATIVE_HBT_PRIVATE_NET_DIAGNOSIS_NOT_ACCEPTANCE',
            source_run=pin['run'],source_summary_sha256=pin['summary_sha256'],diagnosis=proof,
            controls=controls,sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={p.name:sha(p)for p in OUT.iterdir()if p.is_file()and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
