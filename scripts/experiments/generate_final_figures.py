"""Regenerate descriptive closure tables/figures into a fresh directory.

Requires matplotlib; does not recompute inferential statistics or access ROS/DB.
"""
from pathlib import Path
import argparse
import csv
import json
from scripts.experiments.verify_final_results import verify, ROOT

def read(path):
    return path.read_text(encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify()
    inputs = ROOT/"experiments/results/final"
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    obs=json.loads(read(inputs/"E1/final_selected_observations.json"));assert len(obs)==40
    rows=[]
    for scenario in ["home","park"]:
     for c in ["N0","N1"]:
      g=[r for r in obs if r["scenario"]==scenario and r["memory_condition"]==c];assert len(g)==10
      ev=[r for r in g if r.get("context_compliance") in (0,1,True,False)]
      rows.append(dict(scenario=scenario,condition=c,n=10,success=sum(r["success"] in (1,True) for r in g),
       compliance_evaluable=len(ev),compliant=sum(r["context_compliance"] in (1,True) for r in ev),
       compliance_NA=10-len(ev),mean_time_s=sum(float(r["navigation_time_s"]) for r in g)/10,
       mean_distance_m=sum(float(r["distance_m"]) for r in g)/10))
    with (out/"navigation_summary.csv").open("w",encoding="utf-8",newline="") as f:
     w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(9,4),layout="constrained");labels=[r["scenario"].upper()+" "+r["condition"] for r in rows]
    ax[0].bar(labels,[r["success"] for r in rows],color=["#777","#2878b5"]*2);ax[0].set(title="Llegada al destino",ylabel="Ejecuciones (de 10)",ylim=(0,11))
    x=range(4)
    ax[1].bar(x,[r["compliant"] for r in rows],label="Cumple",color="#2878b5")
    ax[1].bar(x,[r["compliance_evaluable"]-r["compliant"] for r in rows],bottom=[r["compliant"] for r in rows],label="No cumple",color="#777")
    ax[1].bar(x,[r["compliance_NA"] for r in rows],bottom=[r["compliance_evaluable"] for r in rows],label="N/A",color="#ddd",hatch="//")
    ax[1].set(title="Coherencia con estrategia oeste",ylabel="Ejecuciones (de 10)",ylim=(0,11),xticks=list(x),xticklabels=labels);ax[1].legend(fontsize=8)
    for ext in ["png","pdf"]:fig.savefig(out/f"E1_success_and_coverage.{ext}",dpi=200)
    plt.close(fig)
    s2=json.loads(read(inputs/"E2/summary.json"))[0];s3=json.loads(read(inputs/"E3/summary.json"))[0]
    fig,ax=plt.subplots(1,2,figsize=(8,4),layout="constrained")
    ax[0].bar(["R0","R1"],[s2[c]["recall_at_3"] for c in ["R0","R1"]],color=["#777","#2878b5"]);ax[0].set(title="E2: Recall@3 (20 consultas)",ylabel="Media",ylim=(0,1))
    ax[1].bar(["P0","P1"],[s3[c]["strategy_accuracy"] for c in ["P0","P1"]],color=["#777","#2878b5"]);ax[1].set(title="E3: exactitud (8 casos primarios)",ylabel="Proporción",ylim=(0,1.1))
    for ext in ["png","pdf"]:fig.savefig(out/f"E2_E3_primary.{ext}",dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
