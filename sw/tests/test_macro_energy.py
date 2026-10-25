# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Current power inventories must include ECC and both Ethernet SRAM ports."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT/'hw/soc/flow'
RAM = 'RM_IHPSG13_1P_512x16_c2_bm_bist'
ETH = 'RM_IHPSG13_2P_256x16_c2_bm_bist'


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(FLOW))
    import macro_activity
    import macro_energy
    return macro_activity, macro_energy


def library(master):
    ports = ['A','B'] if '_2P_' in master else ['A']
    text = ('library(example) { capacitive_load_unit(1,pf); voltage_unit:"1V"; '
            'leakage_power_unit:"1nW"; cell('+master+') { cell_leakage_power:100;\n')
    for port in ports:
        text += 'pin('+port+'_CLK) {\n'
        for i in range(8):
            state = f'{i:03b}'
            terms = '&'.join(('!' if v=='0' else '')+port+'_'+n for n,v in zip(['MEN','WEN','REN'],state))
            value = 1+i+(10 if port=='B' else 0)
            text += ('internal_power() { when:"'+terms+'"; '
                     'rise_power("scalar") { values('+str(value)+'); } '
                     'fall_power("scalar") { values(0); } }\n')
        text += '}\n'
    return text+'}}\n'


@pytest.fixture
def fixture(tmp_path, modules):
    activity, energy = modules
    netlist = tmp_path/'soc.v'
    netlist.write_text('module soc_top(input clk);\n'+RAM+' \\u_ram.g_ecc.u_c0 ();\n'+ETH+' \\u_eth.packet.bank0 ();\nendmodule\n')
    pdk = tmp_path/'pdk'
    libdir = pdk/'libs.ref/sg13g2_sram/lib'; libdir.mkdir(parents=True)
    for master in (RAM,ETH):
        (libdir/(master+'_typ_1p20V_25C.lib')).write_text(library(master))
    macros = {'u_ram.g_ecc.u_c0':RAM,'u_eth.packet.bank0':ETH}
    pins = {}; text='$timescale 1 ns $end\n$scope module tb $end\n$scope module dut $end\n'
    for name,master in macros.items():
        text += '$scope module '+name+' $end\n'
        for port in activity.ports(master):
            for suffix in ('CLK','MEN','WEN','REN','BIST_EN'):
                key=name,port,suffix; pins[key]='v'+str(len(pins))
                text += '$var wire 1 '+pins[key]+' '+port+'_'+suffix+' $end\n'
        text += '$upscope $end\n'
    text += '$upscope $end\n$upscope $end\n$enddefinitions $end\n#0\n'
    for (name,port,suffix),ident in pins.items():
        text += ('1' if suffix=='REN' else '0')+ident+'\n'
    text += '#4\n1'+pins['u_ram.g_ecc.u_c0','A','MEN']+'\n'
    for t,name,port in [(5,'u_ram.g_ecc.u_c0','A'),(7,'u_eth.packet.bank0','A'),
                        (9,'u_eth.packet.bank0','B'),(15,'u_ram.g_ecc.u_c0','A')]:
        ident=pins[name,port,'CLK'];text+=f'#{t}\n1{ident}\n#{t+1}\n0{ident}\n'
    text += '#20\n'
    vcd=tmp_path/'soc.vcd';vcd.write_text(text)
    return activity, energy, netlist, vcd, pdk, pins


def test_counts_actual_edges_per_macro_port_and_prices_leakage_once(fixture):
    activity,energy,netlist,vcd,pdk,_=fixture
    measured=activity.collect(vcd,netlist,'tb.dut',1,20)
    ram=measured['macros']['u_ram.g_ecc.u_c0']['ports']['A']
    assert ram['rising_edges']==2 and ram['state_edges']['101']==2
    eth=measured['macros']['u_eth.packet.bank0']['ports']
    assert eth['A']['state_edges']['001']==1 and eth['B']['state_edges']['001']==1
    result=energy.estimate(measured,netlist,pdk,'nom_typ_1p20V_25C')
    assert result['clock_energy_pj']==2*6+2+12
    # Two cells, three ports: leakage is charged twice, never three times.
    assert result['leakage_energy_pj']==pytest.approx(2*100e-9*19*1000)
    assert result['modelled_power_mw']==pytest.approx((26+0.0038)/19)
    assert len(result['macros'])==2 and len(result['library_sha256'])==2


def test_window_includes_start_and_excludes_end_edge(fixture):
    activity,_,netlist,vcd,_,_=fixture
    measured=activity.collect(vcd,netlist,'tb.dut',5,9)
    assert measured['macros']['u_ram.g_ecc.u_c0']['ports']['A']['rising_edges']==1
    assert measured['macros']['u_eth.packet.bank0']['ports']['B']['rising_edges']==0


def test_stopped_clock_charges_no_clock_energy_but_retains_leakage(fixture):
    activity,energy,netlist,vcd,pdk,pins=fixture
    clk=pins['u_ram.g_ecc.u_c0','A','CLK']
    vcd.write_text(vcd.read_text().replace('1'+clk+'\n', '0'+clk+'\n'))
    measured=activity.collect(vcd,netlist,'tb.dut',1,20)
    result=energy.estimate(measured,netlist,pdk,'nom_typ_1p20V_25C')
    assert result['macros']['u_ram.g_ecc.u_c0']['clock_energy_pj']==0
    assert result['macros']['u_ram.g_ecc.u_c0']['leakage_energy_pj']>0
    assert result['clock_energy_pj']==14


@pytest.mark.parametrize('problem', ['unknown_control','clock_x','bist','race','missing_pin','truncated','glitch','backwards','no_timescale'])
def test_ambiguous_missing_or_unknown_vcd_is_rejected(fixture, problem):
    activity,_,netlist,vcd,_,pins=fixture
    s=vcd.read_text();men=pins['u_ram.g_ecc.u_c0','A','MEN'];clk=pins['u_ram.g_ecc.u_c0','A','CLK']
    if problem=='unknown_control':s=s.replace('#4\n1'+men,'#4\nx'+men)
    elif problem=='clock_x':s=s.replace('#5\n1'+clk,'#5\nx'+clk)
    elif problem=='bist':s=s.replace('0'+pins['u_ram.g_ecc.u_c0','A','BIST_EN'], '1'+pins['u_ram.g_ecc.u_c0','A','BIST_EN'])
    elif problem=='race':s=s.replace('#4\n1'+men+'\n#5', '#5\n1'+men+'\n#5')
    elif problem=='missing_pin':s=s.replace('A_BIST_EN $end', 'A_BIST_OTHER $end')
    elif problem=='truncated':s=s.replace('#20\n','#19\n')
    elif problem=='glitch':s=s.replace('#5\n1'+clk,'#5\n1'+clk+'\n0'+clk)
    elif problem=='no_timescale':s=s.replace('$timescale 1 ns $end\n','')
    else:s=s.replace('#9\n','#6\n')
    vcd.write_text(s)
    with pytest.raises(ValueError):activity.collect(vcd,netlist,'tb.dut',1,20)


def test_unknown_to_high_clock_at_start_is_not_silently_ignored(fixture):
    activity,_,netlist,vcd,_,pins=fixture
    clk=pins['u_ram.g_ecc.u_c0','A','CLK']
    vcd.write_text(vcd.read_text().replace('0'+clk+'\n', 'x'+clk+'\n', 1))
    with pytest.raises(ValueError, match='Unknown-to-high'):
        activity.collect(vcd,netlist,'tb.dut',5,20)


@pytest.mark.parametrize('problem', ['missing_macro','wrong_master','missing_port','wrong_netlist','missing_state','negative','fractional','boolean','wrong_edges','zero_duration','bad_window'])
def test_incomplete_or_unbound_activity_never_produces_power(fixture, problem):
    activity,energy,netlist,vcd,pdk,_=fixture
    measured=activity.collect(vcd,netlist,'tb.dut',1,20)
    ram=measured['macros']['u_ram.g_ecc.u_c0'];counts=ram['ports']['A']
    if problem=='missing_macro':del measured['macros']['u_ram.g_ecc.u_c0']
    elif problem=='wrong_master':ram['master']=ETH
    elif problem=='missing_port':del measured['macros']['u_eth.packet.bank0']['ports']['B']
    elif problem=='wrong_netlist':measured['source_sha256']['netlist']='0'*64
    elif problem=='missing_state':del counts['state_edges']['000']
    elif problem=='negative':counts['state_edges']['000']=-1
    elif problem=='fractional':counts['state_edges']['000']=0.5
    elif problem=='boolean':counts['state_edges']['000']=False
    elif problem=='wrong_edges':counts['rising_edges']+=1
    elif problem=='zero_duration':measured['elapsed_ns']=0
    else:measured['end_ns']=21
    with pytest.raises(ValueError):energy.estimate(measured,netlist,pdk,'nom_typ_1p20V_25C')


@pytest.mark.parametrize('problem', ['units','missing','duplicate','fall','negative','unclosed'])
def test_unsupported_liberty_never_gets_a_silent_energy_estimate(fixture, problem):
    _,energy,_,_,pdk,_=fixture
    p=pdk/'libs.ref/sg13g2_sram/lib'/f'{RAM}_typ_1p20V_25C.lib';s=p.read_text()
    if problem=='units':s=s.replace('1,pf','1,ff')
    elif problem=='missing':s=s.replace('A_MEN&A_WEN&A_REN','A_MEN&A_WEN&A_OTHER')
    elif problem=='duplicate':s=s.replace('!A_MEN&!A_WEN&!A_REN','!A_MEN&A_WEN&!A_REN')
    elif problem=='fall':s=s.replace('fall_power("scalar") { values(0); }','fall_power("scalar") { values(1); }',1)
    elif problem=='negative':s=s.replace('values(1);','values(-1);',1)
    else:s=s[:-4]
    p.write_text(s)
    with pytest.raises(ValueError):energy.read_tables(pdk,RAM,'typ_1p20V_25C')


def test_legacy_cli_requires_explicit_opt_in(tmp_path):
    source=tmp_path/'old.json';source.write_text('{}')
    result=subprocess.run([sys.executable,str(FLOW/'macro_energy.py'),str(source),'--window','idle'],capture_output=True,text=True)
    assert result.returncode==2 and '--legacy-six-macros' in result.stderr and not result.stdout


@pytest.mark.parametrize('master', [RAM,ETH,'RM_IHPSG13_1P_2048x64_c2_bm_bist','RM_IHPSG13_1P_1024x32_c2_bm_bist'])
@pytest.mark.parametrize('corner', ['typ_1p20V_25C','slow_1p08V_125C','fast_1p32V_m55C'])
def test_installed_native_library_tables_are_complete(modules, master, corner):
    import os
    _,energy=modules
    pdk=Path(os.environ.get('PWR_PDK',str(Path(os.environ.get('PDK_ROOT',str(Path.home()/'.ciel')))/'ihp-sg13g2')))
    if not pdk.is_dir():pytest.skip('Native IHP SRAM Liberty is not installed')
    tables,leak,_=energy.read_tables(pdk,master,corner)
    assert len(tables)==(2 if '_2P_' in master else 1) and leak>0
    assert all(len(table)==8 and table['101']>table['000'] for table in tables.values())


def test_historical_six_macro_arithmetic_remains_explicit_and_reproducible(tmp_path):
    pdk=tmp_path/'pdk';libdir=pdk/'libs.ref/sg13g2_sram/lib';libdir.mkdir(parents=True)
    for master in ('RM_IHPSG13_1P_2048x64_c2_bm_bist','RM_IHPSG13_1P_1024x32_c2_bm_bist'):
        (libdir/(master+'_typ_1p20V_25C.lib')).write_text(library(master))
    derived={f'{prefix}_{state}{bank}':{'high_cycles':1}
             for prefix,banks in [('ram',range(4)),('rom',range(2))]
             for state in ('rd','wr','dr','dw') for bank in banks}
    source=tmp_path/'old.json';source.write_text(json.dumps({'windows':{'idle':{'cycles':4,'derived':derived}}}))
    command=[sys.executable,str(FLOW/'macro_energy.py'),str(source),'--legacy-six-macros',
             '--window','idle','--pdk-dir',str(pdk)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'HISTORICAL SIX-MACRO MODEL ONLY' in result.stdout
    assert '1.350600' in result.stdout  # 108 pJ / 80 ns + six 100 nW cells
    derived['ram_rd0']['high_cycles']=0
    source.write_text(json.dumps({'windows':{'idle':{'cycles':4,'derived':derived}}}))
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==2 and 'Incomplete' in result.stderr
