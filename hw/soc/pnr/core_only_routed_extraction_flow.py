# SPDX-License-Identifier: Apache-2.0
"""Core-only nominal extraction and actual-SPEF STA; RC corners not qualified."""
import json
import math
from pathlib import Path
from core_only_routed_guards import guarded_sta
from replay_onehot_routed_extraction_flow import AuditedRCX, AuditedRoutedSTA, ROOT, sha
from interface_flow import Interfaces
from librelane.flows import Flow

class CoreAuditedRCX(AuditedRCX):
    id = "NSSOC.CoreOnlyRouteRCX"

class CoreExtractedSTA(AuditedRoutedSTA):
    id = "NSSOC.CoreOnlyExtractedSTA"
    def run_corner(self, state_in, current_env, corner, corner_dir):
        # Capture only this native process's updates, not inherited state metrics.
        updates = super().run_corner(state_in, current_env, corner, corner_dir)
        suffix = "__corner:" + corner
        assert not [k for k in updates if "__corner:" in k and not k.endswith(suffix)]
        for key in ("timing__setup__ws", "timing__hold__ws",
                    "timing__setup_vio__count", "timing__hold_vio__count",
                    "design__max_cap_violation__count", "design__max_slew_violation__count"):
            value = updates.get(key + suffix)
            assert isinstance(value, (int, float)) and not isinstance(value, bool)
            assert math.isfinite(value), (corner, key, value)
            if key.endswith("__count"):
                assert value >= 0 and value == int(value)
        (Path(corner_dir) / "fresh_metrics.json").write_text(json.dumps(updates, indent=2) + "\n")
        return updates

    def get_script_path(self):
        # Skip the legacy four-clock adapter, retaining the native STA producer.
        original = Path(super(AuditedRoutedSTA, self).get_script_path())
        guard = ROOT / 'hw/soc/flow/check_timing_derate.tcl'
        target = Path(self.step_dir) / 'core_only_extracted_sta.tcl'
        target.write_text(guarded_sta(original.read_text(), guard.read_text()))
        (Path(self.step_dir) / 'native-sta-script-proof.json').write_text(json.dumps(dict(
            original=str(original), original_sha256=sha(original),
            guard_sha256=sha(guard), adapted_sha256=sha(target),
            required_clock='clk_i', period_ns=20, derate_percent=5,
            engine='standalone OpenSTA', requires_spef=True,
            report_label_assignment_corrected=True,
            qualified_rc_minmax=False, accepted=False), indent=2) + '\n')
        return str(target)

@Flow.factory.register()
class CoreOnlyRoutedExtraction(Interfaces):
    Steps = [CoreAuditedRCX, CoreExtractedSTA]

if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
