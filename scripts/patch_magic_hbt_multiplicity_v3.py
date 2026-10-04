#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Private opt-in native terminal-component measurement; original Magic stays unchanged.

The target C file retains its original UC Regents permissive license. The new
``n1=Nx`` technology parameter asks the extractor to enumerate every connected
terminal geometry component under the actual device region. Equal rectangular
components on one electrical node supply measured dimensions and multiplicity.
No instance name, declared PCell parameter, or prescribed emitter size is used.
"""
import argparse
import hashlib
from pathlib import Path

SOURCE_SHA = 'b09c5b536fcf5cc320a04fe0b9f23382edc05bbaa86cdd546fcb9a453a93e0be'
TECH_SHA = '72f596aac2826188e42d1e1147ac1749acf47289acd52c66fbe9a6ac036cc638'

COMPONENT_CODE = r'''
/* Opt-in repeated-terminal geometry.  This data is private to ExtBasic.c;
 * no exported structure or ABI changes.  Node connectivity and geometry
 * are checked independently; the technology requests this using n<term>.
 */
typedef struct _exttermcomponents {
    ExtAreaPerimData ap;
    LinkedTile *seen;
    NodeRegion *node;
    int count, area, perim, invalid, tiles;
    Rect bounds;
} ExtTermComponents;

void
extTermComponentTile(Tile *tile, TileType dinfo, ExtTermComponents *data)
{
    LinkedTile *entry = (LinkedTile *)mallocMagic(sizeof(LinkedTile));
    entry->t = tile;
    entry->dinfo = dinfo & TT_SIDE;
    entry->t_next = data->seen;
    data->seen = entry;
    Rect r;
    TiToRect(tile, &r);
    if (data->tiles++ == 0) data->bounds = r;
    else
    {
        data->bounds.r_xbot = MIN(data->bounds.r_xbot, r.r_xbot);
        data->bounds.r_ybot = MIN(data->bounds.r_ybot, r.r_ybot);
        data->bounds.r_xtop = MAX(data->bounds.r_xtop, r.r_xtop);
        data->bounds.r_ytop = MAX(data->bounds.r_ytop, r.r_ytop);
    }
    extTermAPFunc(tile, dinfo, &data->ap);
}

int
extTermComponentFind(Tile *tile, TileType dinfo, ExtTermComponents *data)
{
    LinkedTile *entry;
    double disc, root;
    int a, p, w, l;
    for (entry = data->seen; entry; entry = entry->t_next)
        if (entry->t == tile && entry->dinfo == (dinfo & TT_SIDE)) return 0;
    if (ExtGetRegion(tile, dinfo) != (ExtRegion *)data->node)
        data->invalid = 1;
    data->ap.eapd_area = data->ap.eapd_perim = 0;
    data->tiles = 0;
    extEnumTerminal(tile, dinfo, DBConnectTbl, extTermComponentTile,
            (ClientData)data);
    a = data->ap.eapd_area;
    p = data->ap.eapd_perim;
    disc = (double)p * p - 16.0 * a;
    root = (disc >= 0.0) ? sqrt(disc) : -1.0;
    w = (int)((p + root) / 4.0 + 0.5);
    l = (w > 0) ? a / w : 0;
    if (a <= 0 || p <= 0 || root < 0.0 || w * l != a || 2 * (w + l) != p)
        data->invalid = 1;
    if (a != (data->bounds.r_xtop - data->bounds.r_xbot) *
             (data->bounds.r_ytop - data->bounds.r_ybot))
        data->invalid = 1;
    if (data->count && (data->area != a || data->perim != p))
        data->invalid = 1;
    data->area = a;
    data->perim = p;
    data->count++;
    return 0;
}

void
extCountTerminalComponents(CellDef *def, TransRegion *reg, FindRegion *arg,
        TileTypeBitMask *mask, NodeRegion *node, int terminal, int plane)
{
    ExtTermComponents data;
    LinkedTile *deviceTiles, *entry, *next;
    TileTypeBitMask realmask;
    Rect area;
    memset(&data, 0, sizeof(data));
    data.node = node;
    data.ap.eapd_gatemask = &DBZeroTypeBits;
    data.ap.eapd_gatenode = NULL;
    TTMaskCom2(&data.ap.eapd_mask, mask);
    realmask = *mask;
    TTMaskClearType(&realmask, TT_SPACE);
    extSpecialDevice = NULL;
    arg->fra_uninit = (ClientData)extTransRec.tr_gatenode;
    arg->fra_region = (ExtRegion *)reg;
    arg->fra_each = extSDTileFunc;
    ExtFindNeighbors(reg->treg_tile, reg->treg_dinfo, arg->fra_pNum, arg);
    deviceTiles = extSpecialDevice;
    arg->fra_uninit = (ClientData)reg;
    arg->fra_region = (ExtRegion *)extTransRec.tr_gatenode;
    arg->fra_each = (int (*)())NULL;
    ExtFindNeighbors(reg->treg_tile, reg->treg_dinfo, arg->fra_pNum, arg);
    for (entry = deviceTiles; entry; entry = entry->t_next)
    {
        TiToRect(entry->t, &area);
        /* A contact has residues on several planes.  Count the native
         * terminal geometry plane once, never its overlying metal residue. */
        DBSrPaintNMArea(NULL, def->cd_planes[plane],
            TiGetTypeExact(entry->t) | entry->dinfo, &area, &realmask,
            extTermComponentFind, (ClientData)&data);
    }
    for (entry = deviceTiles; entry; entry = next)
    {
        next = entry->t_next;
        freeMagic((char *)entry);
    }
    extSpecialDevice = NULL;
    for (entry = data.seen; entry; entry = next)
    {
        next = entry->t_next;
        freeMagic((char *)entry);
    }
    if (data.invalid || data.count == 0)
    {
        TxError("NSSOC terminal component geometry/connectivity failure at (%d %d)\n",
                reg->treg_ll.p_x, reg->treg_ll.p_y);
        extTransRec.tr_termcomponents[terminal] = -1;
    }
    else
    {
        extTransRec.tr_termcomponents[terminal] = data.count;
        /* Existing wN/lN formulas now describe each equal component. */
        extTransRec.tr_termarea[terminal] = data.area;
        extTransRec.tr_termperim[terminal] = data.perim;
    }
}

'''


def patch(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError('Exact private v2 ExtBasic.c required')
    text = data.decode()
    edits = [
        ('    int\t\t tr_termarea[MAXSD];', '    int tr_termcomponents[MAXSD];\n    int\t\t tr_termarea[MAXSD];'),
        ('\t    extTransRec.tr_termarea[i] = 0;', '\t    extTransRec.tr_termcomponents[i] = 0;\n\t    extTransRec.tr_termarea[i] = 0;'),
        ('void\nextOutputDevices(def, transList, outFile)', COMPONENT_CODE + 'void\nextOutputDevices(def, transList, outFile)'),
        ('\t    extTransRec.tr_termshared[termcount] = 1;', '''\t    extTransRec.tr_termshared[termcount] = 1;
            for (chkParam = devptr->exts_deviceParams; chkParam;
                    chkParam = chkParam->pl_next)
                if (tolower(chkParam->pl_param[0]) == 'n' &&
                        chkParam->pl_param[1] == '1' + termcount)
                {
                    extCountTerminalComponents(def, reg, &arg, tmask, node,
                            termcount, DBPlane(tt));
                    break;
                }'''),
        ("\t    case 's':\n\t    case 'x':", '''            case 'n':
                if (chkParam->pl_param[1] > '0' && chkParam->pl_param[1] <= '9')
                    fprintf(outFile, " %s=%d", chkParam->pl_name,
                        extTransRec.tr_termcomponents[chkParam->pl_param[1] - '1']);
                break;
\t    case 's':
\t    case 'x':'''),
    ]
    for before, after in edits:
        if text.count(before) != 1:
            raise ValueError('Missing or ambiguous private patch anchor')
        text = text.replace(before, after)
    inverse = text
    for before, after in reversed(edits):
        inverse = inverse.replace(after, before)
    if inverse.encode() != data:
        raise ValueError('Unexpected source delta')
    return text.encode()


def patch_technology(data):
    if hashlib.sha256(data).hexdigest() != TECH_SHA:
        raise ValueError('Exact private v2 axis/contact technology required')
    before = 'npn13g2 npn gec *ndiff space/w error w1=le l1=we'
    text = data.decode()
    if text.count(before) != 2:
        raise ValueError('Both native HBT style definitions required')
    return text.replace(before, before + ' n1=Nx').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with args.output.open('xb') as stream:
        stream.write(patch(args.source.read_bytes()))


if __name__ == '__main__':
    main()
