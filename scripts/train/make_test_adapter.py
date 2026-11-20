"""Create a small random-but-nonzero LoRA adapter for the 12B text model (vLLM compatibility test only)."""
import torch,sys
from transformers import AutoModelForCausalLM,BitsAndBytesConfig
from peft import LoraConfig,get_peft_model
out=sys.argv[1]
m=AutoModelForCausalLM.from_pretrained('models/gemma-4-12b-bf16-train',device_map='auto',dtype=torch.bfloat16,max_memory={0:'9GiB',1:'12GiB'},
  quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16))
m=get_peft_model(m,LoraConfig(r=16,lora_alpha=32,target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],task_type='CAUSAL_LM'))
torch.manual_seed(0)
for n,p in m.named_parameters():
    if 'lora_B' in n:p.data.normal_(0,0.02)
m.save_pretrained(out)
import json,safetensors.torch as st
keys=list(st.load_file(out+'/adapter_model.safetensors').keys());print('n_keys',len(keys));print('\n'.join(keys[:4]));print(json.load(open(out+'/adapter_config.json'))['target_modules'])
