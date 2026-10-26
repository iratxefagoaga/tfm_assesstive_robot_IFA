"""Select independent pose available when the final Nav2 success was observed."""
def reference(poses,observations):
    events=[r for r in observations if r.get('kind')=='navigation_status']
    births={g['id']:g['created'] for r in events for g in r['goals']}
    if not births:return None
    latest=max(births.values());ids=[i for i,t in births.items() if t==latest]
    if len(ids)!=1:return None
    goal=ids[0]
    success=next((r for r in events if any(g['id']==goal and g['status']==4 for g in r['goals'])),None)
    if success is None:return None
    available=[p for p in poses if p['wall_monotonic']<=success['wall_monotonic']]
    if not available:return None
    pose=max(available,key=lambda p:p['wall_monotonic'])
    return {'pose':pose,'age_s':success['wall_monotonic']-pose['wall_monotonic'],'goal_id':goal,'success_wall_monotonic':success['wall_monotonic']}
