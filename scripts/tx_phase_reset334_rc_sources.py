#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pending reset334 RC source derivations; require fresh qualified MIM prerequisite."""
import ast,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CELL='phase_reset334_wires'
PRECISE='1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c'
def derive(text,edits):
    original=text;records=[]
    for before,after in edits:
        assert before and before!=after
        matches=list(re.finditer(re.escape(before),text));assert matches,before
        positions=[m.start()+i*(len(after)-len(before))for i,m in enumerate(matches)]
        text=text.replace(before,after);records.append(dict(before=before,after=after,count=len(matches),positions=positions))
    reverse=text
    for record in reversed(records):
        for start in reversed(record['positions']):
            assert reverse[start:start+len(record['after'])]==record['after']
            reverse=reverse[:start]+record['before']+reverse[start+len(record['after']):]
    assert reverse==original;ast.parse(text)
    return text,dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),generated_sha256=hashlib.sha256(text.encode()).hexdigest(),edits=records,reversible=True)
def names(pol):
    assert pol in ('p','n')
    return 'nssoc_tx_phase_reset334_'+pol+'_intrinsic_v1','nssoc_tx_phase_reset334_'+pol+'_native_wire_v1'
def mim_source():
    return derive((ROOT/'scripts/audit_tx_phase55_mim_intrinsic.py').read_text(),[
      ('four actual phase55','eight actual reset334'),
      ('len(expected)==sum(expected.values())==4','len(expected)==sum(expected.values())==8'),
      ('PASS_FOUR_NATIVE_MIM_SOURCE_REPLACEMENT_BASELINE_EXPORT_IDENTITIES','PASS_EIGHT_NATIVE_MIM_SOURCE_REPLACEMENT_BASELINE_EXPORT_IDENTITIES'),
      ('devices=4,source_records','devices=8,source_records')])
def audit_source():
    return derive((ROOT/'scripts/pll_divider_load3p2_audit_rc02.py').read_text(),[
      ("PRIOR=B.parent/'pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'","PRIOR=B.parent/'raw-parser.py'"),
      ('import networkx as nx','import networkx as nx\nsys.path.insert(0,str(Path.cwd()/"scripts"))\nfrom audit_tx_reset334_mim_generated import validate_mim'),
      ('divider_load3p2_wires',CELL),
      ('==205','==695'),('=205','=695'),('=198','=684'),('=85','=326'),('==283','==1010'),
      ("['38']","['120']"),("['37']","['119']"),('==37','==119'),('range(1,38)','range(1,120)'),
      ("require(not after['devices'] and not before['devices'] and not before['resistors'],'Device insertion into wire-only graph')","require(not before['resistors'],'Unexpected baseline resistor insertion')"),
      ("require(native_r==export_r,'Native/export resistor topology/value differs')","require(native_r==export_r,'Native/export resistor topology/value differs')\n mim_proof=validate_mim(rows,rep,before,after,original,owners,anchors,json.loads((B.parent/'source/native.json').read_text()))"),
      ('original_devices=91,public_ports=7,physical_wire_components=37','native_mim_intrinsic=mim_proof,original_devices=334,public_ports=11,physical_wire_components=119'),
      ('connected_wire_components=37','connected_wire_components=119'),
      ('collapsed_matrix_entries=38**2','collapsed_matrix_entries=120**2')])
def mutations_source():
    return derive((ROOT/'scripts/pll_divider_load3p2_mutations01.py').read_text(),[
      ('divider_load3p2_wires',CELL),("NO_SPREADING_R',84)","NO_SPREADING_R',325)")])
def rc_source(B,reversed_order):
    edits=[
      ("W=B/'native01/wires.gds'","W=B/'wires.gds'"),
      ("RT=B/'magic-cloud/runtime/lib';T=B/'magic-cloud/tech'","RT=B.parent/'precision-runtime/lib';T=B.parent/'ngspice-mim-tech'"),
      ('e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e',PRECISE),
      ('divider_load3p2_wires',CELL)]
    if reversed_order:
        marker="'extract all',"
        command='exec /usr/bin/python3 {'+str(ROOT/'scripts/tx_reverse_native_cap_order.py')+'} {'+str(B/'rc01'/f'{CELL}.ext')+'}'
        edits.append((marker,marker+repr(command)+','))
    return derive((ROOT/'scripts/pll_divider_load3p2_run_rc01.py').read_text(),edits)
def compose_source(pol,nr,nc):
    intrinsic,model=names(pol)
    assert type(nr)is type(nc)is int and min(nr,nc)>0
    # Static census substitutions must precede measured count insertion; otherwise
    # a measured779 R/C count could accidentally be rewritten by an old ==7 edit.
    edits=[
      ('import pll_divider_load3p2_intrinsic as intrinsic','import tx_phase_reset334_'+pol+'_intrinsic_generated as intrinsic'),
      ('nssoc_divider_load3p2_native91_wire_v1',model),
      ('nssoc_divider_load3p2_native91_intrinsic_v1',intrinsic),
      ('divider_load3p2_wires',CELL),
      ('Full native91 divider composition','Full native334 reset composition'),
      ('==91','==334'),('==205','==695'),('==7','==11'),('==283','==1010'),('==37','==119'),('wire_components=37','wire_components=119'),
      ('dict(devices=91,wire_resistors=382,wire_capacitors=649','dict(devices=334,wire_resistors='+str(nr)+',wire_capacitors='+str(nc)),
      ('dict(R=382,C=649)','dict(R='+str(nr)+',C='+str(nc)+')'),
      ('==1031','=='+str(nr+nc)),
      ('Actual raw91 divider devices and382R649C metal/via model','Actual raw334 reset devices and'+str(nr)+'R'+str(nc)+'C metal/via model')]
    return derive((ROOT/'scripts/pll_divider_load3p2_compose_model.py').read_text(),edits)
