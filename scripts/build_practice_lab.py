"""Package the actual local application and browser-driven test matrix offline."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
CASES = [('Normal travel','80','travel','AUTO-APPROVED'),
 ('Travel boundary','100','travel','AUTO-APPROVED'),
 ('One cent over','100.01','travel','SENT FOR MANAGER REVIEW'),
 ('Software boundary','200','software','AUTO-APPROVED'),
 ('Software over','200.01','software','SENT FOR MANAGER REVIEW'),
 ('Supplies boundary','50','supplies','AUTO-APPROVED'),
 ('Supplies over','50.01','supplies','SENT FOR MANAGER REVIEW'),
 ('Zero','0','travel','Enter an amount and category first.'),
 ('Empty amount','','travel','Enter an amount and category first.'),
 ('Negative','-1','travel','Enter an amount and category first.'),
 ('Empty category','80','','Enter an amount and category first.')]


def build_lab():
    site=ROOT/'production_pro/site'
    app=(site/'index.html').read_text().replace('<link rel="stylesheet" href="styles.css">','<style>'+(site/'styles.css').read_text()+'</style>').replace('<script src="app.js"></script>','<script>'+(site/'app.js').read_text()+'</script>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>LogicScript — Offline Boundary Testing Lab</title>
<style>*{box-sizing:border-box}body{display:block;margin:0;background:#0b1021;color:#eaf3ff;font:24px Arial;padding:110px 65px 130px}h1{font-size:44px;margin:10px 0}h2{font-size:30px;color:#7bf1d0}p,li{line-height:1.5}button,a{font:24px Arial;padding:15px 24px;border-radius:9px;width:auto;margin:0;font-weight:600;border:1px solid #4e827b;background:#173b43;color:#fff;cursor:pointer;text-decoration:none}nav{display:flex;gap:18px;margin:24px 0}.panel{width:100%;min-height:0;box-shadow:none;transform:none;border:1px solid #375269;border-radius:16px;background:#122237;padding:25px}section[hidden]{display:none}iframe{position:absolute;left:-4000px;width:1920px;height:1080px}table{width:100%;border-collapse:collapse;font-size:21px}td,th{padding:6px 15px;border-bottom:1px solid #365064;text-align:left}.pass{color:#7bf1d0}.fail{color:#ffb177}#summary{font-size:30px;font-weight:bold;margin:18px 0}small{color:#aebed8}</style>
<small>LOGICSCRIPT / ORIGINAL OFFLINE PRACTICE FILE</small><h1>Test the rule. Inspect the evidence.</h1>
<nav><button id="guide-tab">1. Start here</button><button id="matrix-tab">2. Test matrix</button><button id="download">Save practice file</button></nav>
<section id="guide" class="panel"><h2>Reproduce this lesson — no account or installation</h2><ol>
<li>Download <b>LogicScript_Practice_Lab.html</b> from the lesson files.</li><li>Save the file in a folder you can find. Double-click it to open it in your desktop browser.</li><li>Keep this file local. It contains the real example application and test runner.</li><li>Select <b>Test matrix</b>, then <b>Run all cases</b>. Read expected and observed results.</li><li>Use <b>Introduce wrong expectation</b> to see a deliberate test failure. Restore it afterward.</li></ol><p>These are invented expense limits for testing practice. No login, network request, payment, database or production authorization.</p></section>
<section id="matrix" class="panel" hidden><button id="run">Run all cases</button> <button id="mutate">Introduce wrong expectation</button><div id="summary">Ready — no tests run yet</div><table><thead><tr><th>Case / input USD</th><th>Expected</th><th>Observed from app</th><th>Result</th></tr></thead><tbody id="rows"></tbody></table></section>
<iframe title="Actual expense application under test" id="app"></iframe>
<script>
const cases=__CASES__;const frame=document.getElementById('app');frame.srcdoc=__APP__;
let wrong=false;document.getElementById('guide-tab').onclick=()=>{guide.hidden=false;matrix.hidden=true};
document.getElementById('matrix-tab').onclick=()=>{guide.hidden=true;matrix.hidden=false};
document.getElementById('mutate').onclick=()=>{wrong=!wrong;document.getElementById('mutate').textContent=wrong?'Restore correct expectation':'Introduce wrong expectation';document.getElementById('summary').textContent=wrong?'Exercise active: the one-cent expectation is intentionally wrong. Run the tests.':'Expectation restored. Run again.'};
document.getElementById('run').onclick=()=>{
const doc=frame.contentDocument;if(!doc?.getElementById('submit'))throw Error('Actual app is not ready');
const rows=document.getElementById('rows');rows.replaceChildren();let passed=0;
for(const [label,amount,category,original] of cases){const input=doc.getElementById('amount');input.value=amount;input.dispatchEvent(new Event('input',{bubbles:true}));const cat=doc.getElementById('category');cat.value=category;cat.dispatchEvent(new Event('change',{bubbles:true}));doc.getElementById('submit').click();
const observed=doc.getElementById('result').textContent;const expected=wrong&&label==='One cent over'?'AUTO-APPROVED':original;const ok=observed.startsWith(expected);if(ok)passed++;
const tr=document.createElement('tr');for(const text of [label+' / '+(amount||'(empty)')+' '+(category||'(no category)'),expected,observed,ok?'PASS':'FAIL']){const td=document.createElement('td');td.textContent=text;tr.append(td)}tr.lastChild.className=ok?'pass':'fail';rows.append(tr)}
document.getElementById('summary').textContent=`${passed} passed / ${cases.length-passed} failed — actual browser application results`;
};
document.getElementById('download').onclick=()=>{const blob=new Blob(['<!doctype html>'+document.documentElement.outerHTML],{type:'text/html'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='LogicScript_Practice_Lab.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
</script></html>'''
    return html.replace('__CASES__',json.dumps(CASES)).replace('__APP__',json.dumps(app).replace('</','<\\/'))


def mount_lab(page):
    """Mount the SAME offline app in the recording shell, with no account or network."""
    html=build_lab();markup,script=html.split('<script>',1)
    script=script.split('</script>',1)[0]
    page.evaluate(r"""markup=>{
      for(const child of [...document.body.children])if(!['lesson-overlay','capture-pointer'].includes(child.id))child.style.display='none';
      const lab=document.createElement('div');lab.id='practice-lab';lab.style.cssText='position:fixed;inset:94px 0 125px;background:#0b1021;z-index:49;padding:18px 65px;overflow:hidden';
      lab.innerHTML=markup.replace(/<!doctype html>|<html[^>]*>|<\/html>|<meta[^>]*>|<title>.*?<\/title>/gi,'');document.body.append(lab);
    }""",markup)
    page.add_script_tag(content=script)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(build_lab())
