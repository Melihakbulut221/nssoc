# XOR load-v3 candidate after full-wire rejection

The actual load-v2 parent with4020R/2641C failed the unchanged100mV gate: nominal98.7526195mV(13below),cold85.8977980mV(387below). All768signs and19HBTengineering screens passed. This is insufficient signal margin, not a native execution failure. Original raw captures remain in run39039570837.

Candidatev3 changes only XD0007/XD0008 resistor lengths1.4to1.8um, width18um unchanged. Larger load resistance may increase differential swing but also changes settling and transistor headroom. This is a design hypothesis requiring actual native measurements. Input common modes, drivers,50fFoutputloads,500uAbias,256symbols/768samples,0.3/0.5/0.7UI sampling,34ns/.3125ps,all19HBTbounds,OFF/zeroOP and diagnostic rejection remain unchanged.

The first campaign tests nominal/hot_low/cold_high and an actual swapped-output control using the frozen native schematic controller. No oldRC network is scaled or claimed as the new physical layout. If schematic gates pass, the new canonical layout input requires fresh geometry,560categoryDRC,deep/flatLVS,actualphysicalfaults,newcrossedparentrouting,fullRCbinding/composition and the same fullwire waveform campaign. FullCDR/serialPHY and mainchip acceptance remain open.
