* Exploratory pre-layout clock buffer; sizing resistors are ideal, NOT PEX.
* Input differential pair, cascodes, crossed emitter followers, native current mirrors.
* Same 2.5 V supply and original external 10 ohm clock source resistance.
Xip_0 ep inp tail 0 npn13G2 Nx=2
Xip_1 ep inp tail 0 npn13G2 Nx=2
Xip_2 ep inp tail 0 npn13G2 Nx=2
Xin_0 en inn tail 0 npn13G2 Nx=2
Xin_1 en inn tail 0 npn13G2 Nx=2
Xin_2 en inn tail 0 npn13G2 Nx=2
Xcp_0 cp cas ep 0 npn13G2 Nx=2
Xcp_1 cp cas ep 0 npn13G2 Nx=2
Xcp_2 cp cas ep 0 npn13G2 Nx=2
Xcn_0 cn cas en 0 npn13G2 Nx=2
Xcn_1 cn cas en 0 npn13G2 Nx=2
Xcn_2 cn cas en 0 npn13G2 Nx=2
Xfp_0 avdd cn outp 0 npn13G2 Nx=5
Xfp_1 avdd cn outp 0 npn13G2 Nx=5
Xfp_2 avdd cn outp 0 npn13G2 Nx=5
Xfn_0 avdd cp outn 0 npn13G2 Nx=5
Xfn_1 avdd cp outn 0 npn13G2 Nx=5
Xfn_2 avdd cp outn 0 npn13G2 Nx=5
Xref bias bias 0 0 npn13G2 Nx=1
Xtail_0 tail bias 0 0 npn13G2 Nx=4
Xtail_1 tail bias 0 0 npn13G2 Nx=4
Xtail_2 tail bias 0 0 npn13G2 Nx=4
Xtp_0 outp bias 0 0 npn13G2 Nx=4
Xtp_1 outp bias 0 0 npn13G2 Nx=4
Xtp_2 outp bias 0 0 npn13G2 Nx=4
Xtp_3 outp bias 0 0 npn13G2 Nx=4
Xtn_0 outn bias 0 0 npn13G2 Nx=4
Xtn_1 outn bias 0 0 npn13G2 Nx=4
Xtn_2 outn bias 0 0 npn13G2 Nx=4
Xtn_3 outn bias 0 0 npn13G2 Nx=4
* Double only output follower and matched sink area/current for measured output-stage delay.
Xfp_3 avdd cn outp 0 npn13G2 Nx=5
Xfp_4 avdd cn outp 0 npn13G2 Nx=5
Xfp_5 avdd cn outp 0 npn13G2 Nx=5
Xfn_3 avdd cp outn 0 npn13G2 Nx=5
Xfn_4 avdd cp outn 0 npn13G2 Nx=5
Xfn_5 avdd cp outn 0 npn13G2 Nx=5
Xtp_4 outp bias 0 0 npn13G2 Nx=4
Xtp_5 outp bias 0 0 npn13G2 Nx=4
Xtp_6 outp bias 0 0 npn13G2 Nx=4
Xtp_7 outp bias 0 0 npn13G2 Nx=4
Xtn_4 outn bias 0 0 npn13G2 Nx=4
Xtn_5 outn bias 0 0 npn13G2 Nx=4
Xtn_6 outn bias 0 0 npn13G2 Nx=4
Xtn_7 outn bias 0 0 npn13G2 Nx=4
Rup_p avdd cp 50
Rup_n avdd cn 50
Rdown_p cp 0 430
Rdown_n cn 0 430
Rcas_hi avdd cas 100
Rcas_lo cas 0 355
* Supply-referenced bias avoids forcing reference current above a rising rail.
* 3.2 kohm nominal estimate: (2.5 V - 0.9 V) / 0.5 mA; actual current measured by native model.
Rref avdd bias 3200
