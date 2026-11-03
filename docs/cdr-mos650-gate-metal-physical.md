# Independent full physical verification of local gate metallization

Producer run41706600267, source155dd4718ec9ffe6847cfd73f637466ec8f4208c, release433145277.
Actual candidate GDS: {'bytes': 1640956, 'sha256': '48df330263db46d13d15e61bac380db8f10a0917815a72b5fdeee8d14e8aa461'}.
Independent650-device reference: {'bytes': 35500, 'sha256': '21d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb'}.

The only candidate acquisition changes adapt the newly sealed archive/layout
paths and bind every generation report. The checker itself is byte-identical
to the already qualified650 checker: all560 DRC categories, deep and flat
LVS with200MOS/124HBT/98resistors/7MIM/221ptaps, all25 ports and all13
intentional fault controls remain unchanged. The schematic is independently
rebuilt from the original plan during controls and matched byte-for-byte,
not generated from candidate LVS extraction.

The candidate preserves all original device geometry and adds local gate
contacts and160nm Metal1 straps, with explicit source/drain M1/Via1
relocation and same-net M2 landing extensions. The complete actual GDS is independently checked;
the generator's geometric guards do not substitute for DRC or LVS. All
native outcomes, including rejections, remain in cloud releases. Full RC,
electrical qualification, full serialPHY and final mainchip timing remain open.
