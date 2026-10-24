# Full PLL845 acquisition result

The contiguous reader completed the original1us recording and all6167 bound terminal-voltage measurements. Run39854075819 is an original acquisition rejection, not a reader timeout or rerun of the native circuit. All3,201,410 original rows and5106 columns were checked, with no removed samples/columns; the130,771,392,219-byte original raw SHA256 remains4646ad014fb3cf44b06adf6b9ec7b29a9ed50011ea7214f4223d1c9acff314d1.

The last0.9–1.0us window reports feedback110.440674MHz instead of the100MHz target, phase span9.190319ns, and failed frequency100ppm, phase50ps and no-slip checks. VCTRL remains0.413489–0.802017V within the development range. All81 rolling windows and108 observed feedback cycles remain in the immutable report. The capture has99 reference edges and109 feedback edges; sustained acquisition is absent.

This establishes a real loop failure requiring diagnosis of the native feedback/PFD/pump/filter/VCO behavior. UP/DOWN voltage duty is not charge-pump current, and raw terminal voltage extrema are not full device-reliability approval. No threshold, control range, waveform alignment, target clock or sample count was changed. The original simulation and failed full analysis are preserved; do not rerun the same native circuit merely because this reader now returns a rejection.
