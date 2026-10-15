# LogicScript — First Video, Channel Setup and Management Strategy

**Prepared by:** Claude (Opus 5.5) · **Date:** 15 October 2026 · **Mode:** research only. Nothing was published, no channel setting was changed, no money was spent.

**How to read the numbers in this report**
- **Verified** = read today from an official page (YouTube Help, YouTube API docs, Make/n8n program pages).
- **Third-party** = view counts and CPM ranges read today from aggregator sites (developereducators.com, OutlierKit). They were not checked directly on YouTube, and their methods are not disclosed.
- **Estimate / judgement** = my assessment. It is labelled as such.
- I did **not** obtain search volumes, real RPM data or YouTube Analytics data. Those need Google Trends, YouTube Studio or the Analytics API, none of which this session can reach.

---

## 1. Recommendation in one paragraph

**Make the first public video a practical, searchable spreadsheet build:** *"Build a Free Expense Tracker That Catches Its Own Mistakes."* Publish **"Before You Automate: Test the One-Cent Boundary" second**, as its natural follow-up ("now test your tracker's rules").

Together they establish one clear channel promise: **LogicScript makes your spreadsheets and automations trustworthy.** That promise is:
- searchable (people look for trackers and automations, not for "boundary testing");
- evergreen;
- close to business and finance topics;
- backed by your real tax-office experience, which also protects the channel against YouTube's "inauthentic content" rules for AI-assisted channels.

The catch: the expense-tracker video does not exist yet and needs about 30 Actions minutes after the allowance resets around 1 November. Until then, the One-Cent video can go up **privately** to test the upload path.

---

## 2. Facts that shape the strategy

| Topic | What I found | Status |
|---|---|---|
| Partner Program thresholds | 1,000 subscribers **plus** either 4,000 qualified public long-form watch hours in the last 12 months, or 10M qualified Shorts views in 90 days. Shorts-feed watch time does not count toward the 4,000 hours. New partner terms take effect 1 Feb 2027 and must be accepted in Studio by 31 Jan 2027. | Verified ([YouTube Help](https://support.google.com/youtube/answer/72851)) |
| Country | The partner program is available in **both the Dominican Republic and the United States**. Use your true country of residence. | Verified ([availability list](https://support.google.com/youtube/answer/7101720)) |
| AI-assisted content | YouTube renamed its "repetitious content" policy to "inauthentic content". Mass-produced, low-value uploads are not monetizable. AI tools (including voice) are allowed when the final video is original and adds real value. | Third-party report of YouTube statements ([Creator Handbook](https://www.creatorhandbook.net/youtube-updates-monetization-policy-for-inauthentic-content/)) |
| Ad rates by niche | Published **CPM** ranges: tech reviews about $10–18, AI/tech about $8–20, business about $14–35, personal finance about $15–45. These are advertiser prices, not creator earnings. Creators keep at most 55% on long-form (that is what RPM measures). Rates depend heavily on viewer country, season, ad eligibility and video format. Sources disagree, and none disclose a method. | Third-party ([OutlierKit compilation](https://outlierkit.com/resources/youtube-rpm-benchmarks/)) |
| Affiliate programs | Make pays 35% of subscription payments for 12 months from signup; anyone with a Make account can join. n8n pays 30% recurring for 12 months via PartnerStack (the listing says it was verified 8 Aug 2026). | Make verified ([Make help](https://help.make.com/affiliate-program.md)); n8n third-party ([Reditus](https://getreditus.com/affiliate-programs/n8n)) |
| Cost of one video | Measured from your own runs: render about 16 min, polish about 12 min, script dry run about 1.5 min, OAuth check about 0.5 min. So **about 30–45 Actions minutes per video**, including one retry. | Verified (your run logs) |

---

## 3. Five candidate topics

View counts come from the developereducators.com aggregator, read on 15 Oct 2026, with its own relative dates.

### Topic 1 — Self-checking expense tracker *(recommended first)*
1. **Title:** *Build a Free Expense Tracker That Catches Its Own Mistakes* (58 characters)
2. **Audience:** freelancers, side-hustlers and small-business owners in the US, UK, Canada and Australia who track expenses for taxes.
3. **Problem → outcome:** spreadsheets silently accept typos, duplicates and wrong categories, and the errors surface at tax time. The viewer leaves with a free template that rejects bad entries, flags duplicates and shows a "checks passed" panel.
4. **Demand evidence:** *EASY Budget & Expense Tracker with Google Sheets* (Jeremy's Tutorials), about 1.06M views in roughly 2 years. Its v2 follow-up has about 220K views in roughly 10 months. Expense and budget tracking is an evergreen need with a yearly peak around tax season (the peak is my judgement; not measured with Trends).
5. **Competition:** high for "budget tracker", medium for the error-proofing angle (judgement).
6. **Monetization:** business/finance-adjacent ad rates (third-party ranges above). Also the template as a free download that grows an email list, then a premium version on your existing TinyPages store. Bookkeeping-tool affiliates later.
7. **Shareability:** high. Templates get saved, shared and bookmarked.
8. **Thumbnail:** a spreadsheet row glowing red with a big ✗ next to a green "CHECKS PASSED" badge. Text: **"IT CAUGHT IT"**.
9. **Opening 15 seconds:** "Your expense tracker will happily add a typo to your tax totals. In the next few minutes you'll build a free one that refuses bad entries, flags duplicates and tells you exactly what's wrong, before tax season does."
10. **Production difficulty: medium-high.** It needs a real Google Sheets screen recording. Untested assumption: Playwright can record a link-shared sheet without signing in. If that fails, the fallback is LibreOffice Calc or a guided screen recording.

### Topic 2 — The existing One-Cent video *(recommended second)*
1. **Title:** *Before You Automate: Test the One-Cent Boundary* (47 characters)
2. **Audience:** people automating approvals and finance rules; junior QA staff.
3. **Problem → outcome:** a rule passes the obvious tests and still approves the wrong request. The viewer leaves with a boundary test matrix and a free practice lab.
4. **Demand evidence:** none found that people *search* for this concept. Business viewers rarely type "boundary testing". It works better as suggested or follow-up content.
5. **Competition:** low (judgement).
6. **Monetization:** low to medium. The practice lab can collect emails.
7. **Shareability:** low to medium. The concrete $100.00 vs $100.01 visual is memorable.
8. **Thumbnail:** the current one ("THE ONE-CENT BOUNDARY TEST", $100.00 vs $100.01) already exists. Shorter text such as **"ONE CENT?"** would fit project policy better.
9. **Opening 15 seconds:** already recorded. It scores "weak" (32/100) on the advisory hook scorer, which has limited predictive value.
10. **Production difficulty:** none. It is rendered and passed QC. It only needs your review.

### Topic 3 — Safe AI agents in n8n
1. **Title:** *Make Your n8n AI Agent Ask Before It Acts (Human Approval)*
2. **Audience:** no-code automation builders and operations staff.
3. **Problem → outcome:** an agent sends the wrong email or payment. The viewer adds an approval step and proves it really stops.
4. **Demand evidence:** n8n beginner and agent tutorials range from about 200K to 1.2M views, for example *n8n Quick Start Tutorial* by n8n itself (about 510K) and *N8N Full Tutorial* by AI Foundations (about 419K). n8n officially documents [human-in-the-loop for AI tools](https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/index.md), so the feature is real.
5. **Competition:** very high for n8n generally, lower for the safety angle. Large creators dominate (e.g. NetworkChuck about 5.4M subscribers).
6. **Monetization:** strongest affiliate fit (n8n 30%, Make 35%). Business audience.
7. **Shareability:** medium.
8. **Thumbnail:** an AI robot hand frozen above a red "APPROVE?" button. Text: **"WAIT. APPROVE?"**
9. **Opening 15 seconds:** "AI agents are great until one emails the wrong customer. Here's how to make your n8n agent stop and ask you first, and how to prove it actually stops."
10. **Production difficulty: medium.** Self-host n8n free in Docker during the render job, record with Playwright. The engine already does browser recording.

### Topic 4 — CSV imports that break dates
1. **Title:** *Stop CSV Imports From Breaking Your Dates (Excel & Sheets)*
2. **Audience:** office workers and bookkeepers moving data between systems.
3. **Problem → outcome:** 03/04 becomes April 3 instead of March 4, and leading zeros vanish. The viewer leaves with a safe import checklist.
4. **Demand evidence:** Excel tutorials are among the most-viewed educational topics (1.3M–3.4M views on the top general videos). Demand for this *specific* problem is unverified.
5. **Competition:** high (judgement).
6. **Monetization:** business ad rates; can bundle with the Topic 1 template.
7. **Shareability:** medium. Very relatable pain.
8. **Thumbnail:** a calendar with two dates swapped. Text: **"WRONG MONTH"**.
9. **Opening 15 seconds:** "Open the same file on two computers and your dates can change months. Here's why it happens and a 3-step import that keeps them right."
10. **Production difficulty: low to medium.** It can run fully in a local browser lab with no sign-in.

### Topic 5 — AI coding agents for non-programmers
1. **Title:** *AI Coding Agents for Non-Programmers: What's Safe to Let Them Do*
2. **Audience:** curious business owners.
3. **Problem → outcome:** fear and hype around AI agents. The viewer leaves with a clear safe/unsafe checklist.
4. **Demand evidence:** very high. The top Claude Code videos have about 480K–2.4M views, e.g. Nick Saraev's 4-hour course (about 2.4M) and Simon Scrapes' *Every Claude Code Concept Explained for Normal People* (about 850K).
5. **Competition:** very high, and tools change monthly (trend risk).
6. **Monetization:** medium; affiliate fit is weak.
7. **Shareability:** high but short-lived.
8. **Thumbnail:** a terminal with a red "rm -rf" line crossed out. Text: **"NOT THIS"**.
9. **Opening 15 seconds:** "An AI agent can write code for you, and it can also delete your files. Here's the short list of what to let it do, and what to never approve."
10. **Production difficulty: high.** It needs paid tool accounts. Note: I am made by Anthropic, the maker of Claude Code, so any vendor comparison I write should be checked for neutrality.

### Comparison

| | Demand evidence | Competition | Money | Shareability | Evergreen | Engine fit |
|---|---|---|---|---|---|---|
| 1 Expense tracker | Strong (1M+ outlier) | High / medium angle | Medium-high | High | Yes | Medium (Sheets recording) |
| 2 One-Cent (existing) | Weak | Low | Low-medium | Low-medium | Yes | **Ready** |
| 3 n8n approval | Strong | Very high / lower angle | High (affiliates) | Medium | Medium | Good |
| 4 CSV dates | Indirect | High | Medium | Medium | Yes | **Best** |
| 5 AI coding agents | Very strong | Very high | Medium | High, short-lived | No | Weak |

### Why Topic 1 beats One-Cent as the first video
- **Discovery:** a new channel gets almost no suggested traffic, so its first views come from search. People search for expense trackers; nobody searches for "one-cent boundary".
- **Asset:** the template keeps paying off (email list, product, links from later videos). One-Cent's practice lab is less broadly useful.
- **Authenticity:** an expense and tax topic matches your real expertise. That is the strongest defense against "mass-produced AI content" judgements.
- **Sequencing:** One-Cent becomes the perfect video 2 ("You built the tracker; now prove its rules work"). It keeps its value and gains a ready-made audience instead of being discarded.

**Where One-Cent wins:** it is finished, verified and costs nothing more to produce. If speed matters more than discovery, publishing it first is defensible.

---

## 4. Realistic monetization path

1. **Months 0–6 (before ads):**
   - free template as an email-list magnet;
   - Make and n8n affiliate links in automation videos (Make 35% for 12 months; n8n 30% for 12 months), disclosed in each video and description as the FTC requires;
   - premium template or mini-course on your existing TinyPages store.
2. **Partner program:** 1,000 subscribers plus 4,000 public long-form watch hours. Timing is unknowable; do not plan finances around it.
3. **After joining:** ad revenue, plus memberships if the audience asks. Ad rates for business and spreadsheet topics are *published* as higher than general tech, but your actual rate depends on how much of the audience is in the US, UK, Canada or Australia, the season (Q4 is usually stronger), and video length (8+ minutes allows mid-rolls).
4. **Rule:** no invented income claims in videos or descriptions. The engine's gates already block uncited numbers.

---

## 5. Channel-configuration checklist and who can do what

**Current state:**
- The existing OAuth token has only the **youtube.upload** and **youtube.readonly** permissions (scopes).
- This session **cannot reach Google APIs**; its network is restricted.
- The GitHub Actions allowance is exhausted until about 1 Nov.
- So right now **I can configure nothing on the live channel.** No setting has been changed.

### A. I can do directly, with existing access
| Item | How |
|---|---|
| Titles, descriptions, chapters, tags, thumbnails, SRT | Built offline (Phase 1 checks + lesson package builder). |
| Channel description, keywords and positioning text | Drafted offline; you paste them into Studio. |
| Profile image (800×800) and banner (2560×1440 with safe area) | I can design both as image files for you to upload. |
| Upload privately, then set the thumbnail | Upload workflow is built and tested; needs Actions minutes, the merge, `YOUTUBE_UPLOAD_ALLOWED=1` and your typed approval digest. |
| Read channel/video info, verify the right channel | Read-only access works through the existing OAuth check workflow. |
| Analytics and retention analysis | From CSV files you export from Studio, using the retention reader planned in the integration roadmap. |
| Comment reply drafts | From comments you paste; never posted automatically. |
| Competitor tracking | Public data; ranking by outlier multiple (the ported `swipe.py` logic, Phase 3). |

### B. Needs new permissions or integration work
| Item | What's missing |
|---|---|
| Channel description and keywords through the API (`channels.update`) | A broader scope (`youtube` or `youtube.force-ssl`) at the next credential rotation. Note: the call **overwrites** fields that are left out, so it needs careful code. The channel *title* cannot be changed through the API. ([docs](https://developers.google.com/youtube/v3/docs/channels/update)) |
| Captions upload (`captions.insert`) | The `youtube.force-ssl` scope; 400 quota units per upload. Already built in the uploader, but off by default. ([docs](https://developers.google.com/youtube/v3/docs/captions/insert)) |
| Playlists, editing metadata after upload, scheduled publishing | Broader scope plus new code; scheduled public release would still require your approval. |
| Analytics API (CTR, retention, revenue) | Enable the YouTube Analytics API in the Google project, add the `yt-analytics.readonly` scope, and write a reporting module. |
| Posting comment replies | `youtube.force-ssl` scope plus new code. I'd recommend keeping replies manual or approval-gated. |

### C. You must do these in YouTube Studio
- **Phone verification** (custom thumbnails, videos over 15 minutes).
- **Google account 2-step verification.**
- **Channel name** "LogicScript" and **handle** (check @LogicScript availability).
- **Profile picture and banner upload.** The API docs do not list the profile picture as changeable.
- **Upload defaults:** Education category, English, comment moderation level.
- **Homepage layout:** trailer for non-subscribers, featured sections.
- **Partner program application and AdSense/payment and tax info** (in your own name).
- **Altered/synthetic content disclosure** decision per video (the uploader also sets the API field from your decision).
- **Copyright claims, monetization settings, and Test & Compare thumbnails.**
- **Manager access:** add access through Studio permissions rather than ever sharing a password.

**Draft positioning (for your approval):**
- **One-line description:** LogicScript: practical tutorials that make your spreadsheets and automations trustworthy, for small businesses, freelancers and anyone who can't afford a silent mistake.
- **Playlists:**
  1. Spreadsheet Systems That Don't Lie
  2. Test Before You Automate
  3. Safe AI Automation

---

## 6. 30-day plan (16 Oct – 14 Nov 2026)

| Week | Work | Who |
|---|---|---|
| 16–22 Oct | **Save both artifacts before 22 Oct.** Phone verification, 2-step verification, handle, profile image and banner (I'll design them). Check whether the Google app is in "Testing" mode. Approve merging the upload workflow. Review the One-Cent video and record decisions. | You + me |
| 23–29 Oct | Write the expense-tracker script by hand, with sources checked, and build the template. Feasibility test for recording Sheets. Rotate credentials, adding the `youtube.force-ssl` scope if you approve. | Me (offline) + you (Google Cloud) |
| 30 Oct–5 Nov | Actions resets about 1 Nov: OAuth check, then render the expense tracker (about 30–45 min). You review it. Upload privately → check it in Studio → **you** make it public. Template goes live on TinyPages. | Engine + you |
| 6–14 Nov | Publish One-Cent as video 2, linked from video 1. Cut 2–3 Shorts from existing renders. First Studio export (impressions, CTR, retention) → I analyze it. Pick video 3 (n8n approval or CSV dates) based on the data. | Engine + you |

**Cadence:** 1 long-form video per week. That fits about 30–45 Actions minutes per video inside the 2,000-minute monthly allowance, with room for checks.

---

## 7. Running the channel with the existing engine

| Need | Existing module | Status / gap |
|---|---|---|
| Weekly topic research | `channel/intelligence.py`, research pipeline | Exists. The live script quality gate is still unproven (1,045/1,200 words on the last run). |
| Data-driven selection | Outlier ranking (from the integration plan) | Phase 3: port `swipe.py`; collect data with the official API using an API key. |
| Production | `narration_pro`, `production_pro`, renderers | Verified on the One-Cent lesson. |
| Title and thumbnail quality | Phase 1 checks (merged) | Done. Real Test & Compare happens in Studio. |
| Scheduling and upload | Upload workflow (on a branch) | Built and tested offline; needs merge and minutes. |
| Analytics, retention, CTR | Retention reader (planned) + Studio CSV | Manual CSV first; Analytics API later (section 5B). |
| Comments | `channel/community.py` (drafts only) | Exists. Keep human approval. |
| Monetization tracking | — | Manual monthly review of Studio, affiliate dashboards and TinyPages. |

**Approval rules (unchanged):** nothing public, no spending, and no channel-setting change without your explicit approval. Every upload goes **private first**.

---

## 8. Blockers to direct channel management
1. **Artifacts expire 22 Oct.** Unless saved, the One-Cent video and its source audio are lost.
2. **This session cannot reach Google or the artifact storage host.** All live channel actions must run in GitHub Actions.
3. **The Actions allowance is exhausted until about 1 Nov.**
4. **Credentials are not rotated**, and the Google app may be in Testing mode (7-day token expiry).
5. **The current scopes are upload and read-only**, which is not enough for channel settings, captions, playlists or analytics.
6. **The upload workflow isn't merged into `main`**, so it can't be started yet.
7. **Google's docs currently contradict themselves** on whether API uploads from unaudited projects stay private. Upload privately and check in Studio.

---

## Sources
- [YouTube Partner Program overview & eligibility](https://support.google.com/youtube/answer/72851)
- [YouTube Partner Program availability](https://support.google.com/youtube/answer/7101720)
- [YouTube API — channels.update](https://developers.google.com/youtube/v3/docs/channels/update)
- [YouTube API — captions.insert](https://developers.google.com/youtube/v3/docs/captions/insert)
- [OutlierKit — YouTube RPM benchmarks by niche](https://outlierkit.com/resources/youtube-rpm-benchmarks/)
- [Creator Handbook — YouTube inauthentic content update](https://www.creatorhandbook.net/youtube-updates-monetization-policy-for-inauthentic-content/)
- [developereducators.com — best n8n videos](https://developereducators.com/best/n8n/)
- [developereducators.com — best Claude Code videos](https://developereducators.com/best/claude-code/)
- [developereducators.com — best Google Sheets videos](https://developereducators.com/best/google-sheets/)
- [developereducators.com — best Excel videos](https://developereducators.com/best/excel/)
- [n8n docs — human-in-the-loop for AI tool calls](https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/index.md)
- [Make affiliate program](https://help.make.com/affiliate-program.md)
- [Reditus — n8n affiliate program listing](https://getreditus.com/affiliate-programs/n8n)
