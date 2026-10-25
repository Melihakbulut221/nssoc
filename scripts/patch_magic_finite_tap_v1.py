#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Private finite-tap technology and native grid/arithmetic repair.

Original Magic/PDK and frozen HBT multiplicity v3 remain unchanged. Modified
Magic C keeps its original UC Regents permissive notice; modified IHP technology
keeps Apache-2.0. No fitted device value or geometry substitution is introduced.
"""
import argparse
import hashlib
from pathlib import Path

PINS = {
    'ExtBasic.c': 'c72a67e5575d7f28680777e640666654d076eda277775916420753f43dc62428',
    'ExtTech.c': '0f6520adb71a1ba1eba1cac447635068f134a8da29fdde4c5dbb4a1c88a624ca',
    'ihp-sg13g2-extract.tech': 'd17966b1e432388c34ef978faa5a416a850abde2cdc47f2320ff0c94ae9458ad',
}

AREA_BEFORE = '''		    resvalue = (ResValue)(pointertype)HashGetValue(he);
		    resvalue /= (ResValue)reg->treg_area;

		    he = HashLookOnly(&extTransRec.tr_devrec->exts_deviceResist,
				"perimeter");
		    if (he != NULL)
		    {
			ResValue perimr;
			perimr = (ResValue)(pointertype)HashGetValue(he);
			perimr /= (ResValue)extTransRec.tr_perim;

			/* Perimeter and area resistances combine in parallel */
			resvalue = (ResValue)(1.0 / ((1.0 / (double)perimr) +
				(1.0 / (double)resvalue)));
		    }'''

AREA_AFTER = '''            /* Keep the existing physical coefficients, but do not truncate
             * either branch or their parallel combination to integer ohms. */
            double measured = (double)(pointertype)HashGetValue(he)
                    / (double)reg->treg_area;
            he = HashLookOnly(&extTransRec.tr_devrec->exts_deviceResist,
                    "perimeter");
            if (he != NULL)
            {
                double perimeter = (double)(pointertype)HashGetValue(he)
                        / (double)extTransRec.tr_perim;
                measured = 1.0 / (1.0 / perimeter + 1.0 / measured);
            }
            fprintf(outFile, " %c=%g", chkParam->pl_param[0], measured);
            break;'''

SCALE_BEFORE = '''	    devptr->exts_deviceGateCap *= sqn;
	    devptr->exts_deviceGateCap /= sqd;

	    for (chkParam = devptr->exts_deviceParams; chkParam;'''

SCALE_AFTER = '''	    devptr->exts_deviceGateCap *= sqn;
	    devptr->exts_deviceGateCap /= sqd;

            /* devresist coefficients are stored in the current geometry
             * grid, just like parameter areas/lengths.  GDS import may
             * refine that grid after technology parsing. */
            {
                const char *keys[] = {"area", "perimeter"};
                int k;
                for (k = 0; k < 2; k++)
                {
                    HashEntry *entry = HashLookOnly(&devptr->exts_deviceResist,
                            keys[k]);
                    if (entry != NULL)
                    {
                        double factor = (k == 0) ? (double)sqd / sqn :
                                (double)scaled / scalen;
                        double value = (double)(spointertype)HashGetValue(entry)
                                * factor;
                        if (value < 0.0 || value > 2147483647.0)
                            TxError("NSSOC devresist grid coefficient overflow\\n");
                        else
                            HashSetValue(entry, (spointertype)(ResValue)value);
                    }
                }
            }
	    for (chkParam = devptr->exts_deviceParams; chkParam;'''

TAP_BEFORE = ''' # "ptap1" is not a simulatable device.  Used for LVS only.
 # device csubcircuit ptap1 *ptap,*hvtap pwell,space/w r=r a=a p=p w=w l=l

 # "ntap1" is not a simulatable device.  Used for LVS only.
 # device csubcircuit ntap1 *ntap,*hvntap dnwell r=r a=a p=p w=w l=l'''

TAP_AFTER = ''' # Explicit finite taps, using the existing native LVS geometry/connectivity
 # and the pinned foundry ptap1/ntap1 subcircuits (R, w and l parameters).
 disconnect *ptap *psd,pwell
 disconnect *hvptap *hvpsd,pwell
 disconnect *ntap *nsd,nwell,dnwell
 disconnect *hvntap *hvnsd,nwell,dnwell
 device csubcircuit ptap1 *ptap,*hvptap pwell,space/w r=r w=w l=l
 device csubcircuit ntap1 *ntap,*hvntap nwell r=r w=w l=l
 devresist *ptap,*hvptap area 980
 devresist *ptap,*hvptap perimeter 980
 devresist *ntap,*hvntap area 980
 devresist *ntap,*hvntap perimeter 980'''


def patch(name, data):
    if name not in PINS or hashlib.sha256(data).hexdigest() != PINS[name]:
        raise ValueError('Exact unchanged native Nx-v3 parent required')
    edits = {
        'ExtBasic.c': [(AREA_BEFORE, AREA_AFTER)],
        'ExtTech.c': [(SCALE_BEFORE, SCALE_AFTER)],
        'ihp-sg13g2-extract.tech': [
            ('variants (),(hrhc),(lrhc),(hrlc),(lrlc)\n'
             ' substrate *psd,*ptap,*hvpsd,*hvptap,space/w,pwell well $SUB -dnwell,digisub',
             'variants (),(hrhc),(lrhc),(hrlc),(lrlc)\n'
             ' substrate *psd,*hvpsd,space/w,pwell well $SUB -dnwell,digisub'),
            (TAP_BEFORE, TAP_AFTER),
        ],
    }[name]
    text = data.decode()
    for before, after in edits:
        if text.count(before) != 1:
            raise ValueError('Missing or ambiguous finite-tap patch anchor')
        text = text.replace(before, after)
    inverse = text
    for before, after in reversed(edits):
        inverse = inverse.replace(after, before)
    if inverse.encode() != data:
        raise ValueError('Unexpected finite-tap source delta')
    return text.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with args.output.open('xb') as stream:
        stream.write(patch(args.source.name, args.source.read_bytes()))


if __name__ == '__main__':
    main()
