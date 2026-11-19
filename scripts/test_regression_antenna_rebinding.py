"""Cloud checks: reject missing, stale, duplicate and unapproved diode connections."""
import copy,json
from rebind_regression_antenna_inventory import EXPECTED,rebind_inventory,verify_moved_export

def reject(call):
    try: call()
    except (AssertionError,ValueError): return True
    raise AssertionError('Invalid evidence was accepted')

moves={name:dict(master='sg13g2_antennanp',old_net=old,new_net=new) for name,(old,new) in EXPECTED.items()}
audit=dict(moves=moves,all_original_diodes_preserved=True,functional_equivalence_by_identity_buffer_collapse=True,antenna_protection_revalidation_required=True,accepted=False)
inventory={name:dict(master='sg13g2_antennanp',signal_terms=[dict(pin='A',type='SIGNAL',net=old)],terms=[dict(pin='A',type='SIGNAL',net=old),dict(pin='VDD',type='POWER',net='VPWR')]) for name,(old,new) in EXPECTED.items() if name not in {'ANTENNA_491','ANTENNA_500'}}
original=copy.deepcopy(inventory)
updated,moved=rebind_inventory(inventory,audit)
assert inventory==original and len(updated)==8 and len(moved)==10
assert all(c['terms'][1]['net']=='VPWR' for c in updated.values())
netlist='\n'.join('sg13g2_antennanp '+name+' (.A('+new+'));' for name,(_,new) in EXPECTED.items())
verify_moved_export(netlist,moved)
controls={}
for name in EXPECTED:
    bad=copy.deepcopy(audit);del bad['moves'][name]
    controls['missing_move_'+name]=reject(lambda:rebind_inventory(inventory,bad))
    old,new=EXPECTED[name]
    controls['stale_export_'+name]=reject(lambda:verify_moved_export(netlist.replace('.A('+new+')', '.A('+old+')',1),moved))
    controls['missing_export_'+name]=reject(lambda:verify_moved_export('\n'.join(l for l in netlist.splitlines() if (' '+name+' ') not in l),moved))
    controls['duplicate_export_'+name]=reject(lambda:verify_moved_export(netlist+'\nsg13g2_antennanp '+name+' (.A('+new+'));',moved))
bad=copy.deepcopy(audit);bad['moves']['ANTENNA_9999']=dict(master='sg13g2_antennanp',old_net='a',new_net='b')
controls['unexpected_move']=reject(lambda:rebind_inventory(inventory,bad))
bad=copy.deepcopy(inventory);del bad['ANTENNA_2569']
controls['missing_added_diode']=reject(lambda:rebind_inventory(bad,audit))
controls['double_rebind']=reject(lambda:rebind_inventory(updated,audit))
assert all(controls.values())
print(json.dumps(dict(status='PASS',negative_controls=len(controls),input_unchanged=True,scope='Parser and inventory logic only; no new physical or timing result'),indent=2))
