"""Feasibility: QLoRA on Gemma-4 12B (bf16 checkpoint -> nf4) on 2x A16 16GB; one fwd/bwd/step; loss on the last K tokens."""
import json,sys,time,torch
from transformers import AutoModelForCausalLM,BitsAndBytesConfig
from peft import LoraConfig,get_peft_model
seq=int(sys.argv[1]);K=int(sys.argv[2]) if len(sys.argv)>2 else 512;out={'seq':seq,'loss_tokens':K};t=time.time()
m=AutoModelForCausalLM.from_pretrained('models/gemma-4-12b-bf16-train',device_map='auto',dtype=torch.bfloat16,max_memory={0:'9GiB',1:'12GiB'},attn_implementation='sdpa',
  quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True))
out['load_s']=round(time.time()-t,1);m.config.use_cache=False
m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False});m.enable_input_require_grads()
m=get_peft_model(m,LoraConfig(r=16,lora_alpha=32,lora_dropout=0.0,target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],task_type='CAUSAL_LM'))
m.train();tr,_=m.get_nb_trainable_parameters();out['trainable_M']=round(tr/1e6,1)
opt=torch.optim.AdamW([p for p in m.parameters() if p.requires_grad],lr=1e-4)
ids=torch.randint(100,20000,(1,seq),device='cuda:0');[torch.cuda.reset_peak_memory_stats(i) for i in range(2)];times=[]
try:
    for step in range(2):
        t=time.time();o=m(input_ids=ids,logits_to_keep=K+1);loss=torch.nn.functional.cross_entropy(o.logits[0,:-1].float(),ids[0,-K:])
        loss.backward();opt.step();opt.zero_grad();torch.cuda.synchronize();times.append(round(time.time()-t,1))
    out.update(step_s=times,loss=round(loss.item(),3),ok=True)
except torch.OutOfMemoryError as e:out.update(ok=False,error='OOM')
out['peak_GiB']=[round(torch.cuda.max_memory_allocated(i)/2**30,2) for i in range(2)];print('RESULT '+json.dumps(out))
