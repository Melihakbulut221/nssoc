# V34 matched HBT area screen
The six complete V33 diagnostic runs reproduced all original120HBT and four sampler results. At all255 uniquely associated steering transitions per sampler the master input has the expected polarity. In bleed12 both phases, master outputs clear100mV at the original37.5ps output deadline, while slave outputs still miss that deadline in97..129 bits. Actual selector-base clock crossings lag the external reference by about2..4ps, and collector-current steering crosses roughly12..14ps after the reference. These observations locate a transfer/settling problem but do not prove one physical cause.

The measured maximum current per emitter in the selected HBTs is roughly2.05..2.22mA. Simply halving their emitter count would risk the unchanged3mA-per-emitter bound; no such reduced-area candidate is used. Instead this experiment tests matched area increases to reduce current density while allowing the real model to expose the extra capacitance penalty. Improvement is a hypothesis, not a predicted pass.

Three disclosed variants retain the bleed12 candidate's eight slave-bleed resistor edits:
- slave_area15: only slave selectors Nx2→3 and slave data/hold Nx4→6 (32HBT edits).
- all_area15: both master/slave selectors Nx2→3 and data/hold Nx4→6 (64HBT edits).
- all_area20: both master/slave selectors Nx2→4 and data/hold Nx4→8 (64HBT edits).

Selection comes from the pinned native master/slave topology, never guessed instance numbers. Every other circuit card and all17918R12850C records remain exact; candidate contracts preserve every terminal and update only the explicitly selected dimensions. All476 devices and original full1104-column34.25ns captures are retained. Original clocks, bit pattern, sampling phases,150fF sampler/50fF XOR loads,37.5ps/100mV acceptance, phase/VI gates and device limits are unchanged.

These are exploratory intrinsic-model screens on frozen V32 wire RC. No larger-HBT layout, new contact parasitics, DRC/LVS or fresh RC is claimed. A useful candidate must subsequently be physically generated and re-extracted, then pass the same full loaded tests. All failures remain in cloud releases. No candidate is accepted merely by completing its transient or passing transistor checks.
