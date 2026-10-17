"""Real keyboard regression: numeric input after a forced-text import.

Runs in an actual Calc window, not a fake UNO object. Fast gate before filming.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest


@pytest.mark.skipif(not all(shutil.which(x) for x in ('soffice','xvfb-run','xdotool')),
                    reason='Native Calc/Xvfb/xdotool unavailable')
def test_native_number_replaces_an_imported_text_amount(tmp_path):
    script=tmp_path/'check.py'
    script.write_text(f'''
import json,sys
from pathlib import Path
sys.path.insert(0,{str(Path.cwd())!r})
from production_pro.sheet_recorder import SheetRecorder
lesson=json.loads(Path('content/expense-tracker-lesson/lesson.json').read_text())
observed=[]
with SheetRecorder(Path('content/expense-tracker-lesson/LogicScript_Expense_Tracker.xlsx'),Path({str(tmp_path)!r})/'calc') as rec:
    for a in lesson['demo_setup']['rows']:rec.apply(a,sleep=lambda s:None)
    for a in [{{'do':'type','ref':'Expenses!E6','text':'41.25'}},
              {{'do':'set','ref':'Expenses!E6','value':'$38.75'}},
              {{'do':'type','ref':'Expenses!E6','text':'38.75','as_number':True}}]:
        rec.apply(a)
        _,c=rec._range('Expenses!E6')
        observed.append({{'value':rec.value('Expenses!E6'),'status':rec.value('Expenses!J6'),
                         'type':str(c.getType()),'number_format':c.NumberFormat,
                         'format_type':rec.doc.getNumberFormats().getByKey(c.NumberFormat).Type}})
        print(json.dumps(observed[-1]),flush=True)
print('NATIVE_RESULT '+json.dumps(observed),flush=True)
''')
    env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)}
    p=subprocess.run(['xvfb-run','-a','-s','-screen 0 1920x1080x24',sys.executable,str(script)],
                      capture_output=True,text=True,timeout=120,env=env)
    print(p.stdout)
    assert p.returncode==0,p.stdout[-2500:]+p.stderr[-1000:]
    import json
    rows=json.loads(p.stdout.split('NATIVE_RESULT ')[-1].strip())
    assert [x['value'] for x in rows]==['41.25','$38.75','38.75']
    assert [x['status'] for x in rows]==['OK','ERROR','OK']
