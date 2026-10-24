# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,re,sys
B=Path(__file__).resolve().parent;T=B.parent/'pcie-tail115-connected570-tuning-20261006';R=Path.cwd();sys.path.insert(0,str(T));sys.path.insert(0,str(B))
import characterize_clamped570_02 as m
import save_batches03 as batch

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert not(B/'source-freeze01.json').exists()and not(B/'native-control01').exists()
old=json.loads((T/'source-freeze02.json').read_text());paths=set(map(Path,old['pins']))
for p,v in old['pins'].items():assert pin(p)==v
paths.update([T/'source-freeze02.json',T/'source-only-peer-root02.json',T/'resource-peer-pll02.json',T/'native02-failure-diagnosis01.json',T/'campaign02.json',T/'detached-launch02.json',T/'controller02.log'])
paths.update(p for p in (T/'native02').rglob('*')if p.is_file())
up=B/'upstream-source01/tmpsndfibtf';defs=(up/'src/include/ngspice/cpdefs.h').read_text();commands=(up/'src/frontend/commands.c').read_text();control=(up/'src/frontend/control.c').read_text();save=(up/'src/frontend/breakp2.c').read_text()
assert re.search(r'#define LOTS\s+1000\b',defs)
assert re.search(r'\{ "save", com_save, TRUE, FALSE,\s*\{[^}]+\}, E_DEFHMASK, 0, LOTS,',commands)
assert 'nargs > command->co_maxargs'in control and '%s: too many args.'in control
assert 'settrace(wl, VF_ACCUM, NULL);'in save and 'last->db_next = d;'in save
c,rows,texts=m.config(.5);expected=m.n.vectors(rows,c['extra_vectors']);lines=batch.commands(expected);assert len(lines)==9 and [len(x.split())-1 for x in lines]==[128]*8+[109]
olddeck=m.deck(c,rows,texts);newdeck=batch.replace_save(olddeck,expected);assert newdeck.replace('\n'.join(lines),'save '+' '.join(expected))==olddeck
(B/'proposed-full34ns-deck03.cir').write_text(newdeck)
report=dict(status='PREDECLARED_EXACT570_BATCHED_SAVE_COMMAND_CONTROL',source_package='47+ds-1~bpo13+1',primary_source_url='https://deb.debian.org/debian/pool/main/n/ngspice/ngspice_47+ds-1~bpo13+1.dsc',upstream_tag_url='https://github.com/imr/ngspice/blob/ngspice-47/src/frontend/commands.c',declared_source_limit=1000,actual_original_arguments=1133,batch_arguments=[128]*8+[109],native_negative=str(T/'native02/v050-01/result.json'),actual_negative='save: too many args. then2679allvariables rejected;65596byteprefix retained',static_body_delta='Only one save1133 command replaced by9append save commands; exact original vector sequence and allphysical deck lines remain unchanged.',control_only_delta='Separate samegraph .5V command/OP experiment, only stop2ps and explicit run/write tiny.raw in place of FIFO. This is not a tuning point, never a34ns result. Fullretry deck remains34ns.',planned_controls=['actual570_OP64OFF_and2ps_samebinary_full1134columns','literal_missing_command_observation_rejected','literal_duplicate_command_observation_rejected','literal_reordered_command_observation_rejected','actual_native_header_missing_row_rejected','actual_native_header_duplicate_name_rejected','actual_native_header_reordered_ID_rejected','original_native1133single_command_failure_readback_only'],resource=dict(CPU=10,AS=2*1024**3,FSIZE=16*1024**2,SSDcap=128*1024**2,SSDfloor=1024**3,shared_entry=1024**3,shared_continuous_terminal=512*1024**2,elapsed_watchdog=None,owner='exact inherited ProcessOwner with registered child group, real41priorcontrols+02native failure closure retained'),no_control_native_started=True)
(B/'control-contract01.json').write_text(json.dumps(report,indent=2)+'\n')
paths.update(p for p in B.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc')
record=dict(status='FROZEN_BOUNDED570_SAVE_BATCH_NATIVE_CONTROLS_REQUIRES_PEER',pins={str(p.absolute()):pin(p)for p in sorted(paths)},contract=pin(B/'control-contract01.json'),sources={name:pin(B/name)for name in ['save_batches03.py','run_controls01.py','freeze_controls01.py']},prior_failure=pin(T/'native02-failure-diagnosis01.json'),prior_combined_peer=pin(T/'source-only-peer-root02.json'),full34ns_physics_changes=False,full34ns_acceptance_changes=False,scope='Source-only before one bounded samebinary570 command/OP/2ps transient control. Full34ns retry is separately gated after actual control results. Old sources/results remain unchanged.')
(B/'source-freeze01.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(freeze=pin(B/'source-freeze01.json'),pins=len(paths),batch_sizes=report['batch_arguments'])))
