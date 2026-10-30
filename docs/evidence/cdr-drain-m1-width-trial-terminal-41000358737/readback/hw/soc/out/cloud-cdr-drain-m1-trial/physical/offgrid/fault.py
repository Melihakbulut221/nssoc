import pya
L=pya.Layout();L.read('/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-drain-m1-trial/layout/nssoc_cdr_pd500_resistor_v59.gds');top=L.cell('nssoc_cdr_pd500_resistor_v59');assert top is not None
fault='offgrid';ys={'avdd': 32.0, 'avss': 112.0, 'cn': 1014.29, 'cp': 1020.29, 'dn': 996.29, 'dp': 990.29, 'ibda': 2450.44, 'ibdc': 3226.33, 'ibs0': 3500.96, 'ibs1': 4080.2200000000003, 'ira': 1367.92, 'irb': 1044.29, 'irc': 1691.5500000000002, 'ird': 502.03, 'irvx': 4659.48, 'irvy': 4665.48, 'irx': 3787.59, 'iry': 4366.85, 'sub': 192.0, 'vin': 4671.48, 'vip': 4677.48, 'xn': 3823.59, 'xp': 3829.59, 'yn': 4402.85, 'yp': 4408.85}
if fault=='offgrid':top.transform(pya.Trans(1,0))
elif fault=='q_open':
    li=L.layer(134,0);before=pya.Region(top.shapes(li));y=ys['vip'];cut=pya.Region(pya.DBox(5,y-2.2,7,y+2.2).to_itype(L.dbu));after=before-cut;assert before.area()!=after.area();top.shapes(li).clear();top.shapes(li).insert(after)
elif fault=='rail_short':
    top.shapes(L.layer(134,0)).insert(pya.DBox(2.5,min(ys['avdd'],ys['avss'])-.7,3,max(ys['avdd'],ys['avss'])+.7))
else:raise ValueError(fault)
L.write('/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-drain-m1-trial/physical/offgrid/fault.gds')
