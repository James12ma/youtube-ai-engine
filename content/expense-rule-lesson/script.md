# Before You Automate: Test the One-Cent Boundary

Assistant-authored, source-checked educational script; not output from the rate-limited project AI provider.

## The one-cent test

A rule can pass the obvious tests and still approve the wrong request. Watch what happens when we move a travel expense just one cent above its limit. In this lesson, you will build a small test matrix, run it against a real local application, and learn which checks belong outside the browser. No bank account or paid service is connected.

## Write the policy first

Start with a policy that someone can read without knowing the code. Our example allows automatic approval for travel up to one hundred dollars, software up to two hundred, and supplies up to fifty. These limits are invented teaching examples. They are not accounting guidance. Larger amounts go to a manager. A missing or nonpositive amount must never become an approval.

## Separate three decisions

There are three different questions. Is the request valid? What does the spending policy decide? Is the person allowed to perform this action? A valid amount does not prove that the requester has permission. An automatic policy decision does not transfer money. Keeping these questions separate makes both the implementation and the tests easier to reason about.

## First, prove the normal case

Here is the actual application running locally. We enter eighty dollars and select travel. Before clicking, predict the outcome. Eighty is below the travel limit, so the expected result is automatic approval. Now we run the rule. The decision displayed here is produced by the application code, rather than a caption pretending that an action happened.

## Now prove the other branch

Change only the amount to one hundred twenty dollars. Keep travel selected. This time the expected result is manager review. Run the rule again and compare the displayed decision with that expectation. Changing one input at a time helps explain why the result changed. It also prevents a successful test from hiding an unrelated change in category or configuration.

## Test the exact boundary

The phrase up to includes the limit itself. Set travel to exactly one hundred dollars. Our implementation uses a less than or equal comparison, so the boundary is approved. A strict less than comparison would behave differently. This is why the written policy should say whether the endpoint is included, and the test should check the endpoint directly.

## Cross it by one cent

Now enter one hundred dollars and one cent. The travel category stays the same. Run the rule and the request goes to manager review. Together, the previous test and this one exercise the exact decision boundary. Do not test only eighty and one hundred twenty. Those two examples could both pass even if the threshold were accidentally set to ninety or one hundred ten.

## The category is part of the rule

Use the same one hundred twenty dollar amount, but select software. Software has a different limit, so this request is automatically approved. This is a useful cross-check: the engine must read the category rather than apply one global threshold. Your test table needs at least one meaningful case for every supported category, including supplies.

## Check the smaller limit

For supplies, try sixty dollars. The limit is fifty, so sixty needs review. A common testing mistake is to cover the first category thoroughly and assume the others work. A category table can contain a typo even when the comparison logic is correct. Test the policy data as well as the code that reads it.

## Reject invalid requests

Set the amount to zero and keep a category selected. Run the rule. The application asks for an amount and category instead of approving the request. Also test an empty amount, a negative amount, and an empty category. In a real service, define an explicit response for unknown categories. Do not let missing policy data silently become an approval.

## Turn examples into a matrix

Write each case as inputs, expected result, and observed result. Our boundary pair is travel at one hundred and at one hundred point zero one. Add software at two hundred and two hundred point zero one, and supplies at fifty and fifty point zero one. Keep invalid-input cases in a separate group. A test passes only when the observed result matches the expected result.

## Money needs an explicit representation

There is another boundary underneath the policy: how you represent money. Binary floating point cannot represent every decimal fraction exactly. Python provides decimal arithmetic for decimal calculations. For a single currency with two decimal places, validated integer minor units are another design option. Choose the currency, accepted precision, and rounding policy explicitly. Reject unsupported precision instead of silently inventing a policy.

## The browser is not the security boundary

The form is useful for feedback, but it is not an authority. A user can alter client-side code or submit a request without the form. Repeat validation and authorization on the server before a consequential action. OWASP recommends denying access by default and checking permissions on every request. A missing permission check cannot be repaired by making the button harder to find.

## What this demo does not prove

This local demo does not authenticate users, save decisions to a database, send payments, or implement a server-side approval service. Its purpose is to make the rule visible and testable. Before connecting real accounts, add those controls and test them separately. Keep a record of the request, policy version, decision, and reviewer so a later investigation can explain what happened.

## Open your free practice lab

To reproduce this lesson, use the free practice file included with the video. Download LogicScript Practice Lab dot H T M L and save it in a folder you can find. On a desktop computer, double-click that file to open it in your browser. You do not need an account, a paid tool, or a software installation. This start page lists the steps. The file contains our actual example application and a test runner. Keep it local. It does not connect to a business account or send your entries anywhere. If you want a separate copy, click Save practice file here.

## Run the full browser test matrix

Select Test matrix. The cases include both sides of the travel, software, and supplies boundaries, plus invalid inputs. Click Run all cases. The runner enters each amount and category into the actual example application, clicks its approval button, then reads the result. These observed values are not a prewritten answer table. Eleven passes means these eleven expectations matched this version of the application. It does not mean the system is secure or complete. Notice the empty amount, negative amount, and missing category cases. They are just as important as the normal approvals.

## Prove that a failing test is visible

A green test report is useful only if a mismatch can make it fail. Click Introduce wrong expectation. This exercise changes the expected outcome for the one-cent-over travel case to approval. It does not alter the application rule. Click Run all cases again. Now one test fails: the actual application still sends that request for manager review. Compare the expected and observed columns before deciding what to fix. Here the expectation is deliberately wrong, so click Restore correct expectation, then run the cases again. All eleven should pass. This checks that our test runner can detect the disagreement.

## Your practical checklist

Before you connect an automation, answer five questions. Is the policy written clearly? Have you tested both sides of every boundary? Do invalid requests fail safely? Does the server check both inputs and permissions? Can you explain a past decision from a record? Start with a test matrix you can inspect, then automate its checks. That is how a small working demo becomes evidence you can use.