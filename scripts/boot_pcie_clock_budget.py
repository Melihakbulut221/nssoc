"""Guard the functional boot packet clock at its 250 MHz interface budget."""
CLOCK_LINE = "  initial begin #1.3; forever #4 pcie_clk = ~pcie_clk; end"
CLOCK_GUARD = r'''
  realtime nssoc_previous_pcie_edge;
  realtime nssoc_pcie_period;
  integer nssoc_pcie_edges = 0;
  always @(posedge pcie_clk) begin
    if (nssoc_pcie_edges > 0) begin
      nssoc_pcie_period = $realtime - nssoc_previous_pcie_edge;
      if (nssoc_pcie_period < 3.999 || nssoc_pcie_period > 4.001) begin
        $display("NSSOC_BOOT_PCIE_CLOCK_FAIL period_ns=%0.3f", nssoc_pcie_period);
        $finish;
      end
      if (nssoc_pcie_edges == 1)
        $display("NSSOC_BOOT_PCIE_CLOCK_PASS period_ns=%0.3f", nssoc_pcie_period);
    end
    nssoc_previous_pcie_edge = $realtime;
    nssoc_pcie_edges = nssoc_pcie_edges + 1;
  end
'''
def adapt(text):
    assert text.count(CLOCK_LINE)==1
    assert chr(96)+"timescale 1ns / 1ps" in text
    changed=text.replace(CLOCK_LINE,CLOCK_LINE.replace("forever #4","forever #2")+CLOCK_GUARD)
    assert changed.replace(CLOCK_LINE.replace("forever #4","forever #2")+CLOCK_GUARD,CLOCK_LINE)==text
    return changed
