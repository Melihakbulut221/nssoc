// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
#include <stdint.h>
#include "lib/soc_hal.h"
#include "soc_reg_offsets.h"
#include "soc_eth.h"
#include "soc_timers.h"
volatile uint32_t fi_phase, fi_sig, fi_mask, fi_rounds_done;
#define rd soc_read32
#define wr soc_write32
static uint32_t mip(void) {uint32_t x;__asm__ volatile("csrr %0, mip":"=r"(x));return x;}
#define putc_ soc_uart_putc
static void hex(uint32_t value) { soc_uart_hex32(value, 0); }
int main(void) {
 static const uint32_t lengths[8]={60,61,300,511,127,512,300,300};
 uint32_t bad=0,sig=0;
 wr(SOC_UART0_BASE + SOC_UART_SCALER_OFF,0);wr(SOC_UART0_BASE + SOC_UART_CTRL_OFF,2);
 if(rd(ETH_ID)!=0x474d4901u)bad|=1;
 wr(ETH_CTRL,ETH_ENABLE);wr(ETH_IRQEN,ETH_IRQ_RX_READY);
 fi_phase=1;
 for(uint32_t f=0;f<8;f++) {
  wr(WDOG_CTRL,WDOG_W(GPT_LD));
  for(uint32_t i=0;i<lengths[f];i++) {
   uint32_t t=20000;
   while(!(rd(ETH_STATUS)&ETH_TX_READY)&&--t) {}
   if(!t){bad|=2;break;}
   wr(ETH_TX,((f*29u+i*13u+7u)&255u)|(i+1==lengths[f]?ETH_LAST:0));
  }
  uint32_t t=20000;
  while(!(rd(ETH_STATUS)&ETH_RX_READY)&&--t) {}
  if(!t){bad|=4;break;}
  if(!(mip()&(1u<<(16+SOC_IRQLINE_ETH))))bad|=8;
  for(uint32_t i=0;i<lengths[f];i++) {
   uint32_t word=rd(ETH_RX);
   uint32_t expected=ETH_RX_VALID|((f*29u+i*13u+7u)&255u)|(i+1==lengths[f]?ETH_LAST:0);
   if(word!=expected)bad|=16;
   sig+=word&255u;
  }
  if(rd(ETH_STATUS)&ETH_RX_READY)bad|=32;
  if(mip()&(1u<<(16+SOC_IRQLINE_ETH)))bad|=64;
  if(rd(ETH_EVENTS)&0x1fcu)bad|=128;
  fi_rounds_done=f+1;
 }
 fi_phase=2;fi_sig=sig;fi_mask=bad;
 putc_('S');hex(sig);putc_('M');hex(bad);putc_('\n');
 return (int)bad;
}
