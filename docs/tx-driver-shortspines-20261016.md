# Shorter physical driver spines after the localpins loaded failure

Localpins run38910247036 retained all34ns/77607native rows and original256bits at8GT/s. Output161.702mV and CMOS interface167.974mV passed their original100/150mV gates. Final interface130.597mV failed288samples and12HBTs failed the original0.4V minimum VCE gate;0MOS failures. This is not an accepted driver/PHY.

This new physical variant preserves every device, finite contact, Metal1 access, source schematic, cell location, wire width and upper2x2via type. It only packs the nine separate Metal5 rails into five rows and changes their Metal4 spine lengths and upper via positions. Rail spans remain local to actual contacts. Disjoint x intervals can share a row without being connected; an explicit interval guard and the locked native560categoryDRC/raw100deep-flatLVS/aggregateLVS/fault controls must all agree.

Rows in micrometres: avss50,sub57;drv/gate/dout64;sink/avdd71;din/dvdd78. Before: drv60,gate67,sink74,din81,dout88,dvdd95,avdd102,avss109,sub116. The longest supply/return spines shrink while drv grows4um. No electrical benefit is assumed from geometry alone: mutual capacitance and supply coupling change as well as resistance.

Run fresh physical validation first, then source-bound LEF/junction/wire/terminal-anchor/RC/composition extraction and the unchanged full loaded electrical test. The previous failing source, limits and all negative controls remain. No ideal-wire substitution, threshold waiver or fitted phase is allowed. A passed component still does not establish32:1/four-lane serialization, PLL/CDR, ESD, PVT, qualified extraction or mainchip integration.

## Full loaded result: rejected, run38920723791

The published full34ns waveform contains77738rows, original256source bits and
all three original0.3/0.5/0.7UI sample phases. Zero-source OP is preserved and
solver diagnostics are empty. Nevertheless component_screen_passed is FALSE:
output minimum−1.495250mV,32samples below100mV including one wrong sign;
CMOS interface133.888359mV with68below150mV; final interface79.546312mV
with576below150mV. Twelve HBTs fail minimum0.4V VCE;0MOS fail. Middle/late
phase output margins do not excuse the failed early phase. This is worse than
localpins; do not adopt shortspines or call a completed workflow acceptance.

The exact source summary is release asset647743172, SHA256
5e0a5c85065968c09c742e5bd5cc4ea6348db4637ab29d20882d02da57aaec04.
Parts manifest647743283 SHA1690b7e0b0896e03f58a63dee2edfc9e877012f36e222d674c12559c4aa160e2
retains the full cloud capture. No waveform archive is stored locally.

Static source-bound network measurements show crossing capacitance increased
on drv53.189→64.580fF, gate17.614→21.450fF and sink64.236→70.939fF despite
shorter supply spines. This suggests an RC tradeoff but does not prove causality.
The next controlled cloud experiment uses the better measured localpins source:
separate half-wire-R and half-wire-C studies, retaining every100raw device,
finite contact, wire endpoint, original source,34ns capture, all672MOS/62HBT
probes and original engineering gates. An actual intrinsic-terminal corruption
must be rejected. These deliberately artificial sensitivity cases are never
physical acceptance candidates. Original251R sensitivity38882163369 is not
repeated: it used a different source and its near-zero-R case failed. A future
layout must be physically built, freshly extracted and retested before adoption.
