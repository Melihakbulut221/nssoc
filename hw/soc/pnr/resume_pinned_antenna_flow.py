# SPDX-License-Identifier: Apache-2.0
"""Reroute verified diode-legalized state with original constraints and strict final gates."""
import hashlib,json,re,subprocess,os
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb
from librelane.state import DesignFormat
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
RESET_ROUTES='if {[ord::openroad_version] ne "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"} {error "Runtime changed"}\ncheck_placement -verbose\nset removed 0\nforeach net [[ord::get_db_block] getNets] {\n if {[$net isSpecial] || [$net getSigType] in {POWER GROUND}} {continue}\n set wire [$net getWire]\n if {$wire ne "NULL"} {odb::dbWire_destroy $wire; incr removed}\n}\nif {$removed == 0} {error "No signal routes cleared"}\nputs "NSSOC_SIGNAL_ROUTES_REBUILT $removed"\n'
class LegalizedGlobalRouting(OpenROAD.GlobalRouting):
    id='NSSOC.LegalizedGlobalRouting'
    def run(self,state_in,**kwargs):
        assert sha(state_in[DesignFormat.ODB])=='c9deaebb26a07bf0909c249547156b1a1cb96401c8ccfa3748acff818131d959'
        assert sha(state_in[DesignFormat.SDC])=='1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511'
        views,metrics=super().run(state_in,**kwargs)
        root=Path(__file__).resolve().parents[3]
        env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
        with (Path(self.step_dir)/'jumper-invariants.log').open('w') as log:
            proc=subprocess.run(['openroad','-exit','-python',str(root/'scripts/check_pre_drt_jumper_invariants.py')],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=300)
        assert proc.returncode==0,'Native jumper invariants failed'
        logtext='\n'.join(p.read_text(errors='replace') for p in Path(self.step_dir).glob('*.log'))
        counts=[(int(a),int(b)) for a,b in re.findall(r'Inserted (\d+) jumpers for (\d+) nets\.',logtext)]
        report={'status':'GLOBAL_GUIDE_JUMPER_SCREEN_COMPLETE','accepted_as_routed':False,'jumper_messages':counts,'total_reported_jumpers':sum(a for a,b in counts),'manufacturing_approval':False,'scope':'Pre-DRT guide repair only. No detailed route or final antenna/timing acceptance.'}
        (Path(self.step_dir)/'jumper-screen-proof.json').write_text(json.dumps(report,indent=2))
        assert report['total_reported_jumpers']>0,'No actual jumpers inserted; do not launch DRT as if repair succeeded'
        return views,metrics
    def get_script_path(self):
        original=Path(super().get_script_path());assert sha(original)=='9cceedd2c477f85b25362d5e3833fe0e9c0d85f14248060fc38e3fdec0c6187c'
        text=original.read_text();anchor='read_current_odb\n';assert text.count(anchor)==1
        addition=RESET_ROUTES
        text=text.replace(anchor,anchor+addition)
        phase='source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl\n'
        assert text.count(phase)==1
        text=text.replace(phase,'\nif {![grt::have_routes] || [grt::have_detailed_routes]} {error "Jumper screen requires global routes and no detailed signal wires"}\nset before_count [llength [[ord::get_db_block] getInsts]]\nwrite_db "$::env(STEP_DIR)/before-jumpers.odb"\nwrite_guide "$::env(STEP_DIR)/before-jumpers.guide"\nset diode_cell [lindex [split $::env(DIODE_CELL) "/"] 0]\nif {$diode_cell ne "sg13g2_antennanp"} {error "Unexpected diode master"}\nset repair_args [list $diode_cell -jumper_only -iterations 3 -ratio_margin $::env(GRT_ANTENNA_REPAIR_MARGIN)]\nappend_if_flag repair_args GRT_ALLOW_CONGESTION -allow_congestion\nlog_cmd repair_antennas {*}$repair_args\nif {[llength [[ord::get_db_block] getInsts]] != $before_count} {error "Jumper-only operation changed cell count"}\nif {[grt::have_detailed_routes]} {error "Unexpected detailed wires in guide-only screen"}\ncheck_placement -verbose\nwrite_db "$::env(STEP_DIR)/after-jumpers.odb"\nwrite_guide "$::env(STEP_DIR)/after-jumpers.guide"\nputs NSSOC_PRE_DRT_JUMPER_SCREEN_DONE_NOT_ROUTED\n'+phase)
        target=Path(self.step_dir)/'legalized_grt.tcl';target.write_text(text)
        (Path(self.step_dir)/'legalized-route-proof.json').write_text(json.dumps({'original_script_sha256':sha(original),'adapted_sha256':sha(target),'placement_source_run':43590951082,'scope':'Rebuild signal routes from verified placement to connect new diodes. Supply and special wires retained. No timing/antenna limits relaxed.','manufacturing_approval':False},indent=2))
        return str(target)
@Flow.factory.register()
class ResumePinnedAntenna(Interfaces):
    Steps=[LegalizedGlobalRouting]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
