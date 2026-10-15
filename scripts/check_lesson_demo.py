"""Run the downloadable policy matrix against actual Chromium application clicks."""
import csv,json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(out=Path('outputs/lesson-demo-matrix.json')):
    base=Path('production_pro/site')
    html=(base/'index.html').read_text().replace('<link rel="stylesheet" href="styles.css">','<style>'+(base/'styles.css').read_text()+'</style>').replace('<script src="app.js"></script>','<script>'+(base/'app.js').read_text()+'</script>')
    evidence=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page()
        page.set_content(html)
        for row in csv.DictReader(Path('content/expense-rule-lesson/test-matrix.csv').open()):
            page.locator('#amount').fill(row['amount']);page.locator('#category').select_option(row['category']);page.locator('#submit').click()
            actual=page.locator('#result').inner_text();passed=row['expected'] in actual
            evidence.append({**row,'actual':actual,'passed':passed})
            assert passed, 'Policy matrix mismatch'
        browser.close()
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(evidence,indent=2));print(f'{len(evidence)} actual Chromium policy tests passed')

if __name__=='__main__':run()
