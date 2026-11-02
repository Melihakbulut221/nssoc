# Same-net Via1 access reinforcement candidate

The current4ccf1212 layout is physically clean but loaded41405079602 fails original gates. Qualified resistance41407813062 proves the local4um M1 widening only reduces each source-ground path by0.6357ohm;24other paths do not change. Current critical geometry41408690630 and whole-wave41408975201 are the actual diagnostic inputs.

This candidate inserts ONLY Via1 cuts into existing same-net Metal1/Metal2 overlap near all28critical native terminals selected by the32actual resistance queries: selector collectors/emitters, driving HBT emitters, eight MOS drains and eight MOS sources. No original metal is widened, removed or replaced; no primitive or device parameter changes. Every cut is independently enclosed by both physical conductor regions owned by the target's actual native component. Unknown Via1 datatypes are treated as obstacles.

Search each native terminal's50um square window using its nearest5nm placement reference (original anchor is unchanged),480nm pitch,190nm square cuts,50nm enclosure by EACH existing metal and240nm minimum clearance from every existing and already-added Via1. Keep all original85geometry controls and10new positive/adversarial enclosure/grid/spacing/shape/extent controls. Require at least4additional same-net cuts in each of the8MOS drain windows, exact serialized sole layer19/0 delta, unchanged hierarchy cell names and exact reversal to every original material region. If actual geometry does not admit the required coverage, retain all refusals and do not accept a GDS.

The primary IHP main DRC table lists Via1 width190nm and spacing220nm; Metal1 enclosure minimum10nm. This proposal uses stricter240nm spacing and50nm enclosure on both metals, followed by the complete native DRC deck; it does not substitute proposal guards for DRC.
https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/02_main_rules.html

IHP process tables list Via1 target resistance9ohm per cut (5–20ohm range) and0.4mA per Via1 under the stated lifetime/temperature conditions. These are motivation for checking parallel access, not an acceptance claim or an assumed equal current split. Actual current distribution, metal widths, PVT/EM and full extracted electrical behavior remain required.
https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html

No electrical improvement or completePHY is claimed from generation. A generated candidate must pass full560DRC/deep-flatLVS13, independent complete canonical per-partition Via1 ownership, freshRC and unchanged loaded waveform gates. Native generation and data stay in GitHub; preserve all failures. Ground paths with only a single minimum overlap may admit no new cuts; the proposal explicitly records coverage rather than inventing an upper-metal connection.
