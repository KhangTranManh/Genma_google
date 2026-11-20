"""QLoRA SFT for Gemma-4 12B on the gold-patch edit dataset (loss on the completion only).
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True .venv-train/bin/python scripts/train/train_lora.py \
      --data data/train_v1/train.jsonl --out runs/train/lora_v1 [--epochs 1 --max-steps N]
Writes a PEFT adapter (vLLM-loadable) plus train/eval loss logs. Held-out split is by task.
"""
import argparse,json,math,random,time,torch
from pathlib import Path
from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig
from peft import LoraConfig,get_peft_model
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--epochs',type=float,default=1)
p.add_argument('--max-steps',type=int,default=0);p.add_argument('--lr',type=float,default=1e-4);p.add_argument('--accum',type=int,default=8);p.add_argument('--max-len',type=int,default=8192)
p.add_argument('--rank',type=int,default=16);p.add_argument('--eval-frac',type=float,default=0.05);p.add_argument('--seed',type=int,default=0);a=p.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);random.seed(a.seed);torch.manual_seed(a.seed)
M='models/gemma-4-12b-bf16-train';tok=AutoTokenizer.from_pretrained(M)
rows=[json.loads(l) for l in open(a.data)];rows=[r for r in rows if r['n_prompt']+r['n_completion']<=a.max_len]
tasks=sorted({r['task'] for r in rows});random.shuffle(tasks);n_eval=max(1,int(len(tasks)*a.eval_frac));ev_tasks=set(tasks[:n_eval])
train=[r for r in rows if r['task'] not in ev_tasks];evals=[r for r in rows if r['task'] in ev_tasks];random.shuffle(train)


def encode(r):
    pi=tok(r['prompt'],add_special_tokens=False).input_ids;ci=tok(r['completion'],add_special_tokens=False).input_ids
    return torch.tensor([pi+ci]),len(pi)


model=AutoModelForCausalLM.from_pretrained(M,device_map='auto',dtype=torch.bfloat16,max_memory={0:'9GiB',1:'12GiB'},attn_implementation='sdpa',
    quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True))
model.config.use_cache=False;model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False});model.enable_input_require_grads()
model=get_peft_model(model,LoraConfig(r=a.rank,lora_alpha=2*a.rank,lora_dropout=0.05,target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],task_type='CAUSAL_LM'))
params=[q for q in model.parameters() if q.requires_grad];opt=torch.optim.AdamW(params,lr=a.lr,weight_decay=0.0)
total=math.ceil(len(train)*a.epochs/a.accum);total=min(total,a.max_steps) if a.max_steps else total;warm=max(1,total//20)
sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda s:min(1,(s+1)/warm)*max(0.05,0.5*(1+math.cos(math.pi*min(1,s/max(1,total))))))


def loss_of(r):
    ids,np_=encode(r);ids=ids.to('cuda:0');K=ids.shape[1]-np_
    logits=model(input_ids=ids,logits_to_keep=K+1).logits[0,:-1].float()
    return torch.nn.functional.cross_entropy(logits,ids[0,-K:])


def evaluate():
    model.eval();ls=[]
    with torch.no_grad():
        for r in evals:ls.append(loss_of(r).item())
    model.train();return sum(ls)/len(ls)


log=open(out/'log.jsonl','a');meta={'train_examples':len(train),'eval_examples':len(evals),'eval_tasks':sorted(ev_tasks),'steps':total,'args':vars(a)}
(out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:meta[k] for k in ['train_examples','eval_examples','steps']}),flush=True)
model.train();e0=evaluate();log.write(json.dumps({'step':0,'eval_loss':e0})+'\n');log.flush();print('step 0 eval',round(e0,4),flush=True)
step=0;i=0;t0=time.time();acc=[]
while step<total:
    r=train[i%len(train)];i+=1;l=loss_of(r)/a.accum;l.backward();acc.append(l.item()*a.accum)
    if i%a.accum==0:
        torch.nn.utils.clip_grad_norm_(params,1.0);opt.step();sched.step();opt.zero_grad();step+=1
        rec={'step':step,'train_loss':sum(acc)/len(acc),'lr':sched.get_last_lr()[0],'elapsed_min':round((time.time()-t0)/60,1)};acc=[]
        if step%10==0 or step==total:rec['eval_loss']=evaluate();model.save_pretrained(out/'adapter')
        log.write(json.dumps(rec)+'\n');log.flush();print(json.dumps(rec),flush=True)
model.save_pretrained(out/'adapter');print('saved',out/'adapter',flush=True)
