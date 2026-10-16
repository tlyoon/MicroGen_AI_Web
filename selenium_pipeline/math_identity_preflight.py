"""Sandboxed numerical identity checks for authored mathematical examples.

A numerical derivative agreement on selected domain points is a regression
check, NOT a formal proof or source correspondence. No eval, exec, SymPy,
network, TTS or generated rewriting of math formulas.
"""
from __future__ import annotations
import argparse,ast,hashlib,json,math,operator
from pathlib import Path

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
     ast.Div:operator.truediv,ast.Pow:operator.pow}
FNS={"sqrt":math.sqrt,"log":math.log,"asin":math.asin,"asinh":math.asinh,
     "atan":math.atan,"sin":math.sin,"cos":math.cos,"tan":math.tan,
     "exp":math.exp,"abs":abs}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1048576),b""):h.update(c)
    return h.hexdigest()

def numeric(expr:str,values:dict)->float:
    if not isinstance(expr,str) or len(expr)>500:raise ValueError("Unsafe math expression")
    tree=ast.parse(expr,mode="eval")
    def visit(node,depth=0):
        if depth>32:raise ValueError("Math formula too complex")
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            if abs(node.value)>1e6:raise ValueError("Unsafe large numeric literal")
            return float(node.value)
        if isinstance(node,ast.Name):
            if node.id=="pi":return math.pi
            if node.id in values and type(values[node.id]) in (float,int):
                return float(values[node.id])
            raise ValueError("Unknown or untrusted symbol")
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            val=visit(node.operand,depth+1)
            return val if isinstance(node.op,ast.UAdd) else -val
        if isinstance(node,ast.BinOp) and type(node.op) in OPS:
            left,right=visit(node.left,depth+1),visit(node.right,depth+1)
            if isinstance(node.op,ast.Pow) and abs(right)>8:
                raise ValueError("Exponent exceeds bounded numerical range")
            return OPS[type(node.op)](left,right)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            if node.func.id in FNS and not node.keywords and len(node.args)==1:
                return float(FNS[node.func.id](visit(node.args[0],depth+1)))
        raise ValueError("Unapproved math expression structure")
    result=visit(tree.body)
    if not math.isfinite(result):raise ValueError("Nonfinite mathematical expression")
    return result

def verify(manifest:Path,source:Path,slides:Path)->dict:
    inp=json.loads(manifest.read_text(encoding="utf8"))
    if (inp.get("schema_version")!=1
       or inp.get("status")!="review_only_explicit_formula_checks"
       or inp.get("source_sha256")!=digest(source)
       or inp.get("slides_sha256")!=digest(slides)):
        raise ValueError("Stale or unapproved mathematical verification manifest")
    items=inp.get("checks")
    if not isinstance(items,list) or not 1<=len(items)<=100:
        raise ValueError("Invalid formula verification batch")
    audits=[]
    for item in items:
        name=item["name"]
        points=item["points"]
        constants=item.get("constants",{})
        if (not isinstance(points,list) or not 2<=len(points)<=30
            or any(type(x) not in (int,float) or abs(x)>1e4 for x in points)
            or not isinstance(constants,dict)):
            raise ValueError("Invalid check points or constants")
        errors=[]
        for x in points:
            bindings={"x":float(x),**constants}
            h=1e-5*max(1.0,abs(float(x)))
            try:
                d=(numeric(item["antiderivative"],{**bindings,"x":float(x)+h})
                   -numeric(item["antiderivative"],{**bindings,"x":float(x)-h}))/(2*h)
                target=numeric(item["integrand"],bindings)
                error=abs(d-target)/max(1.0,abs(target))
                if not math.isfinite(error):raise ValueError("Nonfinite derivative discrepancy")
            except Exception as exc:
                raise ValueError(f"Cannot verify {name} near x={x}: {type(exc).__name__}") from exc
            errors.append(error)
        worst=max(errors)
        audits.append({"name":name,"sample_count":len(points),
            "max_relative_scaled_error":round(worst,9),
            "numerical_consistency":worst<=0.0001,
            "formal_proof":False})
    return {"status":"NUMERICAL_SAMPLE_CHECK_NOT_FORMAL_ACADEMIC_APPROVAL",
        "source_sha256":digest(source),"slides_sha256":digest(slides),
        "total_checks":len(audits),
        "passed":sum(x["numerical_consistency"] for x in audits),
        "failed":sum(not x["numerical_consistency"] for x in audits),
        "source_equivalence_certified":False,"human_academic_signoff":False,
        "checks":audits}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--slides",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    if a.out.exists() or not a.out.parent.is_dir():
        raise ValueError("Output path must be new")
    r=verify(a.manifest,a.source,a.slides)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(r,f,indent=2);f.write("\n")
    print(json.dumps(r,indent=2))
    if r["failed"]:raise SystemExit(2)

if __name__=="__main__":main()
