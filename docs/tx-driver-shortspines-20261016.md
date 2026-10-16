# Shorter physical driver spines after the localpins loaded failure

Localpins run38910247036 retained all34ns/77607native rows and original256bits at8GT/s. Output161.702mV and CMOS interface167.974mV passed their original100/150mV gates. Final interface130.597mV failed288samples and12HBTs failed the original0.4V minimum VCE gate;0MOS failures. This is not an accepted driver/PHY.

This new physical variant preserves every device, finite contact, Metal1 access, source schematic, cell location, wire width and upper2x2via type. It only packs the nine separate Metal5 rails into five rows and changes their Metal4 spine lengths and upper via positions. Rail spans remain local to actual contacts. Disjoint x intervals can share a row without being connected; an explicit interval guard and the locked native560categoryDRC/raw100deep-flatLVS/aggregateLVS/fault controls must all agree.

Rows in micrometres: avss50,sub57;drv/gate/dout64;sink/avdd71;din/dvdd78. Before: drv60,gate67,sink74,din81,dout88,dvdd95,avdd102,avss109,sub116. The longest supply/return spines shrink while drv grows4um. No electrical benefit is assumed from geometry alone: mutual capacitance and supply coupling change as well as resistance.

Run fresh physical validation first, then source-bound LEF/junction/wire/terminal-anchor/RC/composition extraction and the unchanged full loaded electrical test. The previous failing source, limits and all negative controls remain. No ideal-wire substitution, threshold waiver or fitted phase is allowed. A passed component still does not establish32:1/four-lane serialization, PLL/CDR, ESD, PVT, qualified extraction or mainchip integration.
