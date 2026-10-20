#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the fixed three-group candidate to actual failed selector terminals."""
import hashlib,io,json,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39370785088-1-tx-fast-wire24-path-review/'
SUMMARY='4f9b3e60f7c46ce05a42a4b69c94b005da55005db7333aca894754d4c763d71b'
ARCHIVE='44b689df97efda9f5eb4eaaf97043fca0d14e2f72f9e9c1ac6b1e8d3a12840ac'
def validate(out):
    out=Path(out);stem='tx-fast-wire24-path-review-39370785088-1'
    summary=out/'selection-source-summary.json';packed=out/'selection-source.tar.gz'
    fetch(BASE+stem+'.summary.json',SUMMARY,summary)
    r=json.loads(summary.read_text())
    assert r['status']=='COMPLETE_NATIVE_TX_WIRE24_PATH_REVIEW_ORIGINAL_GATES_REMAIN_FAILED'
    assert r['source_head']=='fa85ed972261e9c99ef882d264a1ef408949631a'
    assert r['original_gates_reproduced']and r['sources_unchanged']
    assert r['original_signal_gate']['wrong_sign_samples']==83
    fetch(BASE+stem+'.tar.gz.part0000',ARCHIVE,packed)
    with tarfile.open(packed)as tar:
        name='cloud-tx-fast-wire24-path-review/native-clock-terminals.json'
        raw=tar.extractfile(name).read()
        assert hashlib.sha256(raw).hexdigest()==r['outputs']['native-clock-terminals.json']
        c=json.loads(raw)
    assert c['clock_count']==31 and c['actual_selector_bases']==124
    failed={d['device']:d for d in r['failed_hbt_terminal_review']}
    assert len(failed)==24
    groups={}
    for clock in c['clocks']:
        keys={p[k]['device']for p in clock['terminal_pairs']for k in ('positive','negative')}
        hits=keys&set(failed)
        if hits:groups.setdefault(clock['clock']['reference'],set()).update(hits)
    assert set(groups)=={'clkbias','clkbias_g2','clkbias_g3','clkbias_g4'}
    assert {k:len(v)for k,v in groups.items()}=={'clkbias':4,'clkbias_g2':4,'clkbias_g3':4,'clkbias_g4':10}
    affected=set.union(*(groups['clkbias_g'+str(g)]for g in (2,3,4)))
    assert len(affected)==18
    assert set(failed)-set.union(*groups.values())=={'xtree.xd0114','xtree.xd0115'}
    result=dict(source_summary_sha256=SUMMARY,source_archive_sha256=ARCHIVE,
        unchanged_source_head=r['source_head'],changed_groups=[2,3,4],
        actual_failed_selector_groups={k:sorted(v)for k,v in groups.items()},
        affected_failed_selector_count=18,
        unchanged_final_group_failed_selectors=4,unchanged_final_tails=2,
        reason='Test lower-bias already-physical l5p7 macros only in groups2/3/4; original0.4V device bound and all signal/interface gates remain.',
        candidate_simulation_or_phy_accepted=False)
    (out/'selection-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
