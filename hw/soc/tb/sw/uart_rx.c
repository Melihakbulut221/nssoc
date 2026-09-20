// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
// Real CPU/APB reception; GPIO is only the external peer's phase handshake.
#include <stdint.h>
#include "soc_gpio.h"
volatile uint32_t fi_phase, fi_sig, fi_mask, fi_rounds_done;
extern volatile uint32_t irq_marker, irq_mcause, irq_count;
static void wr(uint32_t a, uint32_t v) { *(volatile uint32_t *)a = v; }
static uint32_t rd(uint32_t a) { return *(volatile uint32_t *)a; }
static uint32_t mip(void) { uint32_t v; __asm__ volatile("csrr %0,mip":"=r"(v)); return v; }
static void peer(uint32_t phase) {
    wr(GPIO_OUTPUT, phase);
    uint32_t n = 5000;
    while ((rd(GPIO_DATA) & 15u) != phase && --n) {}
    if (!n) fi_mask |= 0x100u;
}
static void check(uint32_t ok, uint32_t bit) { if (!ok) fi_mask |= bit; }
static void putc_(char c) { while (!(rd(SOC_UART0_BASE+4)&4u)) {} wr(SOC_UART0_BASE,c); }
static void hex(uint32_t x) { const char *d="0123456789abcdef"; for(int n=28;n>=0;n-=4) putc_(d[(x>>n)&15]); }
int main(void) {
    wr(SOC_UART0_BASE+12, 0); wr(SOC_UART0_BASE+8, 3); wr(GPIO_DIR, 15);
    __asm__ volatile("csrc mstatus,%0; csrw mie,zero"::"r"(8u):"memory");
    fi_phase=1;
    peer(1);
    check((rd(SOC_UART0_BASE+4)&0x51u)==1 && !(mip()&0x10000u), 1);
    check(rd(SOC_UART0_BASE)==0x35 && rd(SOC_UART0_BASE)==0, 1);
    fi_rounds_done=1;

    wr(SOC_UART0_BASE+8, 7);
    __asm__ volatile("csrs mie,%0; csrs mstatus,%1"::"r"(0x10000u),"r"(8u):"memory");
    wr(GPIO_OUTPUT, 2);
    __asm__ volatile("wfi":::"memory");
    peer(2);
    uint32_t n=5000;
    while (irq_count!=1 && --n) {}
    check(n && irq_marker==16 && irq_mcause==0x80000010u, 2);
    check(rd(SOC_UART0_BASE)==0x96 && !(rd(SOC_UART0_BASE+4)&1u), 2);
    fi_rounds_done=2;

    __asm__ volatile("csrc mstatus,%0; csrw mie,zero"::"r"(8u):"memory");
    peer(3);
    check((rd(SOC_UART0_BASE+4)&0x51u)==0x11 && (mip()&0x10000u), 4);
    check(rd(SOC_UART0_BASE)==0xc3 && (mip()&0x10000u), 4);
    wr(SOC_UART0_BASE+4, 0);
    check(!(rd(SOC_UART0_BASE+4)&0x51u) && !(mip()&0x10000u), 4);
    fi_rounds_done=3;

    peer(4);
    check((rd(SOC_UART0_BASE+4)&0x51u)==0x40 && (mip()&0x10000u), 8);
    check(rd(SOC_UART0_BASE)==0, 8);
    wr(SOC_UART0_BASE+4, 0);
    check(!(mip()&0x10000u), 8);
    fi_rounds_done=4;

    wr(SOC_UART0_BASE+8, 2); peer(5);
    check(!(rd(SOC_UART0_BASE+4)&0x51u) && irq_count==1, 16);
    fi_rounds_done=5; fi_phase=2; fi_sig=0xa1170000u|irq_count;
    putc_('S'); hex(fi_sig); putc_('M'); hex(fi_mask); putc_('\n');
    return (int)fi_mask;
}
