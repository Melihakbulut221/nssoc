* Exploratory pre-layout clock buffer; sizing resistors are ideal, NOT PEX.
* Input differential pair, cascodes, crossed emitter followers, native current mirrors.
* Same 2.5 V supply and original external 10 ohm clock source resistance.
Xip ep inp tail 0 npn13G2 Nx=12
Xin en inn tail 0 npn13G2 Nx=12
Xcp cp cas ep 0 npn13G2 Nx=12
Xcn cn cas en 0 npn13G2 Nx=12
Xfp avdd cn outp 0 npn13G2 Nx=12
Xfn avdd cp outn 0 npn13G2 Nx=12
Xref bias bias 0 0 npn13G2 Nx=1
Xtail tail bias 0 0 npn13G2 Nx=12
Xtp outp bias 0 0 npn13G2 Nx=16
Xtn outn bias 0 0 npn13G2 Nx=16
Rup_p avdd cp 50
Rup_n avdd cn 50
Rdown_p cp 0 430
Rdown_n cn 0 430
Rcas_hi avdd cas 100
Rcas_lo cas 0 355
