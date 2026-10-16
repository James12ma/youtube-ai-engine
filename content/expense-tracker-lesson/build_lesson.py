"""Source of truth for video 1: narration, on-screen actions and demo data.

Writes lesson.json (consumed by scripts/render_lesson.py) and script.md (human review copy).
Actions are cued by a phrase that is spoken in the same chapter; the renderer performs
the action at the moment WhisperX aligns that phrase (or at an estimated time in draft mode).
Every action targets the real template (LogicScript_Expense_Tracker.xlsx).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

def row(r, date, vendor, desc, cat, amount, pay='Card', receipt='Yes', notes='', reviewed=''):
    return {'do': 'row', 'row': r, 'values': [{'date': date}, vendor, desc, cat, amount, pay, receipt, notes, reviewed]}

def act(cue, **kw):
    return {'cue': cue, **kw}

SETUP = {
    'clear': 'Expenses!A6:I505',
    'rows': [
        row(6, '2026-01-05', 'Office supply store', 'Paper and toner', 'Office supplies', 48.20),
        row(7, '2026-01-12', 'Design software co.', 'Monthly plan', 'Software & subscriptions', 59.99),
        row(8, '2026-01-20', 'Phone company', 'January phone bill', 'Phone & internet', 65.00, 'Bank transfer'),
    ],
    'start': {'do': 'select', 'ref': 'Expenses!A9'},
}

chapters = [
    dict(title='The typo your total never told you about', visual='sheet', key='', narration=(
        'If your expense tracker accepts a typo, your totals are wrong and you will not know why. Watch this row. '
        'The amount looks normal, but it was typed with a dollar sign, so the spreadsheet stored it as text, not as a number. '
        'A plain total would quietly skip it. This tracker does something different. The row turns red, and the status '
        'column says exactly what is wrong. In the next few minutes, you will build a free expense tracker that checks '
        'every row it receives, catches duplicates and missing receipts, and only tells you all checks passed when the '
        'numbers really add up. The template is free, and it works in Google Sheets, Excel and LibreOffice.'),
        actions=[act('Watch this row', **row(9, '2026-01-28', 'Corner cafe', 'Client lunch', 'Meals', '$38.75'), expect={'Expenses!J9':'ERROR','Expenses!K9':'Amount is not a number.'}),
                 act('the status column', do='select', ref='Expenses!J9:K9')]),
    dict(title='Make your copy and set three rules', visual='sheet', key='', narration=(
        'Start by making your own copy of the template. In Google Sheets, open the link and choose File, then Make a copy. '
        'Your data stays in your copy. Now open the Settings tab. There are three yellow cells to set. The first is your '
        'tax year. Any date outside that year will be flagged. The second is your large expense rule. Anything at or above '
        'that amount gets a second look. The third is your receipt rule. At or above that amount, the tracker expects you '
        'to mark the receipt as saved. These two numbers are your own rules, not legal thresholds, so ask your tax '
        'professional what records you actually need. Below them is your category list. Rename or add categories to match '
        'how you work.'),
        actions=[act('open the Settings tab', do='select', ref='Settings!A1'),
                 act('tax year', do='select', ref='Settings!B4'),
                 act('large expense rule', do='select', ref='Settings!B5'),
                 act('receipt rule', do='select', ref='Settings!B6'),
                 act('category list', do='select', ref='Settings!B11:B23')]),
    dict(title='Rule one: dates you can trust', visual='sheet', key='', narration=(
        "Now the Expenses tab. Each yellow column is something you type, and each grey rule column checks one thing. "
        "Let's add a laptop bought on the thirtieth of December. Look at the status. It says error, because the date falls "
        "outside the tax year we set. This is a common silent mistake in a yearly tracker: a receipt from last year slips "
        "into this year's totals. The date rule also catches dates in the future, and text that only looks like a date. "
        "Let's correct it to the thirtieth of January. The error is gone. The row still says check, and we will come back "
        "to why in a moment."),
        actions=[act('Now the Expenses tab', do='select', ref='Expenses!A9'),
                 act('add a laptop', **row(10, '2025-12-30', 'Computer store', 'Laptop', 'Equipment', 1299.00), expect={'Expenses!J10':'ERROR','Expenses!K10':'Date outside tax year. Large amount: review.'}),
                 act('Look at the status', do='select', ref='Expenses!J10:K10'),
                 act('correct it to the thirtieth of January', do='set', ref='Expenses!A10', value={'date': '2026-01-30'}, expect={'Expenses!J10':'CHECK'}),
                 act('The error is gone', do='select', ref='Expenses!J10:K10')]),
    dict(title='Rule two: amounts must be real numbers', visual='sheet', key='', narration=(
        "Back to the lunch from the opening. The problem was the dollar sign. Type the amount as a plain number, and the row "
        "passes. The amount rule also blocks zero and negative amounts. Here is a refund entered as minus twenty dollars. "
        "It is flagged, because mixing refunds into expenses makes totals hard to check. Record refunds separately, or note "
        "them in the Notes column, and keep this table for money that went out. Let's remove that row."),
        actions=[act('Back to the lunch', do='select', ref='Expenses!E9'),
                 act('as a plain number', do='set', ref='Expenses!E9', value=38.75, expect={'Expenses!J9':'OK'}),
                 act('Here is a refund', **row(11, '2026-02-02', 'Internet provider', 'Refund for outage', 'Phone & internet', -20.00, 'Bank transfer'), expect={'Expenses!J11':'ERROR','Expenses!K11':'Amount must be above zero.'}),
                 act('It is flagged', do='select', ref='Expenses!J11:K11'),
                 act('remove that row', do='clear', ref='Expenses!A11:I11', expect={'Expenses!J11':''})]),
    dict(title="Rule three: why the dropdown isn't enough", visual='sheet', key='', narration=(
        "Categories come from a dropdown, built from your list in Settings. When you type, the dropdown refuses anything "
        "that is not on the list. So why do we need a rule column as well? Because depending on the app, pasted or imported "
        "data can skip the dropdown completely. In Excel, a normal paste can even overwrite the dropdown rule itself. Here is "
        "a row pasted in with the category meal, without the s. The dropdown never saw it, but the category rule did. The "
        "status says error: category not in your list. Fix the spelling, and the row passes. Dropdowns help you type. The "
        "rule column checks what is actually there."),
        actions=[act('Categories come from a dropdown', do='select', ref='Expenses!D6'),
                 act('Here is a row pasted in', **row(11, '2026-02-10', 'Corner cafe', 'Team coffee', 'Meal', 18.40), expect={'Expenses!J11':'ERROR','Expenses!K11':'Category not in your list.'}),
                 act('The status says error', do='select', ref='Expenses!J11:K11'),
                 act('Fix the spelling', do='set', ref='Expenses!D11', value='Meals', expect={'Expenses!J11':'OK'})]),
    dict(title='Rule four: catch duplicates', visual='sheet', key='', narration=(
        "Duplicates are easy to create. You import a statement twice, or two people enter the same bill. Here is the "
        "software subscription entered a second time. Both rows switch to check, with possible duplicate. The rule compares "
        "the date, the vendor and the amount. Behind it is one counting function: it counts how many rows have the same three "
        "values, and if the answer is more than one, it flags them. Some duplicates are real, like two identical purchases on "
        "the same day. If so, you can mark the row as reviewed. This one is a mistake, so we delete it."),
        actions=[act('entered a second time', **row(12, '2026-01-12', 'Design software co.', 'Monthly plan', 'Software & subscriptions', 59.99), expect={'Expenses!J12':'CHECK','Expenses!J7':'CHECK','Expenses!K12':'Possible duplicate.'}),
                 act('Both rows switch to check', do='select', ref='Expenses!J7:K12'),
                 act('Behind it is one counting function', do='select', ref='Expenses!O12'),
                 act('so we delete it', do='clear', ref='Expenses!A12:I12', expect={'Expenses!J7':'OK','Expenses!J12':''})]),
    dict(title='Rules five and six: receipts and large amounts', visual='sheet', key='', narration=(
        "The last two rules never block anything. They ask for a second look. Here is a flight for four hundred twelve dollars "
        "and thirty cents. It is above our receipt rule, and the receipt is not marked as saved, so the row says check. Save the "
        "receipt, mark it as yes, and the row passes. Now the laptop from earlier. It is above our large expense rule, so it "
        "says check. Large amounts are worth a second look, but they are not mistakes. Once you have confirmed it, set reviewed "
        "to yes. Warnings can be cleared by review. Errors cannot. An error must always be fixed."),
        actions=[act('Here is a flight', **row(12, '2026-02-14', 'Airline', 'Flight to client meeting', 'Travel', 412.30, receipt=''), expect={'Expenses!J12':'CHECK','Expenses!K12':'Receipt not marked as saved.'}),
                 act('so the row says check', do='select', ref='Expenses!J12:K12'),
                 act('mark it as yes', do='set', ref='Expenses!G12', value='Yes', expect={'Expenses!J12':'OK'}),
                 act('the laptop from earlier', do='select', ref='Expenses!J10:K10', expect={'Expenses!J10':'CHECK','Expenses!K10':'Large amount: review.'}),
                 act('set reviewed to yes', do='set', ref='Expenses!I10', value='Yes', expect={'Expenses!J10':'OK'})]),
    dict(title='Error versus check: what counts in your totals', visual='sheet', key='', narration=(
        "This difference matters for your totals. A check row is counted, because the data is valid and only needs your "
        "attention. An error row is left out of every total until you fix it, because its numbers cannot be trusted. Let's "
        "add an expense dated last year. Open the Summary tab. It shows one error, and it shows exactly how much money was left "
        "out of the totals because of it. Nothing disappears silently. Go back and correct the date, and the summary updates."),
        actions=[act('add an expense dated last year', **row(13, '2025-12-31', 'Office supply store', 'Notebooks', 'Office supplies', 25.00), expect={'Expenses!J13':'ERROR'}),
                 act('Open the Summary tab', do='select', ref='Summary!B6', expect={'Summary!B6':'1'}),
                 act('how much money was left', do='select', ref='Summary!B11', expect={'Summary!B11':'25.00'}),
                 act('correct the date', do='set', ref='Expenses!A13', value={'date': '2026-02-20'}, expect={'Expenses!J13':'OK'}),
                 act('the summary updates', do='select', ref='Summary!B4', expect={'Summary!B4':'ALL CHECKS PASSED'})]),
    dict(title='The summary that checks itself', visual='sheet', key='', narration=(
        "The summary does more than add things up. It totals every category and every month, and then it checks that both "
        "sets of totals add up to the same overall amount. If a category were renamed or a date were wrong, those two checks "
        "would say no. At the top is one status. It only says all checks passed when there are no errors, every warning has "
        "been reviewed, and both totals agree. That is the moment you can trust the numbers."),
        actions=[act('every category', do='select', ref='Summary!A24:B36'),
                 act('every month', do='select', ref='Summary!D24:E35'),
                 act('add up to the same overall amount', do='select', ref='Summary!A13:B14', expect={'Summary!B13':'YES','Summary!B14':'YES'}),
                 act('At the top is one status', do='select', ref='Summary!A4:B4', expect={'Summary!B4':'ALL CHECKS PASSED'})]),
    dict(title='Your weekly routine', visual='card',
         key='Enter  →  fix ERRORs  →  review CHECKs  →  ALL CHECKS PASSED', narration=(
        "Here is the weekly routine. Enter the week's expenses. Fix every error. Review every check, and mark it reviewed when "
        "you are sure. Then look at the summary. When it says all checks passed, you are done for the week. A few minutes each "
        "week is much easier than untangling a whole year at tax time. One reminder: this is a record-keeping tool, not tax "
        "advice. Your categories and rules are yours to set, and a tax professional can tell you which records you need to keep."),
        actions=[]),
    dict(title='Next: test your rules at the edge', visual='card',
         key='Every rule has an edge. Test it one cent at a time.', narration=(
        "Every rule in this tracker has an edge. What happens at exactly the receipt amount, or one cent above it? In the next "
        "video, we test a real approval rule at its exact boundary, one cent at a time. The free template is linked in the "
        "description. If it catches a mistake for you, tell me which one in the comments."),
        actions=[]),
]

lesson = {
    'title': 'Build a Free Expense Tracker That Catches Its Own Mistakes',
    'renderer': 'spreadsheet',
    'template': 'LogicScript_Expense_Tracker.xlsx',
    'thumbnail': '../../brand/Video1_thumbnail_concept.jpg',
    'thumbnail_text': 'IT CAUGHT IT',
    'topic': 'a self-checking expense tracker spreadsheet',
    'provenance': ('Assistant-authored, source-checked educational script; every on-screen result is produced live by the '
                   'real template during recording. All amounts are invented teaching examples.'),
    'demo_setup': SETUP,
    'chapters': chapters,
}

if __name__ == '__main__':
    for ch in chapters:  # every cue must be spoken in its own chapter
        for a in ch['actions']:
            assert a['cue'].lower() in ch['narration'].lower(), (ch['title'], a['cue'])
    n_expect = sum(len(a.get('expect', {})) for ch in chapters for a in ch['actions'])
    assert n_expect >= 30, n_expect
    (HERE / 'lesson.json').write_text(json.dumps(lesson, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    words = sum(len(c['narration'].split()) for c in chapters)
    md = [f"# {lesson['title']}", '', f'_{words} narrated words, {len(chapters)} chapters. Generated from build_lesson.py._', '']
    for i, c in enumerate(chapters):
        md += [f"## {i:02d}. {c['title']}", '', c['narration'], '']
        if c['actions']:
            md += ['On screen:'] + [f"- at “{a['cue']}”: {a['do']} {a.get('ref', '')}{' row ' + str(a['row']) if 'row' in a else ''}" for a in c['actions']] + ['']
        else:
            md += [f"Card: {c['key']}", '']
    (HERE / 'script.md').write_text('\n'.join(md), encoding='utf-8')
    print('chapters', len(chapters), 'words', words)
