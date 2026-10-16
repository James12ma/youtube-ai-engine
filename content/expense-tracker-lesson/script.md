# Build a Free Expense Tracker That Catches Its Own Mistakes

_1064 narrated words, 11 chapters. Generated from build_lesson.py._

## 00. The typo your total never told you about

If your expense tracker accepts a typo, your totals are wrong and you will not know why. Watch this row. The amount looks normal, but it was typed with a dollar sign, so the spreadsheet stored it as text, not as a number. A plain total would quietly skip it. This tracker does something different. The row turns red, and the status column says exactly what is wrong. In the next few minutes, you will build a free expense tracker that checks every row it receives, catches duplicates and missing receipts, and only tells you all checks passed when the numbers really add up. The template is free, and it works in Google Sheets, Excel and LibreOffice.

On screen:
- at “Watch this row”: row  row 9
- at “the status column”: select Expenses!J9:K9

## 01. Make your copy and set three rules

Start by making your own copy of the template. In Google Sheets, open the link and choose File, then Make a copy. Your data stays in your copy. Now open the Settings tab. There are three yellow cells to set. The first is your tax year. Any date outside that year will be flagged. The second is your large expense rule. Anything at or above that amount gets a second look. The third is your receipt rule. At or above that amount, the tracker expects you to mark the receipt as saved. These two numbers are your own rules, not legal thresholds, so ask your tax professional what records you actually need. Below them is your category list. Rename or add categories to match how you work.

On screen:
- at “open the Settings tab”: select Settings!A1
- at “tax year”: select Settings!B4
- at “large expense rule”: select Settings!B5
- at “receipt rule”: select Settings!B6
- at “category list”: select Settings!B11:B23

## 02. Rule one: dates you can trust

Now the Expenses tab. Each yellow column is something you type, and each grey rule column checks one thing. Let's add a laptop bought on the thirtieth of December. Look at the status. It says error, because the date falls outside the tax year we set. This is a common silent mistake in a yearly tracker: a receipt from last year slips into this year's totals. The date rule also catches dates in the future, and text that only looks like a date. Let's correct it to the thirtieth of January. The error is gone. The row still says check, and we will come back to why in a moment.

On screen:
- at “Now the Expenses tab”: select Expenses!A9
- at “add a laptop”: row  row 10
- at “Look at the status”: select Expenses!J10:K10
- at “correct it to the thirtieth of January”: set Expenses!A10
- at “The error is gone”: select Expenses!J10:K10

## 03. Rule two: amounts must be real numbers

Back to the lunch from the opening. The problem was the dollar sign. Type the amount as a plain number, and the row passes. The amount rule also blocks zero and negative amounts. Here is a refund entered as minus twenty dollars. It is flagged, because mixing refunds into expenses makes totals hard to check. Record refunds separately, or note them in the Notes column, and keep this table for money that went out. Let's remove that row.

On screen:
- at “Back to the lunch”: select Expenses!E9
- at “as a plain number”: set Expenses!E9
- at “Here is a refund”: row  row 11
- at “It is flagged”: select Expenses!J11:K11
- at “remove that row”: clear Expenses!A11:I11

## 04. Rule three: why the dropdown isn't enough

Categories come from a dropdown, built from your list in Settings. When you type, the dropdown refuses anything that is not on the list. So why do we need a rule column as well? Because depending on the app, pasted or imported data can skip the dropdown completely. In Excel, a normal paste can even overwrite the dropdown rule itself. Here is a row pasted in with the category meal, without the s. The dropdown never saw it, but the category rule did. The status says error: category not in your list. Fix the spelling, and the row passes. Dropdowns help you type. The rule column checks what is actually there.

On screen:
- at “Categories come from a dropdown”: select Expenses!D6
- at “Here is a row pasted in”: row  row 11
- at “The status says error”: select Expenses!J11:K11
- at “Fix the spelling”: set Expenses!D11

## 05. Rule four: catch duplicates

Duplicates are easy to create. You import a statement twice, or two people enter the same bill. Here is the software subscription entered a second time. Both rows switch to check, with possible duplicate. The rule compares the date, the vendor and the amount. Behind it is one counting function: it counts how many rows have the same three values, and if the answer is more than one, it flags them. Some duplicates are real, like two identical purchases on the same day. If so, you can mark the row as reviewed. This one is a mistake, so we delete it.

On screen:
- at “entered a second time”: row  row 12
- at “Both rows switch to check”: select Expenses!J7:K12
- at “Behind it is one counting function”: select Expenses!O12
- at “so we delete it”: clear Expenses!A12:I12

## 06. Rules five and six: receipts and large amounts

The last two rules never block anything. They ask for a second look. Here is a flight for four hundred twelve dollars and thirty cents. It is above our receipt rule, and the receipt is not marked as saved, so the row says check. Save the receipt, mark it as yes, and the row passes. Now the laptop from earlier. It is above our large expense rule, so it says check. Large amounts are worth a second look, but they are not mistakes. Once you have confirmed it, set reviewed to yes. Warnings can be cleared by review. Errors cannot. An error must always be fixed.

On screen:
- at “Here is a flight”: row  row 12
- at “so the row says check”: select Expenses!J12:K12
- at “mark it as yes”: set Expenses!G12
- at “the laptop from earlier”: select Expenses!J10:K10
- at “set reviewed to yes”: set Expenses!I10

## 07. Error versus check: what counts in your totals

This difference matters for your totals. A check row is counted, because the data is valid and only needs your attention. An error row is left out of every total until you fix it, because its numbers cannot be trusted. Let's add an expense dated last year. Open the Summary tab. It shows one error, and it shows exactly how much money was left out of the totals because of it. Nothing disappears silently. Go back and correct the date, and the summary updates.

On screen:
- at “add an expense dated last year”: row  row 13
- at “Open the Summary tab”: select Summary!B6
- at “how much money was left”: select Summary!B11
- at “correct the date”: set Expenses!A13
- at “the summary updates”: select Summary!B4

## 08. The summary that checks itself

The summary does more than add things up. It totals every category and every month, and then it checks that both sets of totals add up to the same overall amount. If a category were renamed or a date were wrong, those two checks would say no. At the top is one status. It only says all checks passed when there are no errors, every warning has been reviewed, and both totals agree. That is the moment you can trust the numbers.

On screen:
- at “every category”: select Summary!A24:B36
- at “every month”: select Summary!D24:E35
- at “add up to the same overall amount”: select Summary!A13:B14
- at “At the top is one status”: select Summary!A4:B4

## 09. Your weekly routine

Here is the weekly routine. Enter the week's expenses. Fix every error. Review every check, and mark it reviewed when you are sure. Then look at the summary. When it says all checks passed, you are done for the week. A few minutes each week is much easier than untangling a whole year at tax time. One reminder: this is a record-keeping tool, not tax advice. Your categories and rules are yours to set, and a tax professional can tell you which records you need to keep.

Card: Enter  →  fix ERRORs  →  review CHECKs  →  ALL CHECKS PASSED

## 10. Next: test your rules at the edge

Every rule in this tracker has an edge. What happens at exactly the receipt amount, or one cent above it? In the next video, we test a real approval rule at its exact boundary, one cent at a time. The free template is linked in the description. If it catches a mistake for you, tell me which one in the comments.

Card: Every rule has an edge. Test it one cent at a time.
