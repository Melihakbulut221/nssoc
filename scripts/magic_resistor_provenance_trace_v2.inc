#pragma GCC diagnostic push
#pragma GCC diagnostic error "-Wformat"
/* NSSOC resistor provenance v2. Diagnostic only; numerical objects are read-only.
 * Inserted into qualified ResPrint.c. No resistor struct/ABI change.
 * Names are hex-encoded original bytes. Object addresses are process-local
 * observation keys, NEVER stable identities or proof of physical ownership.
 */
#include <stdlib.h>
#include <errno.h>

static FILE *mrpFile = NULL;
static int mrpState = 0; /* 0 unchecked, 1 active, 2 disabled, -1 failed */
static unsigned long long mrpSeq = 0, mrpEpoch = 0;
static int mrpInNet = 0;

static void mrpFailure(const char *where)
{
    int saved = errno;
    mrpState = -1;
    TxError("NSSOC_RESISTOR_TRACE_ERROR %s errno=%d\n", where, saved);
}
static void mrpHex(const char *value)
{
    const unsigned char *p;
    if (value == NULL) { fputs("null", mrpFile); return; }
    fputc('"', mrpFile);
    for (p = (const unsigned char *)value; *p; p++)
        fprintf(mrpFile, "%02x", (unsigned int)*p);
    fputc('"', mrpFile);
}
static void mrpFinish(void)
{
    fputs("}\n", mrpFile);
    if (ferror(mrpFile) || fflush(mrpFile) != 0)
        mrpFailure("write_or_flush");
}
static void mrpClose(void)
{
    if (mrpFile == NULL) return;
    if (mrpState == 1)
    {
        fprintf(mrpFile, "{\"schema\":1,\"event\":\"trace_end\","
                "\"records_before_footer\":%llu,\"epochs\":%llu,"
                "\"net_still_open\":%s,\"physical_ownership_proved\":false",
                mrpSeq, mrpEpoch, mrpInNet ? "true" : "false");
        mrpFinish();
    }
    if (fclose(mrpFile) != 0) mrpFailure("close");
    mrpFile = NULL;
}
static int mrpReady(void)
{
    const char *path;
    if (mrpState != 0) return mrpState == 1;
    path = getenv("NSSOC_MAGIC_RESISTOR_TRACE");
    if (path == NULL || *path == '\0') { mrpState = 2; return 0; }
    /* Linux/glibc exclusive creation: never truncate an earlier trace. */
    mrpFile = fopen(path, "wx");
    if (mrpFile == NULL) { mrpFailure("exclusive_open"); return 0; }
    mrpState = 1;
    if (atexit(mrpClose) != 0) { mrpFailure("atexit"); return 0; }
    fputs("{\"schema\":1,\"event\":\"trace_start\","
          "\"magic_upstream\":\"fd12c39c37f26a0fe6e04698b1011e31b8bd3229\","
          "\"instrumentation\":\"nssoc_resistor_provenance_v2\","
          "\"names\":\"hex_original_bytes\","
          "\"pointer_scope\":\"this_process_ordered_creation_epoch_only\","
          "\"resistor_footprint_is_not_inferred\":true", mrpFile);
    mrpFinish();
    return mrpState == 1;
}
static int mrpStart(const char *event)
{
    if (!mrpReady()) return 0;
    fprintf(mrpFile, "{\"schema\":1,\"seq\":%llu,\"epoch\":%llu,"
            "\"event\":\"%s\"", ++mrpSeq, mrpEpoch, event);
    return 1;
}
static void mrpRect(const Rect *rect)
{
    if (rect == NULL) { fputs("null", mrpFile); return; }
    fprintf(mrpFile, "[%d,%d,%d,%d]", rect->r_xbot, rect->r_ybot,
            rect->r_xtop, rect->r_ytop);
}
static void mrpTile(const Tile *tile)
{
    if (tile == NULL) { fputs("null", mrpFile); return; }
    fprintf(mrpFile, "{\"bbox\":[%d,%d,%d,%d],"
            "\"exact_type\":%u,\"split\":%s,\"split_direction\":%d,"
            "\"left_type\":%u,\"right_type\":%u}",
            LEFT(tile), BOTTOM(tile), RIGHT(tile), TOP(tile),
            (unsigned int)TiGetTypeExact(tile),
            IsSplit(tile) ? "true" : "false", SplitDirection(tile),
            (unsigned int)TiGetLeftType(tile), (unsigned int)TiGetRightType(tile));
}
static void mrpNode(const resNode *node)
{
    if (node == NULL) { fputs("null", mrpFile); return; }
    fprintf(mrpFile, "{\"address\":\"%p\",\"xy\":[%d,%d],"
            "\"status\":%d,\"why\":%u,\"name_hex\":",
            (const void *)node, node->rn_loc.p_x, node->rn_loc.p_y,
            node->rn_status, node->rn_why);
    mrpHex(node->rn_name);
    fputc('}', mrpFile);
}
static void mrpResistor(const resResistor *resistor)
{
    int valid = resistor->rr_tt >= 0 && resistor->rr_tt < DBNumTypes;
    fprintf(mrpFile, ",\"resistor_address\":\"%p\","
            "\"rr_value_milliohms_hex\":\"%a\",\"rr_status\":%d,"
            "\"rr_tt\":%d,\"rr_width_raw\":%d,\"rr_cl_raw\":%d,"
            "\"type_index_valid\":%s,\"material_name_hex\":",
            (const void *)resistor, (double)resistor->rr_value,
            resistor->rr_status, (int)resistor->rr_tt,
            resistor->rr_width, resistor->rr_cl, valid ? "true" : "false");
    mrpHex(valid ? DBTypeLongNameTbl[resistor->rr_tt] : NULL);
    if (valid)
        fprintf(mrpFile, ",\"is_contact\":%s,\"sheet_resist_raw_hex\":\"%a\","
                "\"via_resist_raw\":%d",
                DBIsContact(resistor->rr_tt) ? "true" : "false",
                (double)ExtCurStyle->exts_sheetResist[resistor->rr_tt],
                (int)ExtCurStyle->exts_viaResist[resistor->rr_tt]);
    fprintf(mrpFile, ",\"resist_scale\":%d,\"node1\":",
            ExtCurStyle->exts_resistScale);
    mrpNode(resistor->rr_node[0]);
    fputs(",\"node2\":", mrpFile);
    mrpNode(resistor->rr_node[1]);
}
void ResPhysicalTraceBegin(const char *net, const char *cell)
{
    if (!mrpReady()) return;
    if (mrpInNet) { mrpFailure("nested_net"); return; }
    mrpEpoch++;
    mrpInNet = 1;
    if (!mrpStart("net_begin")) return;
    fputs(",\"net_name_hex\":", mrpFile); mrpHex(net);
    fputs(",\"cell_argument_hex\":", mrpFile); mrpHex(cell);
    fprintf(mrpFile, ",\"options\":%d,\"cif_output_um_per_internal_hex\":\"%a\","
            "\"resist_scale\":%d,\"physical_ownership_proved\":false",
            ResOptionsFlags, (double)CIFGetOutputScale(1000),
            ExtCurStyle->exts_resistScale);
    mrpFinish();
}
void ResPhysicalTraceEnd(void)
{
    if (!mrpReady() || !mrpInNet) return;
    if (mrpStart("net_end")) mrpFinish();
    mrpInNet = 0;
}
void ResPhysicalTraceTile(const resResistor *resistor, const Tile *tile,
                         const Breakpoint *first, const Breakpoint *second,
                         const char *axis)
{
    if (!mrpStart("create_tile")) return;
    mrpResistor(resistor);
    fprintf(mrpFile, ",\"constructor_axis\":\"%s\",\"tile\":", axis);
    mrpTile(tile);
    fprintf(mrpFile, ",\"break1_xy\":[%d,%d],\"break2_xy\":[%d,%d],"
            "\"break1_contact_rect\":", first->br_loc.p_x, first->br_loc.p_y,
            second->br_loc.p_x, second->br_loc.p_y);
    mrpRect(first->br_crect);
    fputs(",\"break2_contact_rect\":", mrpFile); mrpRect(second->br_crect);
    fputs(",\"geometry_semantics\":\"creation_tile_and_break_interval_only\","
          "\"final_footprint_proved\":false", mrpFile);
    mrpFinish();
}
void ResPhysicalTraceContact(const resResistor *resistor,
                            const ResContactPoint *contact, int index,
                            int minside, int viawidth_current, int spacing,
                            int border, int cscale, int squaresx, int squaresy)
{
    if (!mrpStart("create_contact")) return;
    mrpResistor(resistor);
    fprintf(mrpFile, ",\"contact_type\":%d,\"contact_center\":[%d,%d],"
            "\"contact_width_raw\":%d,\"contact_height_raw\":%d,"
            "\"contact_layers\":%d,\"layer_pair_index\":%d,\"contact_rect\":",
            (int)contact->cp_type, contact->cp_center.p_x,
            contact->cp_center.p_y, contact->cp_width, contact->cp_height,
            contact->cp_currentcontact, index);
    mrpRect(&contact->cp_rect);
    fputs(",\"lower_constructor_tile\":", mrpFile);
    mrpTile(contact->cp_tile[index - 1]);
    fputs(",\"upper_constructor_tile\":", mrpFile);
    mrpTile(contact->cp_tile[index]);
    fprintf(mrpFile, ",\"minside\":%d,\"viawidth_current\":%d,"
            "\"spacing\":%d,\"border\":%d,\"cif_scale_factor\":%d,"
            "\"squares_x\":%d,\"squares_y\":%d,"
            "\"geometry_semantics\":\"contact_region_not_individual_cut_polygons\","
            "\"final_footprint_proved\":false",
            minside, viawidth_current, spacing, border, cscale, squaresx, squaresy);
    mrpFinish();
}
void ResPhysicalTraceSnapshot(const char *phase, const resResistor *list)
{
    unsigned long long count = 0;
    const resResistor *resistor;
    if (!mrpStart("snapshot_begin")) return;
    fprintf(mrpFile, ",\"phase\":\"%s\"", phase); mrpFinish();
    for (resistor = list; resistor != NULL; resistor = resistor->rr_nextResistor)
    {
        if (!mrpStart("snapshot_resistor")) return;
        fprintf(mrpFile, ",\"phase\":\"%s\",\"index\":%llu", phase, count++);
        mrpResistor(resistor);
        mrpFinish();
    }
    if (!mrpStart("snapshot_end")) return;
    fprintf(mrpFile, ",\"phase\":\"%s\",\"count\":%llu", phase, count);
    mrpFinish();
}
void ResPhysicalTraceOutput(const resResistor *resistor, const char *net)
{
    if (!mrpStart("emitted_resistor")) return;
    mrpResistor(resistor);
    fputs(",\"writer_net_hex\":", mrpFile); mrpHex(net);
    /* Reuse the exact original float expression and %g presentation.
     * Original fprintf remains untouched; this is an additional observation. */
    fprintf(mrpFile, ",\"ext_value_token\":\"%g\",\"final_footprint_proved\":false",
            resistor->rr_value / (float)ExtCurStyle->exts_resistScale);
    mrpFinish();
}
void ResPhysicalTraceOrphan(const char *first, const char *second)
{
    if (!mrpStart("emitted_orphan_zero")) return;
    fputs(",\"node1_name_hex\":", mrpFile); mrpHex(first);
    fputs(",\"node2_name_hex\":", mrpFile); mrpHex(second);
    fputs(",\"ext_value_token\":\"0.0\",\"resistor_address\":null,"
          "\"material_unknown\":true,\"final_footprint_proved\":false", mrpFile);
    mrpFinish();
}
#pragma GCC diagnostic pop
