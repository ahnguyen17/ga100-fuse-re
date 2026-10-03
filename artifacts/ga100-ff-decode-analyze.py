#!/usr/bin/env python3
"""Offline only. Decode supplied GA100 rows; no hardware access."""
import json, collections, pathlib, csv
P=pathlib.Path(__file__).resolve().parent
D=json.load(open('/home/f0ol/fuse_dump_results.json'))
R=[{int(k):v for k,v in d['main_rows'].items()} for d in D]
F=[[(r,v) for r,v in x.items() if 222<=r<=331 and v] for x in R]
E={1:16,2:53,10:2,25:1,26:2,6:6,7:1,13:2,14:1,16:3,19:2,20:1,27:9,28:4}
def decode(v,cshift,cwidth,oshift,owidth,dshift):
    return (v>>cshift)&((1<<cwidth)-1),(v>>oshift)&((1<<owidth)-1),(v>>dshift)&65535
# Non-overlapping complete partition layouts, plus truncated-offset proposal.
C=[]
for w in (5,6,7):
    C.extend([(f'low-chain-{w}',0,w,w,16-w,16),(f'mid-chain-{w}',16-w,w,0,16-w,16),(f'high-chain-{w}',32-w,w,16,16-w,0),(f'mid-high-chain-{w}',16,w,16+w,16-w,0)])
C.append(('partial-7bit-offset',0,6,6,7,16))
res=[]
for name,*args in C:
    ds=[[decode(v,*args) for _,v in f] for f in F]
    hist=collections.Counter(c for c,o,d in ds[0]); l1=sum(abs(hist[k]-E.get(k,0)) for k in set(hist)|set(E))
    h=1-l1/(sum(hist.values())+sum(E.values()))
    sets=[set((c,o) for c,o,d in x) for x in ds]; j=len(sets[0]&sets[1])/len(sets[0]|sets[1])
    # Noncircular compactness + uniqueness heuristic; not a probability.
    offsets=[o for c,o,d in ds[0]]
    p=(sum(o<=127 for o in offsets)/len(offsets)+len(sets[0])/len(ds[0]))/2
    score=100*(.4*h+.4*j+.2*p)
    res.append(dict(layout=name,fields=args,histogram=dict(hist),hist_l1=l1,H=h,J=j,P=p,score=score,shared=len(sets[0]&sets[1]),union=len(sets[0]|sets[1]),max_offsets=[max(o for c,o,d in a) for a in ds]))
res.sort(key=lambda x:-x['score']);json.dump(res,open(P/'scores.json','w'),indent=2)
print('EXTERNAL_TOTAL',sum(E.values()),'COUNTS',list(map(len,F)))
for x in res: print(x['layout'],'L1',x['hist_l1'],'HJP',*[round(x[k],5) for k in ['H','J','P']],'score',round(x['score'],3),'shared',x['shared'],x['union'],'max',x['max_offsets'])
# Best compatible with established offset [12:6]: chain [5:0], offset [15:6].
B=[[dict(card=D[i]['card'],row=r,raw=f'{v:08x}',chain=v&63,offset=(v>>6)&1023,data=v>>16) for r,v in f] for i,f in enumerate(F)]
with open(P/'instructions.csv','w') as out:
    w=csv.DictWriter(out,fieldnames=list(B[0][0]));w.writeheader();w.writerows(B[0]+B[1])
json.dump(B,open(P/'instructions.json','w'),indent=2)
M=[{(x['chain'],x['offset']):x for x in b} for b in B]
lines=['| Chain | Offset (dec) | Hynix row:data | Samsung row:data |','|---|---:|---|---|']
for k in sorted(M[0].keys()|M[1].keys()):
    cells=[f"{m[k]['row']}:{m[k]['data']:04x}" if k in m else '—' for m in M]
    lines.append(f'| {k[0]} | {k[1]} | '+ ' | '.join(cells)+' |')
(P/'decoded-map.md').write_text('\n'.join(lines)+'\n')
print('HIST',*[dict(collections.Counter(x['chain'] for x in b)) for b in B])
print('duplicate keys',*[len(b)-len(m) for b,m in zip(B,M)])
# Contiguous field matches, same location on both cards. Search individual halfword and chain concatenations.
targets=[('GPC',8,0x23,0x23),('FBP-disable',12,0x852,0x24),('FBP-defective',12,0x840,0x24),('DEVID',16,0x20c2,0x2082)]
hits=[]
for name,width,a,b in targets:
    for c,o in sorted(M[0].keys()&M[1].keys()):
        for bit in range(16):
            val=[]; valid=True
            for m in M:
                if bit+width>16 and (c,o+1) not in m:valid=False;break
                z=m[c,o]['data'] | (m.get((c,o+1),{}).get('data',0)<<16)
                val.append((z>>bit)&((1<<width)-1))
            if valid and val==[a,b]: hits.append(dict(target=name,chain=c,offset=o,bit=bit,rows=[m[c,o]['row'] for m in M]))
    for row in range(222):
        for bit in range(33-width):
            if [(r[row]>>bit)&((1<<width)-1) for r in R]==[a,b]:hits.append(dict(target=name,row=row,bit=bit))
print('FIELD_MATCHES',json.dumps(hits,indent=2));json.dump(hits,open(P/'field-matches.json','w'),indent=2)
# Verify important exact observations.
assert R[0][287]==0x078209c2 and ((R[0][287]|512)>>6)&1023==47
assert (R[0][287]&63)==(R[0][288]&63)==2
assert [(r[26]>>16)&4095 for r in R]==[0x840,0x24]
assert [(m[2,37]['data']>>1)|((m[2,38]['data']&1)<<15) for m in M]==[0x20c2,0x2082]
print('ASSERTIONS PASSED')
