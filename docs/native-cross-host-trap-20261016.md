# Catch the restored native process fault

Diagnostic38901137382 proved the exact saved image, circuit, simulator and model libraries can execute a fresh4ns reference on AMD EPYC7763: all12818rows/34probes match source bit-exact. The actual restored process still raises SIGILL at a retained prefix of2027rows/end0.6298437500000183ns. That separates basic executable compatibility from saved-process portability, but does not yet identify the failing instruction.

The trap workflow uses the documented CRIU `leave-stopped` restore option through runc's `/etc/criu/runc.conf`. It verifies the actual restored host PID is stopped before GDB attaches, catches SIGILL before the native error handler, and preserves instruction bytes, disassembly, registers, symbol/library and stack. The independent fresh reference and original immutable checkpoint/image are retained. This is a diagnostic process pause, no circuit/solver/trajectory edits, no acceptance substitution.

Primary references: https://github.com/opencontainers/runc/blob/main/docs/checkpoint-restore.md ; https://github.com/checkpoint-restore/criu/blob/9539417f3e3cfa4eb84c319cd71f4d52f1f08645/Documentation/criu.txt ; https://sourceware.org/gdb/current/onlinedocs/gdb.html/Signals.html .
