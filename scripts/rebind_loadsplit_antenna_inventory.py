"""Rebind only the 44 explicit load-split diode moves; preserve immutable input evidence."""
from copy import deepcopy
from check_antenna_netlist_export import check_added_antennas

EXPECTED = {'ANTENNA_1371': ('nssoc_sta_n_62713', 'nssoc_loadsplit_5_net'), 'ANTENNA_1372': ('nssoc_sta_n_62713', 'nssoc_loadsplit_6_net'), 'ANTENNA_1373': ('nssoc_sta_n_62713', 'nssoc_loadsplit_5_net'), 'ANTENNA_1374': ('nssoc_sta_n_62713', 'nssoc_loadsplit_6_net'), 'ANTENNA_1375': ('nssoc_sta_n_62713', 'nssoc_loadsplit_5_net'), 'ANTENNA_1376': ('nssoc_sta_n_62713', 'nssoc_loadsplit_6_net'), 'ANTENNA_1377': ('nssoc_sta_n_62713', 'nssoc_loadsplit_5_net'), 'ANTENNA_1378': ('nssoc_sta_n_62713', 'nssoc_loadsplit_6_net'), 'ANTENNA_1379': ('nssoc_sta_n_62713', 'nssoc_loadsplit_4_net'), 'ANTENNA_1380': ('nssoc_sta_n_62713', 'nssoc_loadsplit_6_net'), 'ANTENNA_1381': ('nssoc_sta_n_62713', 'nssoc_loadsplit_5_net'), 'ANTENNA_1382': ('nssoc_sta_n_62713', 'nssoc_loadsplit_4_net'), 'ANTENNA_1383': ('nssoc_sta_n_62713', 'nssoc_loadsplit_4_net'), 'ANTENNA_1384': ('nssoc_sta_n_62713', 'nssoc_loadsplit_6_net'), 'ANTENNA_1385': ('nssoc_sta_n_62713', 'nssoc_loadsplit_5_net'), 'ANTENNA_1386': ('nssoc_sta_n_62713', 'nssoc_loadsplit_4_net'), 'ANTENNA_1614': ('nssoc_sta_n_100391', 'nssoc_loadsplit_0_net'), 'ANTENNA_1615': ('nssoc_sta_n_100391', 'nssoc_loadsplit_1_net'), 'ANTENNA_1616': ('nssoc_sta_n_100391', 'nssoc_loadsplit_0_net'), 'ANTENNA_1617': ('nssoc_sta_n_100391', 'nssoc_loadsplit_1_net'), 'ANTENNA_1830': ('net5013', 'nssoc_loadsplit_17_net'), 'ANTENNA_1831': ('net5013', 'nssoc_loadsplit_17_net'), 'ANTENNA_1832': ('net5013', 'nssoc_loadsplit_17_net'), 'ANTENNA_1833': ('net5013', 'nssoc_loadsplit_18_net'), 'ANTENNA_1834': ('net5013', 'nssoc_loadsplit_18_net'), 'ANTENNA_1835': ('net5013', 'nssoc_loadsplit_19_net'), 'ANTENNA_1836': ('net5013', 'nssoc_loadsplit_17_net'), 'ANTENNA_1837': ('net5013', 'nssoc_loadsplit_17_net'), 'ANTENNA_1838': ('net5013', 'nssoc_loadsplit_17_net'), 'ANTENNA_1839': ('net5013', 'nssoc_loadsplit_18_net'), 'ANTENNA_1840': ('net5013', 'nssoc_loadsplit_18_net'), 'ANTENNA_1841': ('net5013', 'nssoc_loadsplit_19_net'), 'ANTENNA_2427': ('net4366', 'nssoc_loadsplit_15_net'), 'ANTENNA_2428': ('net4366', 'nssoc_loadsplit_14_net'), 'ANTENNA_2429': ('net4366', 'nssoc_loadsplit_15_net'), 'ANTENNA_2430': ('net4366', 'nssoc_loadsplit_15_net'), 'ANTENNA_2431': ('net4366', 'nssoc_loadsplit_16_net'), 'ANTENNA_2432': ('net4366', 'nssoc_loadsplit_14_net'), 'ANTENNA_2433': ('net4366', 'nssoc_loadsplit_15_net'), 'ANTENNA_2434': ('net4366', 'nssoc_loadsplit_15_net'), 'ANTENNA_2435': ('net4366', 'nssoc_loadsplit_16_net'), 'ANTENNA_2436': ('net4366', 'nssoc_loadsplit_13_net'), 'ANTENNA_2437': ('net4366', 'nssoc_loadsplit_14_net'), 'ANTENNA_2438': ('net4366', 'nssoc_loadsplit_14_net')}

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
            raise AssertionError('Moved diode missing from cumulative inventory: '+name)
        moved[name] = dict(master='sg13g2_antennanp',signal_terms=new_terms)
    assert len(result) == len(cumulative)
    return result, moved

def verify_moved_export(netlist, moved):
    assert set(moved)==set(EXPECTED)
    for name, (_, new) in EXPECTED.items():
        assert moved[name]==dict(master='sg13g2_antennanp',signal_terms=[dict(pin='A',type='SIGNAL',net=new)])
    checked=check_added_antennas(netlist,moved)
    assert checked['new_diodes_exported']==44
    assert not checked['missing_diodes'] and not checked['duplicate_diodes'] and not checked['signal_connection_mismatches']
    return checked
