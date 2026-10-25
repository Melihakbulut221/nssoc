/* SPDX-License-Identifier: Apache-2.0
 * Harmless owned GDB compatibility fixture; no NSSOC design or native route. */
#define _GNU_SOURCE
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/prctl.h>
#include <unistd.h>
_Atomic unsigned long fixture_counter = 7;
__attribute__((noinline)) void fixture_noop(void) { __asm__ __volatile__("" ::: "memory"); }
__attribute__((noinline)) void *fixture_worker(void *p) {
    (void)p;
    for (;;) { atomic_fetch_add(&fixture_counter, 1); usleep(1000); }
    return NULL;
}
int main(void) {
    if (prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0)) return 2;
    pthread_t threads[3];
    for (int i=0;i<3;i++) if (pthread_create(&threads[i],NULL,fixture_worker,NULL)) return 3;
    setvbuf(stdout,NULL,_IOLBF,0);
    for (;;) { printf("%lu\n",atomic_load(&fixture_counter)); usleep(100000); }
}
