"""Independent triangle-mesh checks, without Blender/bmesh/dependencies.

Intersection checks here detect transverse segment/face intersections and strict
coplanar overlaps. Shared vertices/edges are permitted only as their own points.
Numeric tolerance is scale-relative; this is not an exact-predicate certificate.
"""
import math
from collections import defaultdict, Counter

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a): return math.sqrt(dot(a,a))

def segment_triangle(a,b,tri,eps):
    v0,v1,v2=tri
    e1,e2=sub(v1,v0),sub(v2,v0)
    direction=sub(b,a)
    h=cross(direction,e2)
    det=dot(e1,h)
    if abs(det)<=eps*max(norm(e1)*norm(e2)*norm(direction),1e-30): return None
    inv=1/det
    s=sub(a,v0); u=dot(s,h)*inv
    q=cross(s,e1); v=dot(direction,q)*inv; t=dot(e2,q)*inv
    if -eps<=u<=1+eps and -eps<=v and u+v<=1+eps and -eps<=t<=1+eps:
        return tuple(x+t*y for x,y in zip(a,direction))
    return None

def coplanar_strict(a,b,eps):
    n=cross(sub(a[1],a[0]),sub(a[2],a[0])); length=norm(n)
    if length==0: return False
    if any(abs(dot(n,sub(v,a[0])))>eps*length for v in b): return False
    axis=max(range(3),key=lambda i:abs(n[i]))
    aa=[tuple(v[i] for i in range(3) if i!=axis) for v in a]
    bb=[tuple(v[i] for i in range(3) if i!=axis) for v in b]
    # Separating-axis test in the common plane: positive overlap on every
    # triangle edge normal establishes interior overlap, not mere contact.
    for tri in (aa,bb):
        for p,q in zip(tri,tri[1:]+tri[:1]):
            normal=(-(q[1]-p[1]),q[0]-p[0]); scale=math.hypot(*normal)
            ap=[dot(v,normal) for v in aa]; bp=[dot(v,normal) for v in bb]
            if min(max(ap),max(bp))-max(min(ap),min(bp))<=eps*scale: return False
    return True

def check(vertices,faces):
    assert all(len(v)==3 and all(math.isfinite(x) for x in v) for v in vertices)
    assert all(len(f)==3 and len(set(f))==3 and all(0<=i<len(vertices) for i in f) for f in faces)
    edges=defaultdict(list); incident=defaultdict(list)
    for fi,f in enumerate(faces):
        for a,b in zip(f,f[1:]+f[:1]): edges[tuple(sorted((a,b)))].append((a,b,fi))
        for v in f: incident[v].append(fi)
    boundary=[e for e,items in edges.items() if len(items)==1]
    nonmanifold=[e for e,items in edges.items() if len(items)!=2]
    inconsistent=[e for e,items in edges.items() if len(items)==2 and items[0][:2]!=items[1][1::-1]]
    bad_links=[]
    for v,ids in incident.items():
        graph=defaultdict(set)
        for fi in ids:
            a,b=[x for x in faces[fi] if x!=v]; graph[a].add(b);graph[b].add(a)
        if any(len(n)!=2 for n in graph.values()): bad_links.append(v); continue
        seen=set(); stack=[next(iter(graph))]
        while stack:
            x=stack.pop()
            if x in seen:continue
            seen.add(x);stack.extend(graph[x]-seen)
        if len(seen)!=len(graph):bad_links.append(v)
    span=max((max(v[k] for v in vertices)-min(v[k] for v in vertices) for k in range(3)),default=1)
    eps=max(span*1e-9,1e-12)
    triangles=[[vertices[x] for x in f] for f in faces]
    degenerate=[i for i,t in enumerate(triangles) if norm(cross(sub(t[1],t[0]),sub(t[2],t[0])))<=eps*eps]
    intersections=[]
    for i,a in enumerate(triangles):
        for j in range(i+1,len(triangles)):
            b=triangles[j]
            if any(max(v[k] for v in a)<min(v[k] for v in b)-eps or max(v[k] for v in b)<min(v[k] for v in a)-eps for k in range(3)):continue
            shared=set(faces[i])&set(faces[j])
            if coplanar_strict(a,b,eps): intersections.append((i,j,'coplanar'));continue
            points=[]
            for source,target in ((a,b),(b,a)):
                for p,q in zip(source,source[1:]+source[:1]):
                    r=segment_triangle(p,q,target,1e-10)
                    if r is not None:points.append(r)
            # Ignore permitted contact along the shared topological edge/vertex.
            for p in points:
                if shared and any(norm(sub(p,vertices[s]))<=eps*8 for s in shared):continue
                if len(shared)==2:
                    u,v=(vertices[s] for s in shared);edge=sub(v,u);z=dot(sub(p,u),edge)/dot(edge,edge)
                    projected=tuple(x+z*y for x,y in zip(u,edge))
                    if -1e-9<=z<=1+1e-9 and norm(sub(p,projected))<=eps*8:continue
                intersections.append((i,j,'transverse'));break
    origin=vertices[0] if vertices else (0,0,0)
    volume=math.fsum(dot(sub(t[0],origin),cross(sub(t[1],origin),sub(t[2],origin)))/6 for t in triangles)
    return dict(vertices=len(vertices),triangles=len(faces),boundary_edges=len(boundary),nonmanifold_edges=len(nonmanifold),
                inconsistent_edges=len(inconsistent),bad_vertex_links=bad_links,degenerate_faces=degenerate,
                intersections=intersections,volume=volume,tolerance=eps,
                valid=not(boundary or nonmanifold or inconsistent or bad_links or degenerate or intersections) and volume>0)
