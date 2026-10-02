#!/usr/bin/env python3
"""Recreate descriptive and paired statistics for protocol_20260928."""
import csv, json, math, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC=ROOT/"experiments/results/phase5/acceptance_final/navigation_results.csv"
MAN=ROOT/"experiments/results/phase5/acceptance_final/run_manifest.csv"
OUT=ROOT/"experiments/results/statistical_analysis"
PFX="protocol_20260928"; Z=1.959963984540054; T={1:12.706,2:4.303,3:3.182,4:2.776}
def rows(p):
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def wilson(x,n):
    p=x/n; d=1+Z**2/n; c=(p+Z**2/(2*n))/d; r=Z*math.sqrt((p*(1-p)+Z**2/(4*n))/n)/d; return c-r,c+r
def mean_ci(v):
    m=statistics.mean(v)
    if len(v)<2:return m,None,None
    e=T.get(len(v)-1,Z)*statistics.stdev(v)/math.sqrt(len(v)); return m,m-e,m+e
def mcnemar(b,c):
    n=b+c
    return "" if not n else f"{min(1.,2*sum(math.comb(n,i) for i in range(min(b,c)+1))/2**n):.6f}"
def main():
    data=[r for r in rows(SRC) if r["run_id"].startswith(PFX+"_")]
    manifest=[r for r in rows(MAN) if r["run_id"].startswith(PFX+"_")]
    OUT.mkdir(parents=True,exist_ok=True); result=[]
    for cond in ("MEMORY_OFF","MEMORY_ON"):
        g=[r for r in data if r["condition"]==cond]; s=sum(r["success"]=="true" for r in g); lo,hi=wilson(s,len(g))
        for metric in ("time_s","distance_m","replanning_events"):
            v=[float(r[metric]) for r in g if r[metric]!=""]; m,a,b=mean_ci(v)
            result.append({"condition":cond,"metric":metric,"n_recorded":len(v),"mean":f"{m:.6f}","median":f"{statistics.median(v):.6f}","sample_sd":f"{statistics.stdev(v):.6f}" if len(v)>1 else "","mean_ci95_low":"" if a is None else f"{a:.6f}","mean_ci95_high":"" if b is None else f"{b:.6f}","successes":s,"success_n":len(g),"success_rate":f"{s/len(g):.6f}","success_wilson95_low":f"{lo:.6f}","success_wilson95_high":f"{hi:.6f}"})
    pairs={}
    for r in data:pairs.setdefault(r["run_id"],{})[r["condition"]]=r
    full=[p for p in pairs.values() if len(p)==2]
    b=sum(p["MEMORY_OFF"]["success"]=="true" and p["MEMORY_ON"]["success"]!="true" for p in full); c=sum(p["MEMORY_ON"]["success"]=="true" and p["MEMORY_OFF"]["success"]!="true" for p in full)
    paired=[{"complete_pairs":len(full),"off_success_on_failure":b,"off_failure_on_success":c,"mcnemar_exact_two_sided_p":mcnemar(b,c),"missing_memory_on_records":sum(r["condition"]=="memory_on" and r["observed_nav2_status"]=="NO_RESULT" for r in manifest),"quantitative_paired_tests":"not_run: only one pair has success=true in both conditions"}]
    for name,dataout in (("descriptive_statistics.csv",result),("paired_success.csv",paired)):
        with (OUT/name).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=dataout[0]);w.writeheader();w.writerows(dataout)
    (OUT/"analysis_metadata.json").write_text(json.dumps({"source":str(SRC),"run_prefix":PFX,"rows_analyzed":len(data),"manifest_rows_analyzed":len(manifest),"outlier_policy":"No observations removed."},indent=2),encoding="utf-8")
if __name__=="__main__":main()
