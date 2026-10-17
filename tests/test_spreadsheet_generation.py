"""Exercise the recovered generator in isolation; never overwrite its source template."""
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def test_original_generator_produces_a_complete_formula_workbook(tmp_path):
    generator=Path('content/expense-tracker-lesson/build_template.py').resolve()
    template=Path('content/expense-tracker-lesson/LogicScript_Expense_Tracker.xlsx')
    before=template.read_bytes()
    folder=tmp_path/'content'/'expense-tracker-lesson';folder.mkdir(parents=True)
    subprocess.run([sys.executable,str(generator)],cwd=tmp_path,check=True,capture_output=True,text=True)
    output=folder/'LogicScript_Expense_Tracker.xlsx'
    with zipfile.ZipFile(output) as z:
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        book=ET.fromstring(z.read('xl/workbook.xml'))
        assert {s.attrib['name'] for s in book.findall('s:sheets/s:sheet',ns)}=={'Settings','Expenses','Summary','Start Here'}
        formulas=[node for name in z.namelist() if name.startswith('xl/worksheets/') and name.endswith('.xml')
                  for node in ET.fromstring(z.read(name)).findall('.//s:f',ns)]
        assert len(formulas)==4084
        assert all(f.text and '#REF!' not in f.text for f in formulas)
    assert template.read_bytes()==before
