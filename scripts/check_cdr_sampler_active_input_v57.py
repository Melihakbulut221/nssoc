#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require exact v32 sampler plus v56 gain with one shared reference."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD='XIP dp lp sub rppd w=4u l=1.2u b=0 sw_et=1\nXIN dn ln sub rppd w=4u l=1.2u b=0 sw_et=1\nXBP avdd lp sub rppd w=4u l=.9u b=0 sw_et=1\nXBN avdd ln sub rppd w=4u l=.9u b=0 sw_et=1'
GAIN='* Active input replaces all four passive divider resistors.\n* Gain gates share the one existing8um XREF; no duplicate bias source.\nXGP ln dp gain_tail sub npn13G2 Nx=4\nXGN lp dn gain_tail sub npn13G2 Nx=4\nXGT0 gain_tail iref avss sub sg13_lv_nmos w=53.335u l=.3u ng=1\nXGT1 gain_tail iref avss sub sg13_lv_nmos w=53.335u l=.3u ng=1\nXUP avdd lp sub rppd w=8u l=1.8u b=0 sw_et=1\nXUN avdd ln sub rppd w=8u l=1.8u b=0 sw_et=1\nXDP lp avss sub rppd w=4u l=7.4u b=0 sw_et=1\nXDN ln avss sub rppd w=4u l=7.4u b=0 sw_et=1'
PREFIX='* Native shared-bias active-input sampler candidate; not physical or fullPHY acceptance.\n* Original v32 master/slave and single8um reference retained; exact v56 gain without its reference.\n* SPDX-License-Identifier: CERN-OHL-W-2.0\n'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def expected():
 base=ROOT/'hw/soc/analog/pcie/rx_sampler_settling_v32.spice'
 gain=ROOT/'hw/soc/analog/pcie/cdr_active_levelshift_v56.spice'
 assert digest(base)=='c9c78b752e4ec5d17169b3254afa603b3d0b7702f164f8414356d54aa25b6db4' and digest(gain)=='7ef165410c840fcbc51813fc0fcd3944a34f4f42259a857f56e38f3408b2f1c8'
 text=base.read_text();assert text.count(OLD)==1
 # Verify every inserted primitive is the existing gain topology/parameter set.
 rows=[s.lower().split()for s in gain.read_text().splitlines()if s.strip()and not s.lstrip().startswith('*')]
 original={r[0]:r[1:]for r in rows[1:-1]}
 renames={'xp':'xgp','xn':'xgn','xt0':'xgt0','xt1':'xgt1','xup':'xup','xun':'xun','xdp':'xdp','xdn':'xdn'}
 nodes={'ip':'dp','inn':'dn','op':'lp','on':'ln','tail':'gain_tail'}
 inserted={r[0]:r[1:]for line in GAIN.lower().splitlines()if(line and not line.startswith('*'))for r in [line.split()]}
 assert inserted=={renames[name]:[nodes.get(v,v)for v in values]for name,values in original.items()if name!='xref'}
 assert original['xref']==['iref','iref','avss','sub','sg13_lv_nmos','w=8u','l=.3u','ng=1']
 return PREFIX+text[text.index('.subckt '):].replace('nssoc_rx_sampler_settling_v32','nssoc_rx_sampler_active_input_v57').replace(OLD,GAIN)
def verify(text):assert text==expected(),'Shared-reference input replacement or unchanged latch source differs'
def check():
 p=ROOT/'hw/soc/analog/pcie/rx_sampler_active_input_v57.spice';verify(p.read_text())
 controls=[]
 for label,bad in [('duplicate_reference',p.read_text().replace('XREF iref','XREF_EXTRA iref iref avss sub sg13_lv_nmos w=8u l=.3u ng=1\nXREF iref',1)),
                   ('old_divider_retained',p.read_text().replace(GAIN,GAIN+'\n'+OLD)),
                   ('gain_gate_disconnected',p.read_text().replace('gain_tail iref avss','gain_tail new_ref avss',1)),
                   ('latch_tail_changed',p.read_text().replace('w=36u','w=37u',1))]:
  try:verify(bad)
  except AssertionError:controls.append(label)
  else:raise AssertionError('Accepted '+label)
 assert len(controls)==4
 return dict(status='PASS_EXACT_SHARED_REFERENCE_CIRCUIT_AND_FOUR_CORRUPTIONS',rejected=controls,one_existing_reference=True,original_latch_stages_unchanged=True,physical_accepted=False)
if __name__=='__main__':print(json.dumps(check()))
