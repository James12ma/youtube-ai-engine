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
        from scripts.build_practice_lab import build_lab,mount_lab
        # Exercise the renderer shell too: its older CSS formerly shrank the lab.
        page.set_viewport_size({'width':1920,'height':1080});mount_lab(page)
        page.frame_locator('#app').locator('#submit').wait_for()
        page.locator('#matrix-tab').click();page.locator('#run').click()
        table=page.locator('#rows').bounding_box();last=page.locator('#rows tr').last.bounding_box()
        assert table['width']>1600, 'Inherited application CSS narrowed the lab'
        assert last['y']+last['height']<940, 'Invalid-input rows overlap the caption area'

        lab=browser.new_page();lab.set_content(build_lab())
        lab.frame_locator('#app').locator('#submit').wait_for()
        lab.locator('#matrix-tab').click();lab.locator('#run').click()
        assert lab.locator('#summary').inner_text().startswith('11 passed / 0 failed')
        lab.locator('#mutate').click();lab.locator('#run').click()
        assert lab.locator('#summary').inner_text().startswith('10 passed / 1 failed')
        assert lab.locator('#rows tr').filter(has_text='One cent over').inner_text().endswith('FAIL')
        lab.locator('#mutate').click();lab.locator('#run').click()
        assert lab.locator('#summary').inner_text().startswith('11 passed / 0 failed')
        with lab.expect_download() as event:lab.locator('#download').click()
        import tempfile
        directory=tempfile.TemporaryDirectory()
        path=Path(directory.name)/event.value.suggested_filename
        event.value.save_as(path);assert path.stat().st_size>1000
        local=browser.new_page();local.goto(path.as_uri())
        local.frame_locator('#app').locator('#submit').wait_for()
        local.locator('#matrix-tab').click();local.locator('#run').click()
        assert local.locator('#summary').inner_text().startswith('11 passed / 0 failed')
        evidence.append({'practice_lab':True,'normal_passes':11,'deliberate_failure_detected':True,'restored_passes':11,'download_reopened_from_file':True,'passed':True})
        browser.close();directory.cleanup()
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(evidence,indent=2));print(f'{len(evidence)} actual Chromium policy tests passed')

if __name__=='__main__':run()
