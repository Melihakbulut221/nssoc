#include <vpi_user.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
struct group { const char *name; uint64_t signals, changes; };
static struct group groups[]={{"candidate.framer"},{"reference.framer"},{"candidate.ingress"},{"reference.ingress"},{"other"}};
static PLI_INT32 changed(p_cb_data cb) {
    ((struct group *)cb->user_data)->changes++;
    return 0;
}
static void visit(vpiHandle scope) {
    static s_vpi_time suppress = {.type=vpiSuppressTime};
    struct group *g=&groups[4];
    const char *name=vpi_get_str(vpiFullName,scope);
    for(int i=0;i<4;i++) if(strstr(name,groups[i].name)) {g=&groups[i];break;}
    const int types[]={vpiNet,vpiReg,vpiModule,vpiGenScope};
    for(int i=0;i<4;i++) {
        vpiHandle it=vpi_iterate(types[i],scope), obj;
        if(!it) continue;
        while((obj=vpi_scan(it))) {
            if(i>=2) {visit(obj);continue;}
            s_cb_data cb={.reason=cbValueChange,.cb_rtn=changed,.obj=obj,.time=&suppress,.user_data=(PLI_BYTE8*)g};
            if(vpi_register_cb(&cb)) g->signals++;
        }
    }
}
static PLI_INT32 start(p_cb_data cb) {
    vpiHandle it=vpi_iterate(vpiModule,NULL), mod;
    if(it) while((mod=vpi_scan(it))) visit(mod);
    return 0;
}
static PLI_INT32 end(p_cb_data cb) {
    for(int i=0;i<5;i++) vpi_printf("SCOPE_ACTIVITY %s %llu %llu\n",groups[i].name,(unsigned long long)groups[i].signals,(unsigned long long)groups[i].changes);
    return 0;
}
static void install(void) {
    s_cb_data a={.reason=cbStartOfSimulation,.cb_rtn=start}, b={.reason=cbEndOfSimulation,.cb_rtn=end};
    vpi_register_cb(&a);vpi_register_cb(&b);
}
void (*vlog_startup_routines[])(void)={install,0};
