#!/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/tools/cocotb-venv/bin/python
import os,signal,time
from pathlib import Path
body=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-tail115-connected570-tuning-20261006/finite-controls01/positive.raw').read_bytes()
with open("stream.fifo","wb",buffering=0) as f:
 left=body
 while left:
  n=f.write(left);assert n>0;left=left[n:]
