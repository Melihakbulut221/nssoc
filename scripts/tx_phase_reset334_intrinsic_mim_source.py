#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reversible native334/1010-terminal and eight-MIM algorithms; no native call on import."""
import ast,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PORTS=['CLKP','CLKN','MP','MN','QP','QN','ARM_P','ARM_N','DIV_AVDD','AVSS','SUB']
GDS={'p':'601e5611ae555d4a39891a095bce443851665853439d379377d9a1f6cb60c834',
     'n':'c30c73110c4e8f0507b2a10058a2dbfe9a7e2abb22dcb1af7cad1213e4df167b'}
ORIGINAL={
 'native':('scripts/pll_divider_load3p2_native.py','01233ad006ebc53e98499becc37a291f88fb448e73c77293c2403b63a5784d46'),
 'intrinsic':('scripts/pll_divider_load3p2_intrinsic.py','e6ee69991a85cf8dd19f8a92773d8875baf60c69ab37b9959dd0c7e9ab9a0305'),
 'mim':('scripts/tx_phase55_mim_native.py','e033ef082734f10e5617d4c9b42b048ed59441582c810aa9aae24011d3f76e6b')}
MIM_STATUS='PASS_ACTUAL_EIGHT_MIM_DRAWINGS_AND_ALL695_NATIVE_PLANES_WITH_SIX_FAULTS_REQUIRES_RC'
def digest(t):return hashlib.sha256(t.encode()).hexdigest()
def derive(text,edits):
    original=text
    for before,after,count in edits:
        assert text.count(before)==count,(before,text.count(before))
        text=text.replace(before,after)
    back=text
    for before,after,count in reversed(edits):
        assert back.count(after)==count,(after,back.count(after));back=back.replace(after,before)
    assert back==original
    ast.parse(text)
    return text
def top(pol):
    assert pol in ('p','n')
    return 'nssoc_tx_phase_reset244_'+pol+'_v1'
def edits(kind,pol):
    t=top(pol);g=GDS[pol];module='tx_phase_reset334_'+pol+'_native_generated'
    if kind=='native':
        return [
         ("PORTS=['CLKP','CLKN','QP','QN','DIV_AVDD','AVSS','SUB']",'PORTS='+repr(PORTS),1),
         ('nssoc_clock_div4_load3p2_v1_layout',t,1),
         ('ee95597fc6307f2476d49d9ac5560ed6b06d4dcda956f7716e0d7ea5611731f6',g,1),
         ("root=source/'source/wire';gds=root/'source/layout'/(TOP+'.gds');database=root/'raw_flat/result.lvsdb'","root=source;gds=root/'layout'/(TOP+'.gds');database=root/'flat_lvs/result.lvsdb'",1),
         ("source/'anchors03.json'","source/'anchors.json'",1),
         ("root/'source/layout/result.json'","root/'layout/result.json'",1),
         ('c.pin_count()==7','c.pin_count()==11',1),
         ('==91','==334',1),
         ('Counter(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)','Counter(npn13G2=106,rppd=130,cap_cmim=8,ptap1=90)',1),
         ('len(names)==38 and len(set(names.values()))==38','len(names)==120 and len(set(names.values()))==120',1),
         ('==283','==1010',2),
         ('EXPORTED_NATIVE_DIVIDER91_AND283_TERMINALS_NOT_ELECTRICAL_ACCEPTANCE','EXPORTED_NATIVE_RESET334_AND1010_TERMINALS_NOT_ELECTRICAL_ACCEPTANCE',1)]
    if kind=='intrinsic':
        return [
         ('from pll_divider_load3p2_native import ORDER,PORTS','from '+module+' import ORDER,PORTS',1),
         ('Native divider intrinsic 91 devices','Native reset intrinsic 334 devices',1),
         ('91-device','334-device',1),('==91','==334',1),
         ('dict(devices=91,hbt=34,resistors=33,mim=6,finite_contacts=18,ports=PORTS)','dict(devices=334,hbt=106,resistors=130,mim=8,finite_contacts=90,ports=PORTS)',1)]
    assert kind=='mim'
    return [
      ('Bind actual phase55 MIM drawings','Bind actual reset334 MIM drawings',1),
      ("TOP='nssoc_tx_phase_divider55_v1'","TOP="+repr(t),1),
      ("gds=source/'source/layout'/(TOP+'.gds');dbpath=source/'source/flat_lvs/result.lvsdb'","gds=source/'layout'/(TOP+'.gds');dbpath=source/'flat_lvs/result.lvsdb'",1),
      ('c.pin_count()==9','c.pin_count()==11',1),
      ("len(rows)==168 and len(labels)==126 and a['counts']['wire_components']==24","len(rows)==1010 and len(labels)==695 and a['counts']['wire_components']==119",1),
      ('len(caps)==4','len(caps)==8',1),('len(leaves)==4','len(leaves)==8',1),
      ('actual four placed leaf drawings','actual eight placed leaf drawings',1),
      ('len(matched)==len(set(matched))==4','len(matched)==len(set(matched))==8',1),
      ("for x in a['anchors']})==126","for x in a['anchors']})==695",1),
      ("WT.name=='phase_divider55_wires'","WT.name=='phase_reset334_wires'",1),
      ('PASS_ACTUAL_FOUR_MIM_DRAWINGS_AND_ALL126_NATIVE_PLANES_WITH_SIX_FAULTS_REQUIRES_RC',MIM_STATUS,1),
      ('actual_mim_devices=4,physical_points=126,wire_components=24','actual_mim_devices=8,physical_points=695,wire_components=119',1),
      ('all126_native_and_physical_owners_verified','all695_native_and_physical_owners_verified',1)]
def sources(kind,pol,original=None):
    path,expected=ORIGINAL[kind]
    text=(ROOT/path).read_text()if original is None else original
    assert digest(text)==expected,('Frozen algorithm changed',path)
    changes=edits(kind,pol);result=derive(text,changes)
    return result,dict(original_path=path,original_sha256=expected,generated_sha256=digest(result),reversible_edits=changes)
def controls():
    results=[];faults=[]
    for pol in ('p','n'):
        for kind in ORIGINAL:
            code,proof=sources(kind,pol);results.append(dict(kind=kind,polarity=pol,**proof))
            try:sources(kind,pol,(ROOT/ORIGINAL[kind][0]).read_text()+'\n')
            except AssertionError:faults.append(pol+'-'+kind+'-changed-source')
            else:raise AssertionError('Changed original source accepted')
    for name,fn in [('ambiguous-edit',lambda:derive('x x',[('x','y',1)])),
                    ('missing-edit',lambda:derive('x',[('missing','y',1)])),
                    ('wrong-polarity',lambda:top('q'))]:
        try:fn()
        except AssertionError:faults.append(name)
        else:raise AssertionError('Accepted source corruption '+name)
    assert len(faults)==9
    return dict(derivations=results,rejected=faults,native_execution=False,RC_accepted=False,electrical_accepted=False)
