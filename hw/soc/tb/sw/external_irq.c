// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
#include <stdint.h>
#include "lib/soc_hal.h"
#include "soc_reg_offsets.h"
#include "soc_gpio.h"
volatile uint32_t fi_phase,fi_sig,fi_mask,fi_rounds_done;
extern volatile uint32_t irq_marker,irq_mcause,irq_count;
#define wr soc_write32
#define rd soc_read32
static uint32_t mip(void){uint32_t x;__asm__ volatile("csrr %0,mip":"=r"(x));return x;}
static uint32_t mie(void){uint32_t x;__asm__ volatile("csrr %0,mie":"=r"(x));return x;}
static void wait_level(uint32_t high,uint32_t bit){uint32_t n=5000;while (!!(mip()&0x800u)!=high && --n){} if(!n)fi_mask|=bit;}
static void pause_(void){for(volatile uint32_t i=0;i<32;i++)__asm__ volatile("nop");}
#define putc_ soc_uart_putc
static void hex(uint32_t value) { soc_uart_hex32(value, 0); }
int main(void){
 wr(SOC_UART0_BASE + SOC_UART_SCALER_OFF,0);wr(SOC_UART0_BASE + SOC_UART_CTRL_OFF,2);wr(GPIO_DIR,15);
 __asm__ volatile("csrc mstatus,%0; csrw mie,zero"::"r"(8u):"memory");
 fi_phase=1;wr(GPIO_OUTPUT,1);wait_level(1,1);pause_();if(irq_count)fi_mask|=2;
 wr(GPIO_OUTPUT,2);wait_level(0,4);
 __asm__ volatile("csrs mstatus,%0"::"r"(8u):"memory");
 wr(GPIO_OUTPUT,3);wait_level(1,8);pause_();if(irq_count)fi_mask|=16;
 __asm__ volatile("csrs mie,%0"::"r"(0x800u):"memory");
 uint32_t n=5000;while(irq_count!=1 && --n){}pause_();
 if(!n||irq_count!=1||irq_mcause!=0x8000000bu||irq_marker!=11||(mie()&0x800u))fi_mask|=32;
 wr(GPIO_OUTPUT,4);wait_level(0,64);fi_rounds_done=1;
 __asm__ volatile("csrs mie,%0"::"r"(0x800u):"memory");
 wr(GPIO_OUTPUT,5);uint32_t saved;
 __asm__ volatile("li t0,0x13579bdf; wfi; mv %0,t0":"=r"(saved)::"t0","memory");
 if(saved!=0x13579bdfu)fi_mask|=256;
 n=5000;while(irq_count!=2 && --n){}
 if(!n||irq_count!=2||irq_mcause!=0x8000000bu||irq_marker!=11)fi_mask|=128;
 wr(GPIO_OUTPUT,6);wait_level(0,512);fi_rounds_done=2;
 __asm__ volatile("csrc mstatus,%0; csrs mie,%1"::"r"(8u),"r"(0x800u):"memory");
 wr(GPIO_OUTPUT,7);__asm__ volatile("wfi":::"memory");
 wait_level(1,1024);if(irq_count!=2)fi_mask|=2048;
 wr(GPIO_OUTPUT,8);wait_level(0,4096);__asm__ volatile("csrw mie,zero":::"memory");
 fi_rounds_done=3;fi_phase=2;fi_sig=0xe1700000u|irq_count;
 putc_('S');hex(fi_sig);putc_('M');hex(fi_mask);putc_('\n');return (int)fi_mask;
}
