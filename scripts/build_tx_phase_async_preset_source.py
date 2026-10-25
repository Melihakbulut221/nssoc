#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Real-device async-preset/first-fall source candidate; no layout or electrical acceptance."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LATCH='hw/soc/analog/pcie/rx_sampler_hbt_v2.spice'
TAIL='hw/soc/analog/pcie/clock_div4_hbt_v10.spice'
FRONT='hw/soc/analog/pcie/clock_div2_high_input_v1.spice'
OUTPUT='hw/soc/analog/pcie/clock_div2_async_preset_firstfall_v2.spice'
NAMES=dict(seed='nssoc_phase_seed_reference_v2',selp='nssoc_phase_preset_selector_p_v2',seln='nssoc_phase_preset_selector_n_v2',
 latchp='nssoc_phase_async_latch_p_v2',latchn='nssoc_phase_async_latch_n_v2',level='nssoc_phase_native_level_v2',
 release='nssoc_phase_first_fall_release_v2',parentp='nssoc_phase_async_preset_parent_p_v2',parentn='nssoc_phase_async_preset_parent_n_v2')
def definitions(text):
    result={};name=None
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('*'):continue
        row=line.split()
        if row[0].lower()=='.subckt':
            assert name is None and row[1]not in result
            name=row[1];result[name]=dict(ports=row[2:],cards=[])
        elif row[0].lower()=='.ends':assert name==row[1];name=None
        else:
            assert name and row[0].startswith('X'),'Only actual compact devices or declared subcircuits'
            result[name]['cards'].append(row)
    assert name is None
    return result
def reference():
    return (definitions((ROOT/LATCH).read_text())['nssoc_cml_latch'],
      definitions((ROOT/TAIL).read_text())['nssoc_clock_div2_tail_v10'],
      definitions((ROOT/FRONT).read_text())['nssoc_clock_div2_high_input_v1'])
def seed_cards():
    # Unqualified real resistor seed geometry. No ideal DC voltages.
    return [f'{name} {a} {b} sub rppd w=4u l={length}u b=0 sw_et=1'.split()
      for name,a,b,length in [('XHP','avdd','p',4),('XLP','p','avss',40),('XHN','avdd','n',4),('XLN','n','avss',20)]]
def build():
    latch,tail,front=reference();tail_cards={r[0]:r for r in tail['cards']};definitions_out=[]
    def emit(key,ports,cards):
        definitions_out.append('.subckt '+NAMES[key]+' '+ports+'\n'+'\n'.join(' '.join(r)for r in cards)+'\n.ends '+NAMES[key]+'\n')
    emit('seed','p n avdd avss sub',seed_cards())
    for sign in ('p','n'):
        pos,neg=('seedp','seedn')if sign=='p'else('seedn','seedp')
        cards=[tail_cards['XBIAS'],tail_cards['XREF'],
          'XAP outn dp ea sub npn13G2 Nx=2'.split(),'XAN outp dn ea sub npn13G2 Nx=2'.split(),
          f'XBP outn {pos} eb sub npn13G2 Nx=2'.split(),f'XBN outp {neg} eb sub npn13G2 Nx=2'.split(),
          'XSA ea runp tail sub npn13G2 Nx=4'.split(),'XSB eb runn tail sub npn13G2 Nx=4'.split(),
          'XT tail ref avss sub npn13G2 Nx=4'.split(),
          'XRP avdd outp sub rppd w=8u l=2.12u b=0 sw_et=1'.split(),
          'XRN avdd outn sub rppd w=8u l=2.12u b=0 sw_et=1'.split(),
          'XBA ea avss sub rppd w=1u l=38.4u b=0 sw_et=1'.split(),
          'XBB eb avss sub rppd w=1u l=38.4u b=0 sw_et=1'.split(),
          ['XSEED','seedp','seedn','avdd','avss','sub',NAMES['seed']]]
        emit('sel'+sign,'dp dn runp runn outp outn avdd avss sub',cards)
    for sign in ('p','n'):
        cards=[]
        for original in latch['cards']:
            row=list(original)
            if row[0]in ('XDP','XDN','XLP','XLN'):row[2]={'XDP':'data_p','XDN':'data_n','XLP':'hold_p','XLN':'hold_n'}[row[0]]
            cards.append(row)
        cards.extend([['XDATA','dp','dn','runp','runn','data_p','data_n','avdd','avss','sub',NAMES['sel'+sign]],
          ['XHOLD','qp','qn','runp','runn','hold_p','hold_n','avdd','avss','sub',NAMES['sel'+sign]]])
        emit('latch'+sign,'dp dn qp qn cp cn runp runn avdd avss sub ref',cards)
    remap={'clkp':'ip','clkn':'in','ckp':'cp','ckn':'cn'}
    level=[[remap.get(t,t)for t in r]for r in front['cards']if r[0]!='XSECOND']
    emit('level','ip in cp cn avdd avss sub',level)
    release=[['XARM','armp','armn','armcp','armcn','avdd','avss','sub',NAMES['level']],
      tail_cards['XBIAS'],tail_cards['XREF'],
      ['XSEED','capturep','capturen','avdd','avss','sub',NAMES['seed']],
      ['XM','capturep','capturen','amp','amn','clkp','clkn','armcp','armcn','avdd','avss','sub','ref',NAMES['latchn']],
      ['XS','amp','amn','releasep','releasen','clkn','clkp','armcp','armcn','avdd','avss','sub','ref',NAMES['latchn']]]
    emit('release','clkp clkn armp armn releasep releasen avdd avss sub',release)
    for sign in ('p','n'):
        supply={'avdd':'DIV_AVDD','avss':'AVSS','sub':'SUB','mp':'MP','mn':'MN'}
        cards=[['XCLK','CLKP','CLKN','ckp','ckn','DIV_AVDD','AVSS','SUB',NAMES['level']],
          ['XRELEASE','ckp','ckn','ARM_P','ARM_N','releasedp','releasedn','DIV_AVDD','AVSS','SUB',NAMES['release']],
          ['XRUN','releasedp','releasedn','runp','runn','DIV_AVDD','AVSS','SUB',NAMES['level']],
          *[[supply.get(t,t)for t in tail_cards[n]]for n in ('XBIAS','XREF')],
          ['XM','QN','QP','MP','MN','ckn','ckp','runp','runn','DIV_AVDD','AVSS','SUB','ref',NAMES['latch'+sign]],
          ['XS','MP','MN','QP','QN','ckp','ckn','runp','runn','DIV_AVDD','AVSS','SUB','ref',NAMES['latchp']],
          *[[supply.get(t,t)for t in tail_cards[n]]for n in ('XSEEDP','XSEEDN')]]
        emit('parent'+sign,'CLKP CLKN MP MN QP QN ARM_P ARM_N DIV_AVDD AVSS SUB',cards)
    return ('* SPDX-License-Identifier: CERN-OHL-W-2.0\n'
      '* SOURCE CANDIDATE ONLY. No accepted reset, electrical result or layout.\n'
      '* Native devices only; no internal voltage/current/behavioral sources or IC/UIC.\n'
      '* ARM_P/ARM_N are an external differential interface requiring a real driver.\n'
      '* P/N parent suffix selects the required independent master preset polarity.\n'
      '* Added selectors change data/hold delay and loading; all native checks are open.\n\n'+'\n'.join(definitions_out))
if __name__=='__main__':
    print(build(),end='')
