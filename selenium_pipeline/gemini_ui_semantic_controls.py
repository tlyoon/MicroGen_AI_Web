"""One atomic owned-tab snapshot of active Gemini menus.

Open Shadow DOM, tag name, model-version text, CSS classes, material menu
wrappers and option ordering are unstable. Discover the *accessible
semantics* of an individual visible selectable option, not global page text.

No mutation, page secrets, editor text, screenshot, remote model call,
navigation, modal opening, prompt or Send occurs here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Option:
    element: object
    label: str
    selected: bool
    disabled: bool


_SCRIPT=r"""
const selectors=[
 '[role="menuitemradio"]','[role="radio"]','[role="option"]',
 '[role="menuitemcheckbox"]','[role="menuitem"]',
 'gem-menu-item','[aria-checked]','[aria-selected]',
 '[data-test-id*="mode-option"]','[data-test-id*="model-option"]',
 '[data-test-id*="thinking"]','[data-test-id*="reasoning"]',
 '[aria-label*="thinking" i]','[aria-label*="reasoning" i]',
 '[aria-label*="effort" i]'
];
const nodes=new Set();
const roots=[document];
for(let i=0;i<roots.length && i<75;i++){
 const root=roots[i];
 for(const selector of selectors){
  try{for(const el of root.querySelectorAll(selector))nodes.add(el);}
  catch(e){}
 }
 for(const el of root.querySelectorAll('*')){
  if(el.shadowRoot && roots.length<75)roots.push(el.shadowRoot);
 }
}
function visible(node){
 let p=node;
 for(let n=0;n<20 && p;n++){
  const r=p.getBoundingClientRect();
  if(!r || r.width<=0 || r.height<=0)return false;
  const s=getComputedStyle(p);
  if(s.display==='none'||s.visibility==='hidden'||
     Number(s.opacity)<=0.01)return false;
  p=p.parentElement || (p.getRootNode().host||null);
 }
 return true;
}
const choices=[];
for(const n of nodes){
 if(!visible(n))continue;
 const role=(n.getAttribute('role')||'').toLowerCase();
 const test=(n.getAttribute('data-test-id')||'').toLowerCase();
 const aria=(n.getAttribute('aria-label')||'').toLowerCase();
 if(!['menuitemradio','radio','option','menuitemcheckbox','menuitem'].includes(role)
     && !test.includes('model')&&!test.includes('mode')
     && !test.includes('thinking')&&!test.includes('reasoning')
     && !((role==='button'||n.tagName.toLowerCase()==='button')
            && /(thinking|reasoning|effort)/.test(aria)))continue;
 const text=(n.innerText||'').trim();
 const accessible=(n.getAttribute('aria-label')||'').trim();
 const title=(n.getAttribute('title')||'').trim();
 const label=(text||accessible||title);
 if(!label || label.length>230)continue;
 // Reject a container containing nested actionable options: it can
 // list Flash-Lite + Flash + Pro and must never be clicked as one option.
 let nested=false;
 for(const child of n.querySelectorAll(
  '[role="menuitemradio"],[role="radio"],[role="option"]')){
  if(child!==n && visible(child)) {nested=true;break;}
 }
 if(nested)continue;
 const checked=((n.getAttribute('aria-checked')||'').toLowerCase()==='true'
    ||(n.getAttribute('aria-selected')||'').toLowerCase()==='true');
 choices.push({
   element:n,label:selectedText(label,accessible,title),
   selected:checked,
   disabled:(n.getAttribute('aria-disabled')||'').toLowerCase()==='true'
     || n.disabled===true
 });
}
function selectedText(primary,accessible,title){
 return [primary,accessible,title].filter(Boolean).join('\n').slice(0,230);
}
return choices.slice(0,120);
"""


def snapshot_options(driver) -> list[Option] | None:
    """Return None only when test/driver JS snapshot is unsupported.

    In a real Chrome DOM a genuinely empty array is trustworthy as empty
    *right now*, and caller may wait for Angular hydration before Send.
    """
    try:
        raw=driver.execute_script(_SCRIPT)
    except (AttributeError, AssertionError, NotImplementedError):
        return None
    if not isinstance(raw,list):
        return None
    result=[]
    for value in raw:
        if not isinstance(value,dict):
            continue
        label=value.get("label")
        element=value.get("element")
        if (not isinstance(label,str) or not 1<=len(label)<=230
            or element is None or value.get("selected") not in (True,False)
            or value.get("disabled") not in (True,False)):
            continue
        result.append(Option(element,label,value["selected"],value["disabled"]))
    return result
