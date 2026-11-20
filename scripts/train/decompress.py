"""Decompress the w4a16 compressed-tensors checkpoint to plain bf16 on CPU (one-off, for LoRA training only)."""
import sys,time,torch
from pathlib import Path
from transformers import AutoModelForCausalLM,AutoTokenizer,CompressedTensorsConfig
src=Path(sys.argv[1]);dst=Path(sys.argv[2]);t=time.time()
m=AutoModelForCausalLM.from_pretrained(src,device_map='cpu',dtype=torch.bfloat16,quantization_config=CompressedTensorsConfig(run_compressed=False))
print('loaded',type(m).__name__,round(time.time()-t),'s',flush=True)
m.save_pretrained(dst,safe_serialization=True,max_shard_size='4GB');AutoTokenizer.from_pretrained(src).save_pretrained(dst)
print('saved',dst,round(time.time()-t),'s')
