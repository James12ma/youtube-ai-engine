# Sources and claim audit — video 1 (2026-10-15)

The script is assistant-authored and reviewed against the real template. Every on-screen status, issue
message and total in the video is produced live by `LogicScript_Expense_Tracker.xlsx` during recording;
nothing is mocked. All vendors and amounts are invented teaching examples.

## Technical claims
- **Text that looks like a number is not summed.** Demonstrated live: "$38.75" entered as text gets the status "Amount is not a number" and is excluded. Spreadsheet SUM/SUMIFS ignore text values; shown by the tracker's own totals.
- **Pasted or imported data can skip dropdown validation; in Excel a normal paste can overwrite the rule.**
  - Microsoft Q&A (accepted answer by a volunteer moderator, not Microsoft staff): https://learn.microsoft.com/en-us/answers/questions/5046522/validation-not-triggering
  - Automate Excel, "Data Validation Not Working in Excel & Google Sheets": https://automateexcel.com/how-to/data-validation-not-working
  The script says "depending on the app" because Google Sheets behaviour is documented only by a third party.
  The demo writes the value through LibreOffice's API, which (like a paste or import) bypasses the dropdown.
- **Duplicate detection counts rows with the same date, vendor and amount** (COUNTIFS in the template). Verified by formula tests.
- **ERROR rows are excluded from totals; CHECK rows are counted; review clears warnings but never errors.** Verified by LibreOffice recalculation tests (examples, review path, fixed-data path).
- **The template works in Google Sheets, Excel and LibreOffice.** It uses only COUNTA, COUNTIF, COUNTIFS, SUMIFS, DATE, YEAR, TODAY, IF, AND, NOT, ISNUMBER, TRIM, ROUND. Verified in LibreOffice; Google Sheets and Excel import still to be checked by the owner before publication.
- **"File, then Make a copy" in Google Sheets** is the standard command for copying a shared file.

## Claims deliberately NOT made
- No statement that any expense is deductible, and no tax thresholds. Receipt and large-expense values are labelled as the viewer's own rules.
- No promise of saved money or time beyond "a few minutes each week" for the routine, which is presented as an opinion.
- No performance, income or audience claims.

## Visual and audio provenance
- Screen recording of LibreOffice Calc (free software, MPL 2.0) showing LogicScript's own template; the video says the template also works in Google Sheets and Excel.
- Narration: Piper synthetic voice, LibriTTS-trained model, CC BY 4.0 (https://www.openslr.org/60/, https://creativecommons.org/licenses/by/4.0/). Attribution is included in the description.
- Fonts: Inter (SIL Open Font License). No stock footage, music, third-party logos or screenshots.
