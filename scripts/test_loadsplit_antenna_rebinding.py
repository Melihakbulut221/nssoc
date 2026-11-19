"""Synthetic fail-closed checks; physical admission remains separate."""
import copy,json
from rebind_loadsplit_antenna_inventory import EXPECTED,rebind_inventory,verify_moved_export

def reject(call):
    try: call()
    except (AssertionError,ValueError): return True
    raise AssertionError('Invalid evidence was accepted')

moves={name:dict(master='sg13g2_antennanp',old_net=old,new_net=new) for name,(old,new) in EXPECTED.items()}
audit=dict(moves=moves,all_original_diodes_preserved=True,functional_equivalence_by_identity_buffer_collapse=True,antenna_protection_revalidation_required=True,accepted=False)
inventory={name:dict(master='sg13g2_antennanp',signal_terms=[dict(pin='A',type='SIGNAL',net=old)],terms=[dict(pin='A',type='SIGNAL',net=old),dict(pin='VDD',type='POWER',net='VPWR'),dict(pin='VSS',type='GROUND',net='VGND')]) for name,(old,new) in EXPECTED.items()}
inventory['UNCHANGED_DIODE']=dict(master='sg13g2_antennanp',signal_terms=[dict(pin='A',type='SIGNAL',net='untouched')])
original=copy.deepcopy(inventory);original_audit=copy.deepcopy(audit)
updated,moved=rebind_inventory(inventory,audit)
assert inventory==original and audit==original_audit
assert len(updated)==45 and len(moved)==44
assert updated['UNCHANGED_DIODE']==original['UNCHANGED_DIODE']
for name in EXPECTED:
    assert updated[name]['terms'][1:]==original[name]['terms'][1:]
    assert updated[name]['terms'][0]==updated[name]['signal_terms'][0]
lines={name:'sg13g2_antennanp '+name+' (.A('+new+'));' for name,(_,new) in EXPECTED.items()}
netlist='\n'.join(lines.values())
verify_moved_export(netlist,moved)
controls={}
for name,(old,new) in EXPECTED.items():
    bad=copy.deepcopy(audit);del bad['moves'][name]
    controls['missing_move_'+name]=reject(lambda:rebind_inventory(inventory,bad))
    bad=copy.deepcopy(audit);bad['moves'][name]['new_net']='unapproved_net'
    controls['wrong_destination_'+name]=reject(lambda:rebind_inventory(inventory,bad))
    bad=copy.deepcopy(audit);bad['moves'][name]['old_net']='unapproved_source'
    controls['wrong_origin_'+name]=reject(lambda:rebind_inventory(inventory,bad))
    bad=copy.deepcopy(inventory);del bad[name]
    controls['missing_inventory_'+name]=reject(lambda:rebind_inventory(bad,audit))
    bad=copy.deepcopy(inventory);bad[name]['signal_terms'][0]['net']='wrong_source'
    controls['stale_inventory_'+name]=reject(lambda:rebind_inventory(bad,audit))
    bad=copy.deepcopy(inventory);bad[name]['terms'][0]['net']='inconsistent'
    controls['inconsistent_terms_'+name]=reject(lambda:rebind_inventory(bad,audit))
    controls['stale_export_'+name]=reject(lambda:verify_moved_export(netlist.replace(lines[name],lines[name].replace('.A('+new+')','.A('+old+')')),moved))
    controls['missing_export_'+name]=reject(lambda:verify_moved_export('\n'.join(line for cell,line in lines.items() if cell!=name),moved))
    controls['duplicate_export_'+name]=reject(lambda:verify_moved_export(netlist+'\n'+lines[name],moved))
    bad=copy.deepcopy(moved);bad[name]['signal_terms'][0]['net']='wrong_destination'
    controls['wrong_export_inventory_'+name]=reject(lambda:verify_moved_export(netlist,bad))
for flag in ['all_original_diodes_preserved','functional_equivalence_by_identity_buffer_collapse','antenna_protection_revalidation_required']:
    bad=copy.deepcopy(audit);bad[flag]=False
    controls[flag]=reject(lambda:rebind_inventory(inventory,bad))
bad=copy.deepcopy(audit);bad['accepted']=True
controls['premature_acceptance']=reject(lambda:rebind_inventory(inventory,bad))
bad=copy.deepcopy(audit);bad['moves']['ANTENNA_9999']=dict(master='sg13g2_antennanp',old_net='a',new_net='b')
controls['unexpected_move']=reject(lambda:rebind_inventory(inventory,bad))
controls['double_rebind']=reject(lambda:rebind_inventory(updated,audit))
assert inventory==original and audit==original_audit and all(controls.values())
print(json.dumps(dict(status='PASS',negative_controls=len(controls),input_unchanged=True,scope='Synthetic inventory and export checks only; no physical or timing signoff'),indent=2))
