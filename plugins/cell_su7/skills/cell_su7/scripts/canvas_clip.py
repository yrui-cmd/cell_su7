"""Remove only a redundant full-canvas clip, with geometry bounds checked later."""
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path

def normalize_canvas_clip(root, viewbox):
    x,y,w,h=viewbox
    accepted=set()
    parents={child:parent for parent in root.iter() for child in parent}
    for node in list(root.iter()):
        if node.tag.rsplit('}',1)[-1]!='clipPath': continue
        if node.get('transform') or node.get('clipPathUnits','userSpaceOnUse')!='userSpaceOnUse' or len(node)!=1:
            raise ValueError('Unsupported clip: expand clipping before native drawing')
        shape=node[0]
        if shape.get('transform'): raise ValueError('Transformed clip requires preprocessing')
        if shape.tag.rsplit('}',1)[-1]=='rect':
            bounds=tuple(float(shape.get(k,0)) for k in ('x','y','width','height'))
            valid=bounds==(x,y,w,h) and not shape.get('rx') and not shape.get('ry')
        elif shape.tag.rsplit('}',1)[-1]=='path':
            pen=RecordingPen();parse_path(shape.get('d',''),pen)
            valid=all(op in ('moveTo','lineTo','closePath','endPath') for op,_ in pen.value)
            pts=[p for op,items in pen.value for p in items]
            area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1])))/2 if pts else 0
            valid=valid and set(pts)=={(x,y),(x+w,y),(x+w,y+h),(x,y+h)} and abs(area-w*h)<1e-6
        else: valid=False
        if not valid: raise ValueError('Only redundant full-canvas clipping can be removed automatically')
        accepted.add('url(#'+node.get('id','')+')')
        parents[node].remove(node)
    for node in root.iter():
        if node.get('clip-path'):
            if node.get('clip-path') not in accepted: raise ValueError('Unresolved clip-path')
            if any(child.tag.rsplit('}',1)[-1]=='text' for child in node.iter()):
                raise ValueError('Clipped live text requires explicit preprocessing')
            node.attrib.pop('clip-path')
    return bool(accepted)

def assert_inside_canvas(atoms, viewbox):
    x,y,w,h=viewbox
    for atom in atoms:
        if atom.get('kind')=='text':
            continue
        for path in atom.get('subpaths',[]):
            for point in path['points']:
                for key in ('a','l','r'):
                    px,py=point[key]
                    if not (x-1e-6<=px<=x+w+1e-6 and y-1e-6<=py<=y+h+1e-6):
                        raise ValueError('Geometry extends beyond removed canvas clip; preserve/expand clipping first')
