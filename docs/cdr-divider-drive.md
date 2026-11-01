# Twelve-divider drive experiment

The complete original PD650 nominal-late transient (run41288195752,source d638e0e3cd15a0ee930212c27ab1f238b5085237) failed all six fixed output gates and the phase gate. It is preserved. Authenticated complete-wave readouts41293861314 and41294574040 localize downstream lag even after source samplers are valid: at0.9UI,A/C output buffers have77/43 wrong-sign samples; each D selector output has89. X never reaches the positive100mV required output level. These diagnostics are not new acceptance criteria.

This candidate halves both legs of six1um-wide resistor dividers, preserving nominal ratios:
- A/C series227,229,238,240:1.8um to0.9um.
- A/C shunts228,230,239,241:10.8um to5.4um.
- D series234,236:6um to3um.
- D shunts235,237:8.6um to4.3um.

The original generation is authenticated first against the published650-device model SHA2567787330b1bd617a1da93ca6cce0c1b4b3d874a4299cde70733f32fd9fc0b4150. Each selected card and physical descriptor has exact ordered terminal,parameter and identity checks. Reversing the twelve changes must recover every prior model byte and descriptor value. The same divider delta is used in the original500-device baseline binder and the explicit200-unit MOS model. There are24 unique resistor differences versus the original500 model, since eight overlap the prior twenty changes. Selector topology already uses D; no B-to-D rewiring is proposed.

The original source files and tests are retained. The old workflow is archived verbatim at docs/evidence/cdr-divider-drive-inputs/original-workflow.txt and checked against the original source manifest; the actual supplemental workflow has separate exact pins. Original test bodies execute unchanged with the explicit supplemental source gate. New controls reject75 divider/census corruptions, independently check six ratios, and exercise the actual compiled binding path. Synthetic fixture checks are not native electrical evidence.

Native execution requires a separately successful exact-source controls dispatch plus an independently created,empty,read-back exact-source release. The original acquire/restore/runtime,prepare/measure bodies,1301 captured vectors,256 bits,nominal_late stimulus,device/current/output/phase limits and failure publication remain unchanged. All raw outputs and runtime/model files stay on GitHub. Original device diagnostics and numerical warnings are still failures.

Lower resistance increases loading and may reduce headroom. No pass is predicted. Retained original distributed wire RC is exploratory; changed resistor dimensions and all200 MOS physical units require regenerated layout and new extraction. This experiment does not establish PLL/CDR closure,full serial Gen3x4,mainchip integration,final timing or manufacturing acceptance.

## Execution record

Source controls41295792666 passed on 3a6f1f9e3b30f97ffae87f43cf0f7f00e2d2ab43. Full proof 29ca141af33df09b69c320ccdceb92ae1bbc3c63 (docs/evidence/divider-drive-controls-41295792666). Native trial41295928971 has independently reserved release430496244 and the exact same source. Terminal acceptance is not yet established; retain every failure.

## Native terminal result

Run41295928971 completed with electrical rejection. Simulator returncode0,diagnostics[],device gates pass; all six data gates fail. Phase29.329406mV remains below the unchanged30mV criterion. Full proof 19d07ce5f55be3d0c09014f56df9e76a51c9aa1a at docs/evidence/divider-drive-native-terminal-41295928971. Retained-wire RC trial does not establish regenerated layout or fresh extracted RC.
