"""Rebind only the ten admitted diode moves; preserve immutable input evidence."""
from copy import deepcopy
from check_antenna_netlist_export import check_added_antennas

EXPECTED = {
    'ANTENNA_491': ('nssoc_sta_n_100389', 'nssoc_regiso_0_net'),
    'ANTENNA_500': ('nssoc_sta_n_100405', 'nssoc_regiso_1_net'),
    **{'ANTENNA_'+str(i): ('nssoc_sta_n_60783', 'nssoc_regiso_3_net') for i in range(2569,2573)},
    **{'ANTENNA_'+str(i): ('nssoc_sta_n_60783', 'nssoc_regiso_4_net') for i in range(2573,2577)},
}

def rebind_inventory(cumulative, audit):
    assert audit['all_original_diodes_preserved']
    assert audit['functional_equivalence_by_identity_buffer_collapse']
    assert audit['antenna_protection_revalidation_required']
    assert audit['accepted'] is False
    moves = audit['moves']
    assert set(moves) == set(EXPECTED)
    result = deepcopy(cumulative)
    moved = {}
    for name, (old, new) in EXPECTED.items():
        assert moves[name] == dict(master='sg13g2_antennanp',old_net=old,new_net=new)
        old_terms = [dict(pin='A',type='SIGNAL',net=old)]
        new_terms = [dict(pin='A',type='SIGNAL',net=new)]
        if name in result:
            cell = result[name]
            assert cell['master'] == 'sg13g2_antennanp'
            assert cell['signal_terms'] == old_terms
            cell['signal_terms'] = deepcopy(new_terms)
            if 'terms' in cell:
                pins = [term for term in cell['terms'] if term['pin']=='A']
                assert pins == old_terms
                pins[0]['net'] = new
        else:
            # Only these two original diodes may be absent from the added-diode inventory.
            assert name in {'ANTENNA_491','ANTENNA_500'}
        moved[name] = dict(master='sg13g2_antennanp',signal_terms=new_terms)
    assert len(result) == len(cumulative)
    return result, moved

def verify_moved_export(netlist, moved):
    assert set(moved)==set(EXPECTED)
    for name, (_, new) in EXPECTED.items():
        assert moved[name]==dict(master='sg13g2_antennanp',signal_terms=[dict(pin='A',type='SIGNAL',net=new)])
    checked=check_added_antennas(netlist,moved)
    assert checked['new_diodes_exported']==10
    assert not checked['missing_diodes'] and not checked['duplicate_diodes'] and not checked['signal_connection_mismatches']
    return checked
