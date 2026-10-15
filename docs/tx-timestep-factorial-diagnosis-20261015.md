# TSTEP / TMAX startup diagnosis (2026-10-15)

The full 34 ns strict comparison (run38774749514) still fails the unchanged1mV voltage bound: compact8.906847253mV and wire8.111543842mV. Tightening Newton tolerances did not remove the startup discrepancy. No source-bit, phase, observation window or device gate has been relaxed.

The original `.tran step stop 0 step` changes both TSTEP and TMAX. The [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) distinguishes the suggested increment from the maximum integration step. That distinction motivates a factorial experiment; it is not evidence of the root cause yet.

The hosted controller restores the exact strict compact0.125ps source capture38763917040, hashes every archived input and repository circuit file, verifies the executable, and changes only the `.tran` parameters. It runs all four combinations of TSTEP/TMAX0.125ps and0.0625ps through1.2ns. All original models, sources, startup OFF flags, saves, solver options and zero operating point remain. Native raw files and logs are retained. The coarse diagonal is also compared with its original full capture through1.1ns to detect effects of shortening TSTOP.

This is a bounded startup diagnosis, never numerical or physical acceptance. The original0–34ns comparison remains failed until a valid full-capture rerun demonstrates otherwise. No startup removal, fitted timing, redefined oracle or passing substitute is permitted.
