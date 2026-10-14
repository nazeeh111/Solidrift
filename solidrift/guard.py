"""Independent stdlib review; exact rational arithmetic, not a formal certificate."""
from fractions import Fraction as Q
from collections import defaultdict
import math


def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def lerp(a,b,t): return tuple(x+t*(y-x) for x,y in zip(a,b))
def normal(t): return cross(sub(t[1],t[0]),sub(t[2],t[0]))
def sign(x): return (x>0)-(x<0)
def projected(t,n):
    axis=max(range(3),key=lambda k:abs(n[k]))
    return [tuple(p[k] for k in range(3) if k!=axis) for p in t],axis
def orient(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def in_tri(p,t,n):
    tt,axis=projected(t,n)
    pp=tuple(p[k] for k in range(3) if k!=axis)
    s=[sign(orient(a,b,pp)) for a,b in zip(tt,tt[1:]+tt[:1])]
    return all(x>=0 for x in s) or all(x<=0 for x in s)
def slice_plane(t,plane,n):
    distances=[dot(n,sub(p,plane)) for p in t]
    found={p for p,d in zip(t,distances) if d==0}
    for k in range(3):
        l=(k+1)%3
        if distances[k]*distances[l]<0:
            found.add(lerp(t[k],t[l],distances[k]/(distances[k]-distances[l])))
    return found
def coplanar_points(a,b,n):
    # Vertices plus exact edge intersections characterize intersection polygon.
    points={p for p in a if in_tri(p,b,n)} | {p for p in b if in_tri(p,a,n)}
    aa,axis=projected(a,n); bb,_=projected(b,n)
    for i in range(3):
        p,q=aa[i],aa[(i+1)%3]; u=sub(q,p)
        for j in range(3):
            r,s=bb[j],bb[(j+1)%3]; v=sub(s,r); w=sub(r,p)
            det=u[0]*v[1]-u[1]*v[0]
            if det:
                t=(w[0]*v[1]-w[1]*v[0])/det
                z=(w[0]*u[1]-w[1]*u[0])/det
                if 0<=t<=1 and 0<=z<=1: points.add(lerp(a[i],a[(i+1)%3],t))
            # Collinear endpoints already handled by in_tri.
    return points
def tri_intersection(a,b):
    na,nb=normal(a),normal(b)
    if not any(na) or not any(nb): return None, 'degenerate'
    da=[dot(na,sub(p,a[0])) for p in b]
    db=[dot(nb,sub(p,b[0])) for p in a]
    if (all(d>0 for d in da) or all(d<0 for d in da) or
        all(d>0 for d in db) or all(d<0 for d in db)): return set(),'separate'
    if all(d==0 for d in da): return coplanar_points(a,b,na),'coplanar'
    direction=cross(na,nb)
    if not any(direction): return set(),'parallel'
    axis=max(range(3),key=lambda k:abs(direction[k]))
    sa=sorted(slice_plane(a,b[0],nb),key=lambda p:p[axis])
    sb=sorted(slice_plane(b,a[0],na),key=lambda p:p[axis])
    if not sa or not sb:return set(),'separate'
    lo=max(sa[0],sb[0],key=lambda p:p[axis]); hi=min(sa[-1],sb[-1],key=lambda p:p[axis])
    return ({lo,hi} if lo[axis]<=hi[axis] else set()),'transverse'
def on_allowed(p,shared):
    if p in shared:return True
    if len(shared)!=2:return False
    a,b=shared; d=sub(b,a)
    if not any(d):return False
    if any(cross(sub(p,a),d)):return False
    k=next(k for k in range(3) if d[k])
    t=(p[k]-a[k])/d[k]
    return 0<=t<=1

def inspect(vertices,faces):
    vv=[tuple(Q(x) for x in p) for p in vertices]
    tt=[[vv[i] for i in f] for f in faces]
    edges=defaultdict(list); links=defaultdict(list)
    for fi,f in enumerate(faces):
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))].append((a,b,fi))
        for v in f:links[v].append(tuple(x for x in f if x!=v))
    bad_edges=[e for e,x in edges.items() if len(x)!=2 or x[0][0:2]!=x[1][1::-1]]
    bad_links=[]
    for v,link in links.items():
        graph=defaultdict(list)
        for a,b in link:graph[a].append(b);graph[b].append(a)
        seen=set();pending=[next(iter(graph))]
        while pending:
            u=pending.pop()
            if u in seen:continue
            seen.add(u);pending.extend(graph[u])
        if any(len(x)!=2 for x in graph.values()) or len(seen)!=len(graph):bad_links.append(v)
    degenerate=[i for i,t in enumerate(tt) if not any(normal(t))]
    intersections=[]
    for i,a in enumerate(tt):
        if i in degenerate:continue
        for j in range(i+1,len(tt)):
            if j in degenerate:continue
            b=tt[j]
            if any(max(p[k] for p in a)<min(p[k] for p in b) or max(p[k] for p in b)<min(p[k] for p in a) for k in range(3)):continue
            points,kind=tri_intersection(a,b)
            shared=[vv[s] for s in set(faces[i])&set(faces[j])]
            illegal=[p for p in points if not on_allowed(p,shared)]
            if illegal:intersections.append(dict(pair=[i,j],kind=kind,point=[[str(x) for x in p] for p in illegal[:2]]))
    o=vv[0]
    terms=[dot(sub(t[0],o),cross(sub(t[1],o),sub(t[2],o)))/6 for t in tt]
    volume=sum(terms,Q(0))
    # Independent connected components: each oriented shell must point outward.
    adjacent=defaultdict(set)
    for e,xx in edges.items():
        for x in xx:
            for y in xx:adjacent[x[2]].add(y[2])
    seen=set();components=[]
    for i in range(len(tt)):
        if i in seen:continue
        pending=[i];comp=set()
        while pending:
            x=pending.pop()
            if x in comp:continue
            comp.add(x);pending.extend(adjacent[x]-comp)
        seen|=comp
        component_volume=sum((terms[k] for k in comp),Q(0))
        components.append(dict(faces=len(comp),signed_volume=float(component_volume),volume_exact=str(component_volume),positive_orientation=component_volume>0))
    return dict(vertex_count=len(vv),face_count=len(tt),edge_count=len(edges),bad_edges=bad_edges,
                bad_links=bad_links,degenerate=degenerate,intersections=intersections,
                signed_volume=float(volume),volume_exact=str(volume),components=components,
                bbox=[[float(min(p[k] for p in vv)),float(max(p[k] for p in vv))] for k in range(3)])

def check_exact(vertices,faces):
    """Fail-closed gate for one connected shell, using exact stored numbers.

    Floats become Fraction(float), preserving their actual binary coordinate,
    not a rounded display string. This gate deliberately refuses
    disconnected shells, unused vertices and duplicate triangles. It does not
    classify nested shells/cavities or certify its own implementation formally.
    """
    reasons=[]
    if not vertices or not faces:return {'valid':False,'reasons':['empty mesh']}
    if not all(len(p)==3 and all(type(x) in (int,float,Q) and (type(x)!=float or math.isfinite(x)) for x in p) for p in vertices):
        return {'valid':False,'reasons':['coordinates must be finite numeric triples']}
    if not all(len(f)==3 and len(set(f))==3 and all(type(i)==int and 0<=i<len(vertices) for i in f) for f in faces):
        return {'valid':False,'reasons':['faces must contain three distinct in-range integer indices']}
    used={i for f in faces for i in f}
    if len(used)!=len(vertices):reasons.append('unused vertices refused')
    if len({tuple(sorted(f)) for f in faces})!=len(faces):reasons.append('duplicate triangles refused')
    result=inspect(vertices,faces)
    if result['bad_edges']:reasons.append('edge incidence/orientation failed')
    if result['bad_links']:reasons.append('vertex link failed')
    if result['degenerate']:reasons.append('exact zero-area triangles')
    if result['intersections']:reasons.append('prohibited geometric triangle contacts/intersections')
    if len(result['components'])!=1:reasons.append('single connected shell required; disconnected shell containment not certified')
    if not all(c['positive_orientation'] for c in result['components']):reasons.append('nonpositive component volume/orientation')
    result.update(valid=not reasons,reasons=reasons,prohibited_pairs=[x['pair'] for x in result['intersections']],coordinate_interpretation='exact Fraction(number), including exact binary values for floats')
    return result
