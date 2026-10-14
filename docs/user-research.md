# Caregiver app: simulated users and desk research

**What this is.** Ten *synthetic* personas, each walked through the caregiver app (14 Oct build, demo data
after `POST /demo/advance {"days": 11}`), plus a short desk review of published research on what family
caregivers and centre staff need. **These are not real user interviews.** The personas are composites written
from the research below. Treat the feedback as hypotheses to check with real caregivers, not as findings.
Some checks were run in the browser against the live API (noted "observed"); the rest are walkthroughs.

## The ten personas

| # | Persona | Situation | Main job for CareLoop |
| --- | --- | --- | --- |
| 1 | **Wei Ling**, 42, daughter | Works full-time in finance, lives 40 min from Mr Tan (Ang Mo Kio). Checks her phone at lunch. | "Tell me if something's wrong. Otherwise leave me alone." |
| 2 | **Kelvin**, 38, son | Works in Melbourne (3 hours ahead). Sends money, calls on Sundays, feels guilty. | Know how Dad is and help from far away. |
| 3 | **Mei**, 50, daughter | Runs a hawker stall. Reads Chinese best. Mdm Wong (Mandarin) shares the digest only. | A quick, reassuring look, in Chinese. |
| 4 | **Priya**, 29, granddaughter | Nursing student, detail-minded. Helps her grandfather with appointments. | The numbers, trends, and something to show the doctor. |
| 5 | **Hafiz**, 46, eldest son | Two kids at home, three siblings, one father. Ends up doing most of it. | Share the work fairly; see who's doing what. |
| 6 | **Mdm Lim Bee Hoon**, 67, wife | Lives with her husband; has her own diabetes and arthritis. Small text is hard. | Remember appointments and medicines; not be overwhelmed. |
| 7 | **Daniel**, 33, son | Lives with his mother but works night shifts; asleep when she takes her pills. | "Did she take her pill and check in today?" |
| 8 | **Maria**, 36, domestic helper | Live-in helper for Mr Tan's neighbour; does daily care; employer's family make decisions. | Know what to watch for and when to tell the family. |
| 9 | **Siti**, 31, AAC befriender | Covers a caseload of seniors with no family to call; heavy reporting load. | Find who needs a call today; stop re-typing records. |
| 10 | **Mr Rajan**, 52, AAC centre manager | Runs a small team; reports engagement and programme figures to the funding agency. | Centre-level picture; programme uptake; export for reports. |

## What each persona hit (walkthroughs)

1. **Wei Ling.** Liked the hero card ("Needs you") and the plain handover summary. *Friction:* to answer "did Dad take his pill today?" she scrolls past four sections to the timeline detail (observed). *Wants:* today's basics at the top; the next appointment.
2. **Kelvin.** The timeline and GP note draft let him act from Melbourne. *Friction:* no sense of Dad's local time or whether it's a good moment to call; nothing he can take on remotely (e.g. "book the polyclinic slot"). *Wants:* shared to-dos he can claim; Singapore time shown.
3. **Mei.** *Friction:* the whole caregiver app is English (observed: `lang="en"`, English UI). The suggestion line read "您喜欢singing": a Chinese sentence addressed **to the senior** with an English word in it, shown in the family app (observed). *Wants:* Chinese UI; text written to her, about her mother.
4. **Priya.** Liked the 30-day BP chart and the findings with their "based on N days". *Friction:* no medicine list (name, dose, since when); can't add the questions she wants the doctor to answer, and the GP brief leaves the questions blank. *Wants:* medicines in one place; questions that flow into the GP brief.
5. **Hafiz.** "I'll handle it" shows who took a handover, which helps. *Friction:* everything else (refills, appointments, visits) lives in a WhatsApp group; no way to split it. *Wants:* shared to-dos with owners and due dates.
6. **Mdm Lim.** *Friction:* body text at 15px is too small; many sections. *Wants:* bigger text; the next appointment and medicines up front; something for her own strain.
7. **Daniel.** *Friction:* same as Wei Ling: today's pill and check-in are not at the top. *Wants:* a "today so far" line with times.
8. **Maria.** Not a direct user today (no helper role). *Wants:* a simple emergency card: medicines, allergies, GP, address, 995. Flagged for later: a helper role needs its own consent design.
9. **Siti.** Liked the "worth watching" tiles and copyable befriending record. *Friction:* copies records one senior at a time. *Wants:* one export of every record for the reporting period.
10. **Mr Rajan.** *Friction:* the console is per-worker; no centre summary of check-in rates, handovers or programme uptake. *Wants:* a centre report with an export.

**Bug found while simulating (observed):** today's suggestion reasons (`why_it_fits`) are the engine's senior-facing wording ("You said you like…", "您喜欢…"), reused in the family app. Fixed in the app by writing family-voiced reasons from the same data.

## What the research says

| Need | What the source reports | In CareLoop |
| --- | --- | --- |
| Quiet, tiered alerts | Vendor guidance on remote monitoring recommends tiering alerts by severity and capping low-priority ones (e.g. 2–3 a week) to avoid alert fatigue ([Onix](https://health.onix-systems.com/insights/rpm-alert-fatigue-design/)); family can be the first line for low-severity checks ([Orbita](https://blog.orbita.ai/reducing-alert-fatigue-in-healthcare-by-engaging-the-at-home-care-team)). Both are vendors: design advice, not evidence. | Already the ladder's design (one weekly digest, rung 4, red flags). Kept. |
| The senior decides | Adult children rated monitoring tech higher than their mothers did and underestimated how much the mothers wanted to be involved; privacy was the top concern for both. The authors call for shared decision-making ([Berridge & Wetle, The Gerontologist, 2019](https://digital.lib.washington.edu/researchworks/items/9f827726-d4ad-49ea-b5b9-81c6f5133d26/full)). Telecare changes family relationships around dependence and privacy ([Vines et al.](https://researchportal.northumbria.ac.uk/en/publications/making-family-care-work-dependence-privacy-and-remote-home-monito/)). | Consent set on the senior's phone; app shows what's shared and why. New notes are visible to every linked contact. |
| Remote children need practical help | Remote adult children asked for information on services and entitlements, and help coordinating care; strong interest in a "case manager" style service ([Veil, Soar & Su](https://research.usq.edu.au/item/q20wy/care-provision-expectations-of-remote-adult-children-of-ageing-parents)). | Shared to-dos; next steps after a handover; support resources. |
| Care is uneven between siblings | An industry survey reported one sibling doing all or most care in 41% of families, only 3% splitting equally (Home Instead, via [Tri-City News](https://tricitynews.com/living/seniors-study-sheds-light-on-siblings-who-care-for-senior-parents-3009529); industry-sponsored). Guidance: agree one main contact for doctors ([Caregivers.com](https://portal.prod.caregivers.com/articles/questions-caregivers-should-ask-at-an-elderly-parents-doctor-appointment-137912.htm)). | Shared to-dos with an owner each; who's handling each handover. |
| Doctor visits | Keep one medication list with doses; write the top 3–4 questions; note changes since the last visit; get instructions in writing afterwards ([Caregivers.com guide](https://portal.prod.caregivers.com/Articles/How-to-Talk-to-Your-Doctor-A-Guide-for-Caregivers-and-Elders-132484.htm)). | Medicines list; questions for the doctor that flow into the GP brief; next appointment; notes after the visit. |
| Family role in hypertension | Family-based interventions improved adherence and BP control in older adults; caregivers often act as medication reminders ([touchCARDIO, 2026](https://touchcardio.com/wp-content/uploads/sites/4/2026/06/7.-touchCARDIO-D-25-00048_54-60.pdf)). Forgetfulness and access are common barriers ([CiencCuidSaude](https://periodicos.uem.br/ojs/index.php/CiencCuidSaude/article/download/21745/pdf_8)). | Today's pill status at the top; refill reports; weekday miss patterns. |
| Singapore caregivers work, and neglect their own health | Of 7,692 residents aged 48–79 surveyed (Nov 2024), about 1 in 7 were caregivers; 45.24% of caregivers worked full-time; 59.23% managed the recipient's finances, 44.07% arranged care services; 33.99% had two or more chronic conditions; only 50.09% knew of respite care and 82.83% of those had never used it ([SMU ROSA, Apr 2025](https://news.smu.edu.sg/news/2025/04/07/1-7-older-adults-juggle-work-chronic-illness-and-unpaid-caregiving)). An older NTUC survey (2013) found 60% of working caregivers struggled to balance work and care ([HR Online](https://www.humanresourcesonline.net/62-of-singaporeans-still-have-no-flexibility-at-work)). | "Looking after you": a private check-in for the caregiver and Singapore support (AIC, respite, grants). |
| Where to get help in Singapore | AIC hotline 1800-650-6060 (Mon–Fri 8.30am–8.30pm, Sat 8.30am–4pm); respite options include day care and nursing home respite; the Home Caregiving Grant ([AIC contact](https://aic.sg/contact-us), [MOH caregiver support](https://moh.gov.sg/caregiver-support), [MOH respite options](https://www.moh.gov.sg/newsroom/variety-of-respite-care-options-available-for-caregivers-of-frail-seniors/)). | Listed in "Looking after you", with links. Check amounts with AIC before quoting them on a slide. |
| Caregiver apps | Small studies suggest app-based support can help caregiver wellbeing; feature lists are mostly vendor claims ([JMIR mHealth 2021](https://mhealth.jmir.org/2021/1/e21708/PDF)). | A light check-in plus pointers to real services, not a wellbeing programme. |
| AAC staff | Heavy data entry and many reports to the funder; teams are small (main brief, "What AAC staff say": Chan et al. 2026). | Caseload export in one file; centre report. |

## Features: what was built from this

| Feature | From | Status |
| --- | --- | --- |
| **Today so far** at the top of Today: checked in (time), pills, BP (if shared), Singapore time | Wei Ling, Daniel, Kelvin; adherence research | Built |
| **Care plan tab**: next appointment, questions for the doctor (into the GP brief), shared to-dos with owners, medicines and refill reports, emergency card | Priya, Hafiz, Kelvin, Mdm Lim, Maria; doctor-visit and sibling research | Built (`GET/PUT /senior/{id}/care-notes`, added, needs team OK) |
| **Looking after you**: a private weekly check-in for the caregiver (kept on this device), Singapore support with links | Mdm Lim, Hafiz; ROSA, AIC, MOH | Built |
| **Bigger text** setting | Mdm Lim | Built |
| **Family-voiced suggestion reasons** | Mei (bug) | Fixed |
| **Caseload export** (one CSV of every senior's 7-day record) and **centre report** | Siti, Mr Rajan; AAC research | Built |
| Chinese UI for the caregiver app | Mei | Not yet: needs `care.*` strings in `web/shared/i18n.ts` |
| Helper (domestic worker) role | Maria | Not yet: needs its own consent design |
| Push notifications with the app closed | Wei Ling, Daniel | Not yet: needs hosting and a push service |

## Re-run on the new build (observed, 14 Oct)

Each persona's main task was replayed in the browser against the live API after the changes:

| Persona | Task | Result |
| --- | --- | --- |
| Wei Ling, Daniel | Did Dad check in and take his pill today? | Answered at the top of Today without scrolling: "Checked in 8:30 am · Pills taken · BP 156/90". |
| Kelvin | Help from Melbourne | Saw "1 nobody has taken yet" on Today, opened the plan, tapped "I'll do it" on the refill; Wei Ling's view shows Kelvin owns it. Singapore time is shown, with his own time when he's abroad. |
| Priya | Medicines and questions for the doctor | Medicines list (amlodipine 5 mg, morning, since Mar 2024) and the 17 Oct "running low" report; her question appears on the GP brief PDF under "Questions for this visit (from family or centre)", with the visit date in the header. |
| Hafiz | Share the work | Shared to-dos with quick-add chips, an owner each and a per-person count. |
| Mdm Lim | Read it comfortably | "Bigger text" in You enlarges the app on her phone; next visit sits on Today. |
| Mei | Read it in Chinese | **Not fixed.** The suggestion reason is now family-voiced English ("They like singing") instead of the senior's Chinese. A Chinese caregiver UI is still to do. |
| Maria | Emergency card | Allergies, family doctor (tap to call), home address, notes, and a 995 button in the plan. A helper role is still to do. |
| Siti | One export for her reports | Report tab: "Export befriending records (CSV)" for the whole caseload, with a UTF-8 BOM so Excel shows Chinese words. |
| Mr Rajan | Centre picture | Report tab: seniors, check-ins answered (100% this week), quiet days logged (14), handovers and red flags, a per-senior table with "worth watching". |
| Any caregiver | Their own strain | You tab: a private "How are you doing?" (kept on the phone), AIC hotline, respite options, grants, SOS 1767 ([findahelpline](https://findahelpline.com/organizations/samaritans-of-singapore)). |

**Found for other owners:** the senior-facing Chinese suggestion reads "您喜欢singing" because the senior's likes are stored in English and dropped into the Chinese template (Vibu owns the wording in `backend/env/places.suggest()`; translating likes may sit with Mingyu's language layer).
