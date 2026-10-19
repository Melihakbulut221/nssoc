# Measured critical-data buffer candidate

This experiment targets high-delay weak combinational output drivers observed in the exact native three-corner worst-setup path sample from run39288404219. It starts from the routed database of run39243328773, SHA256 `7bcceba57841a8e293918580db654163fa3d45010ec1bbe0e2a50e3b275316ba`.

The source route has149592instances:148871retained preparation instances plus721new routing antenna diodes. All149592are retained with identical masters, locations and original pins except the explicitly split output connections. This corrects any earlier shorthand that counted only the148871pre-route instances.

Selection uses the actual data portion of each path, after the launch output and before capture-clock analysis. It requires cap>=0.07pF, slew>=0.5ns and cell delay>=0.5ns on an allowed weak combinational X/Y output. Clock trees, state elements, SRAM and prior added buffers are excluded. The thresholds select an experiment; they do not change any acceptance limit. The observed o21ai_1 driver$1824847/Y (3.871412ns delay,0.331520pF) must be included. The sample is not a full endpoint census.

Native OpenDB checks actual drivers, sinks, fanout, routed lengths and master names before mutation. Positive buf16cells are inserted near each selected driver; existing output ports stay on their original nets. All original cells are fixed during legalization. Native placement, exact topology/geometry and equation proofs are mandatory, including an actual newly inserted buffer inversion that must be rejected. No reroute or timing acceptance is claimed by this preparation.

The previous route still fails setup/hold, slew/cap/fanout and32antenna nets. The next stage must use the new preparation receipt, restore the complete original state/proof ancestry, reroute, extract fresh RC and evaluate all three original corners with20/4/8/8ns clocks and5percent derate. Compare setup and hold together; do not accept an improvement that silently drops other failures. Nominal OpenRCX is not qualified min/maxRC or transistorLVS.

Execution and evidence publication are exclusively on GitHub Actions. No local checkout, CAD execution, waveform or archive download is required.
