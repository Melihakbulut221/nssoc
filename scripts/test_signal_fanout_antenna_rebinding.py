"""Mutation checks for exact fanout inventory and source/export provenance."""
import copy,json
from rebind_signal_fanout_antenna_inventory import EXPECTED,OUTSIDE_CUMULATIVE,record,rebind_inventory,verify_moved_export

def reject(call):
    try:call()
    except (AssertionError,ValueError):return True
    raise AssertionError('Invalid evidence accepted')

audit=dict(moves={n:dict(master='sg13g2_antennanp',old_net=o,new_net=v)for n,(o,v)in EXPECTED.items()},all_original_diodes_preserved=True,functional_equivalence_by_identity_buffer_collapse=True,antenna_protection_revalidation_required=True,accepted=False)
inventory={n:record(o)for n,(o,v)in EXPECTED.items()if n not in OUTSIDE_CUMULATIVE}
for cell in inventory.values():cell['terms']=copy.deepcopy(cell['signal_terms'])+[dict(pin='VDD',type='POWER',net='VPWR')]
inventory['UNCHANGED_DIODE']=record('untouched')
oldlines={n:'sg13g2_antennanp '+n+' (.A('+o+'));'for n,(o,v)in EXPECTED.items()}
newlines={n:'sg13g2_antennanp '+n+' (.A('+v+'));'for n,(o,v)in EXPECTED.items()}
baseline='\n'.join(oldlines.values())+'\nsg13g2_antennanp UNCHANGED_DIODE (.A(untouched));'
netlist='\n'.join(newlines.values())
original=copy.deepcopy(inventory);original_audit=copy.deepcopy(audit)
updated,moved=rebind_inventory(inventory,audit,baseline)
assert len(updated)==699 and len(moved)==720 and inventory==original and audit==original_audit
assert updated['UNCHANGED_DIODE']==inventory['UNCHANGED_DIODE']
for n in set(EXPECTED)&set(inventory):
    assert updated[n]['terms'][1:]==inventory[n]['terms'][1:]
    assert updated[n]['terms'][0]==updated[n]['signal_terms'][0]
verify_moved_export(netlist,moved)
controls=0
for n,(old,new)in EXPECTED.items():
    bad=copy.deepcopy(audit);del bad['moves'][n]
    reject(lambda:rebind_inventory(inventory,bad,baseline));controls+=1
    bad=copy.deepcopy(audit);bad['moves'][n]['new_net']='wrong'
    reject(lambda:rebind_inventory(inventory,bad,baseline));controls+=1
    bad=copy.deepcopy(audit);bad['moves'][n]['old_net']='wrong'
    reject(lambda:rebind_inventory(inventory,bad,baseline));controls+=1
    reject(lambda:rebind_inventory(inventory,audit,baseline.replace(oldlines[n],'')));controls+=1
    reject(lambda:rebind_inventory(inventory,audit,baseline+'\n'+oldlines[n]));controls+=1
    reject(lambda:rebind_inventory(inventory,audit,baseline.replace(oldlines[n],newlines[n])));controls+=1
    reject(lambda:verify_moved_export(netlist.replace(newlines[n],''),moved));controls+=1
    reject(lambda:verify_moved_export(netlist+'\n'+newlines[n],moved));controls+=1
    reject(lambda:verify_moved_export(netlist.replace(newlines[n],oldlines[n]),moved));controls+=1
    bad=copy.deepcopy(inventory)
    if n in bad:del bad[n]
    else:bad[n]=record(old)
    reject(lambda:rebind_inventory(bad,audit,baseline));controls+=1
for flag in ['all_original_diodes_preserved','functional_equivalence_by_identity_buffer_collapse','antenna_protection_revalidation_required','accepted']:
    bad=copy.deepcopy(audit);bad[flag]=not bad[flag]
    reject(lambda:rebind_inventory(inventory,bad,baseline));controls+=1
reject(lambda:rebind_inventory(updated,audit,baseline));controls+=1
assert inventory==original and audit==original_audit
print(json.dumps(dict(status='PASS',negative_controls=controls,moved_diodes=720,within_cumulative=698,outside_cumulative=22,physical_signoff=False)))
