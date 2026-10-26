"""Plot measured physical trajectories, never AMCL estimates or synthetic paths."""
import argparse,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

def main():
    p=argparse.ArgumentParser();p.add_argument('--gate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise RuntimeError('Refusing to replace a figure')
    fig,ax=plt.subplots(figsize=(8,6))
    for directory,label,color in [('01_original','Original','#2455a4'),('02_candidate','Máscara candidata','#d45725')]:
        path=a.gate/directory/'memory/physical_pose.jsonl'
        rows=[json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        xy=[(r['position'].get('x',0),r['position'].get('y',0)) for r in rows]
        x,y=zip(*xy);distance=math.hypot(x[-1]-1,y[-1]+9)
        ax.plot(x,y,color=color,label=f'{label}: error final {distance:.3f} m',linewidth=1.4)
        ax.scatter(x[-1],y[-1],color=color,marker='x',s=70,zorder=5)
    ax.add_patch(Circle((1,-9),.25,color='green',alpha=.15));ax.scatter([1],[-9],marker='*',s=110,color='green',label='Destino y tolerancia 0,25 m')
    ax.scatter([-1],[-9],marker='D',color='gray',label='Waypoint');ax.scatter([0],[-9],marker='o',color='black',label='Inicio')
    ax.set(xlabel='X física en Gazebo (m)',ylabel='Y física en Gazebo (m)',title='PARK N1: pose física independiente\nDiagnóstico posterior a E1; un par, renderizado con 2 hilos')
    ax.axis('equal');ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(a.output,dpi=170);plt.close(fig)
if __name__=='__main__':main()
