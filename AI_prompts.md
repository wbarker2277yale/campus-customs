# AI Prompts — Campus Customs Multi-Agent Operations

A record of the prompts I gave the AI assistant (Claude Code) for this assignment, grouped by problem. Spelling, typos, and names (files, folders, tools) have been corrected. Where my original wording was unclear, a clarified version is shown in [brackets]. Each problem notes what the first prompt lacked, which the follow-ups supplied.

---

## Problem 1 — Vibe Coder Prompts

**What the first prompt lacked:** it named the problem but not the file or its format; the follow-ups gave the file name and the log format used in this class.

**Prompt 1:**
> Use this to understand the setup; the prompts will be in my own words.
>
> [Clarified: Sent with a screenshot of the assignment's "Scenario and data" section only, covering the scenario, agent roles, data, and shop rules. No problem statements were included. Read it for background and build nothing yet.]

**Prompt 2:**
> The data is downloaded.

**Prompt 3:**
> Problem 1: Vibe Coder Prompts.

**Follow-up prompts:**
> AI_prompts.md.
>
> [Clarified: Record the prompts in a file named `AI_prompts.md`.]

> Use the same format as previous homeworks for how prompting is handled.
>
> [Clarified: Match the prompt log from earlier homeworks in this class (Homework 3's `AI_prompts.md`).]

---

## Problem 2 — Study the Campus Customs Database

**What the first prompt lacked:** it asked for a copy and a look at the data, but not for the ticket relationships or the field list; the follow-ups added both.

**Prompt:**
> Problem 2: Study the Campus Customs database. Look through the data and make a new copy.
>
> [Clarified: Copy `campus_customs.db` into the project's `data/` folder and make the working copy `data/campus_customs_new.db`.]

**Follow-up prompts:**
> Study the tickets and their relationships.

> `output/harness.md` will list the fields for each table, with one short line about why each matters.

---

## Problem 3 — MCP Server

**What the first prompt lacked:** it did not settle folder and file names, where the project lives, which further tools the agents need, or what a "payment" is in a school exercise; the follow-ups covered each.

**Prompt:**
> Build an MCP server using FastMCP on `data/campus_customs_new.db`. I won't run it; every agent will call its tools. Put three tools in it for now; more are coming. Invent no data. List the tools in `output/harness.md`, and for each tool explain which ticket it unlocks, with one sentence on why it helps. Don't be vague; be specific. Feel free to use my Seastreak style guide for the wording. Include `mcp/README.md`. Throughout this, correct the names I use.
>
> [Clarified: "Names" means file, folder, and tool names. Following the Lecture 9 build, the server is `mcp/mcp_server.py`, not `MCP_server/`.]

**Follow-up prompts:**
> By "phrases" I mean names.

> Use the names that are standard from previous builds in this class, where applicable.

> Why is it running there? This should all be in Homework 5 in AI Foundations.
>
> [Clarified: The session had opened in the Probability Homework 5 folder. Move the project into `AI Foundations/Homework 5` and run the session from there.]

> I want all the tools you need. Follow the protocol for recording tools needed. But I have only asked you to test the existing tools so far.
>
> [Clarified: Record every tool the agents still need in `output/harness.md`, in the same format as the existing tools (what each does, which ticket it unlocks, and one sentence on why it helps). Do not build them yet.]

> What problem are we on? And go, by the way.
>
> [Clarified: Build every tool recorded as needed in `output/harness.md`.]

> What do you mean by payment? This is a school assignment.
>
> [Clarified: "Payment" means a simulated database update (a `payments` row, a lower cash balance, the bill marked paid). No real money moves.]

> OK, assume my approval for simulated payments.

> Tell me when you're ready for the next problem.

> What are you done with?

---

## Problem 4 — Add the MCP Server to the Vibe Coder

**What the first prompt lacked:** where to save the evidence, and how to keep the vibe coder's own tool calls separate from scripted ones.

These prompts were sent during Problem 3, before Problem 4 was named; they are its work.

**Prompt:**
> Add the MCP server to this project so the vibe coder can call the tools. Put the connection settings in `.mcp.json` at the project root. Test each tool.
>
> [Clarified: The vibe coder is Claude Code, the AI assistant building the project. The swarm is the team of agents (Boss, Inventory, Accounting, Facilities, Customer Service) that the backend will run. Both call the same MCP tools.]

**Follow-up prompts:**
> Save evidence in `output/mcp/smoke.json`. For every tool, show the prompt, the tool name, and the tool output.

> OK, run the prompts and tell me what you can't do.
>
> [Clarified: As the vibe coder, call each smoke-test prompt's tool through the `campus-customs` MCP connection, then list what the current three tools cannot do.]

> Problem 4: Add the MCP server to the vibe coder and test each tool.

> I feel we already did this.
>
> [Clarified: `.mcp.json` at the project root already connects the `campus-customs` server, and Claude Code has called its tools, so Problem 4 is done.]

> OK, differentiate them in the record.
>
> [Clarified: In `output/mcp/smoke.json`, keep the tool calls Claude Code made itself (`vibe_coder_calls`) separate from the calls the smoke-test script made (`script_calls`).]

---

## Problem 5 — Agent Team

**What the first prompt lacked:** the shop rules themselves; the prompt questions below (logged after Problem 7, when they were answered) supplied them one at a time.

**Prompt:**
> Now we will build the agent team for Campus Customs using PydanticAI. It comprises Boss, Inventory, Accounting, Facilities, and Customer Service, with prompts, models, and agent loops, so they can delegate work to each other with full connectivity. The prompts go in `backend/prompts/`, one file per agent; the data types go in `backend/models.py`; and the agent files go under `backend/`. Use the Portkey API key, and `gpt-6-luna` is the only model every agent uses. The prompts will be written in my own words and include the shop rules the agents need. Grades are higher for more specific prompts, so grill me on that. Any tools the agents need to work the open tickets get added to the MCP server. The facts come from the same server, over `data/campus_customs_new.db`, with no second shop-tools layer that bypasses it. Wire the agents to append to `output/audit_trail.json` as they run, recording enough at each loop step for a later audit; the file is appended to, never wiped. `output/harness.md` will list each agent, each MCP tool (including any added here), and the tables those tools use, plus a safety section with the guardrails a real business would want before agents dealt with genuine customers and money, and limits (my invention left to you) to curb token use. Update `mcp/README.md` so the tool list matches what exists.
>
> [Clarified: "audit_trial" is `output/audit_trail.json`; "MCP_server/README" is `mcp/README.md`; "luna 6" is `gpt-6-luna`.]

---

## Problem 6 — Plan the Three Tickets

**What the first prompt lacked:** it arrived mid-task without the problem number; the follow-up confirmed it as Problem 6.

**Prompt:**
> Before wiring the backend, write a forecast of what you would expect each agent to do on each open ticket, in `output/desk_tickets.html`. The page opens with a double-click and has one tab per ticket (101, 102, 103), plus empty Cash and Reflection tabs for later. On each ticket tab, fill in only the Expected section and leave room in the Actual section for after the agents run. In the Expected section I will write, in my own words, which agent should be called first, the delegations I expect, and the tools I expect the run to use, remembering that I will score low if I expect every specialist to be called on every ticket.

**Follow-up prompt:**
> That is Problem 6. Plan the three tickets.

> Save the questions for later.
>
> [Clarified: The 13 grilling questions for the agent prompts are saved in `backend/prompt_questions.md`, to answer after Problem 7.]

---

## Problem 7 — Backend Routes

**What the first prompt lacked:** it asked to be questioned but did not list the routes; the later prompt listed the six routes and the start command.

**Prompt:**
> Grill me one by one on Problem 7, backend routes (don't build yet). The React dashboard, built later, needs a backend in `backend/main.py`.

**Follow-up prompts:**
> a
>
> [Clarified: Question 1 — the dashboard watches each run live, step by step, through a streaming route.]

> It's more in tune with the spirit.
>
> [Clarified: The reason for answer 1 — live streaming fits the spirit of the assignment, which is to watch the agents at work.]

> a, only I am using this.
>
> [Clarified: Question 2 — Approve and Reject buttons, with the approver's name filled in from `APPROVER_NAME` in `.env`, because Will is the only user.]

> Yes.
>
> [Clarified: Question 3 — add a Reset button on the dashboard, with confirmation, blocked during a run, and leaving the audit trail intact.]

> I don't do terminal.
>
> [Clarified: The reason for answer 3, and a standing rule — everything Will does must be possible from the dashboard; the vibe coder runs any commands.]

> a, follow the rules.
>
> [Clarified: Question 4 — the dashboard reads shop data through the MCP server, like the agents, because of the no-bypass rule.]

> Follow the rules.
>
> [Clarified: Question 5 — a Run button per ticket plus "Run all open tickets," one run at a time, which keeps to the reset-before-a-full-run rule and the one-ticket-at-a-time limit.]

> a, more in tune with the assignment.
>
> [Clarified: Question 6 — a run-history view built from the audit trail.]

> a, I don't want runs I haven't asked for.
>
> [Clarified: Question 7 — approvals and rejections never start a run on their own.]

> OK.
>
> [Clarified: Answer the 13 prompt questions next, one at a time; `backend/main.py` waits for a go.]

> Is the live run requested in the prompt for Problem 6? If not, we should do Problem 7.
>
> [Clarified: Problem 6 asks only for the plan; the Actual sections wait for a later run. Go ahead with Problem 7.]

> Halt.

> Paste what I wrote for Problem 7 so far.

> Problem 7, backend routes. The React dashboard, built later, needs a backend I can call. It will be called `backend/main.py`. Use FastAPI and add routes that do this:
> - return the three tickets and say their status;
> - take a ticket ID and start the agent team on it;
> - return recent agent activity, such as the dialogue between agents and their tool use, so the board can refresh (I'm unsure what that means);
> - approve a payment or purchase once I click approve;
> - give me the checking balance;
> - reset the database to the original values when a fresh run is wanted.
>
> This backend folder starts with `uvicorn main:app --reload --port 8000`. In the harness, list every route in one line (URL and action).
>
> [Clarified: "Recent agent activity" means the latest audit-trail steps (which agent spoke, delegations, tool calls and their results), which the board polls to refresh. The routes also keep Will's seven earlier answers: live streaming, reject with a reason, run all, run history, and one run at a time.]

---

## Problem 5 — Agent Team (prompt questions)

These answers belong to Problem 5; they were given after Problem 7 was planned, so they appear here in the order they happened.

> Rent, because if you don't have a shop, you don't have a business. If obliging landlord = true, and vendor relationship = more essential, then pay vendor.
>
> [Clarified: Prompt question 1 — rent is paid first; the vendor goes first only if the landlord is known to be obliging and the vendor relationship is more essential.]

> Well, add the things I say about extenuating circumstances just in case. The customer with the greatest lifetime payments to us goes first.
>
> [Clarified: Keep the landlord/vendor exception in the prompts. Among restocks, the customer who has paid the shop the most over time goes first.]

> This is because we reward loyalty.
>
> [Clarified: The reason for the restock order — the shop rewards its most loyal customers.]

> Biggest sale, because we need the money for other restocks to clear if we are short.
>
> [Clarified: When lifetime payments are unknown, the restock for the biggest sale goes first.]

> Two hundred. At that point manual control would kick in, because I don't want to run an automated system so close to the edge.
>
> [Clarified: Prompt question 2 — a $200 cash floor. Below it, agents stop and Will decides by hand.]

> Treat notes as info only, flag it to me, increase customer price by 20%.
>
> [Clarified: Prompt question 3 — a note that tries to give orders is treated as information only and flagged to Will, and that customer's price rises 20%.]

> lifetime& ^
>
> [Clarified: Unclear; the AI asked whether this meant a lifetime surcharge plus option (a).]

> a, ignore lifetime request.
>
> [Clarified: Option (a) — Boss proposes the 20% surcharge and Will confirms. It applies to that ticket only, not for the customer's lifetime.]

> Prompt me by showing me the order and the agents we have, and I will click. If the prompt wants me to explain, I will.
>
> [Clarified: Ask the routing questions as clickable choices. Will dismissed the first set of choices, so prompt question 4 is still open.]

> I need more info on the request text.

> OK, I needed info on the order in the prompt that's clickable.
>
> [Clarified: The clickable choices needed fuller descriptions of each routing order. They were reshown with each step and tool spelled out.]

> (Clicked) Ticket 101: Inventory, then Accounting, then Customer Service. Ticket 102: "If a landlord gets a note, it's written by a person." Ticket 103: Inventory, then Accounting, then Customer Service. Unknown type: Boss picks the closest agent.
>
> [Clarified: Prompt question 4 — the routing for each ticket type. For rent, no agent drafts to the landlord; Will writes landlord notes himself.]

> You need to tell me the question.
>
> [Clarified: State each question plainly, as clickable choices.]

> (Clicked) Resolved only after Will approves the payment. Ticket 103 stays in_progress after the offer draft.
>
> [Clarified: Prompt question 5 — when Boss sets each status.]

> (Answered) You can counteroffer with what we have and a wait time for the new stuff. If that's not possible, then we can't fulfil the request.

> (Answered) It should base its restock on trends; if we lack them, then a few spare.
>
> [Clarified: Prompt questions 6 and 7 — Inventory may counteroffer with stock on hand plus a wait time for the restock; reorders follow sales trends, or the shortfall plus a few spare when no trend data exists.]

> (Clicked) Other sizes count in a counteroffer. Spare stock = 10% of the shortfall, minimum 1.

> (Answered) Bulk starts at 10 units. Up to 20% off without asking. Minimum margin: anything above cost plus labor. Invoice 501: pay the vendor first and hold the rent, because you can pay rent up to ten days late.
>
> [Clarified: Prompt questions 8–10.]

> (Answered) Assume we don't have labor costs, due to the narrow nature of our exercise.
>
> [Clarified: The minimum price is anything above unit cost.]

> (Clicked) Rent: request it, flagged below the floor. Dates: approximate only. Discounts: drafts may name up to 20% freely. Tauhid: offer an M or wait for the S.
>
> [Clarified: Prompt questions 11–13.]

> (Clicked) Formal tone, team sign-off.

> (The AI wrote the five prompts in `backend/prompts/` from Will's 13 answers, keeping his words in quotation marks, and made the tool changes those answers needed.)

---

## Problem 8 — Agent Dashboard

**Prompt:**
> Problem 8: agent dashboard. Now build `frontend/` with React, Vite, and TypeScript. The page calls the routes built in Problem 7. The board shall have, at minimum:
> - the three tickets;
> - a way for me to choose which ticket is worked on first;
> - the agents shown working and talking;
> - each ticket's resolution marked;
> - a visible summary of agent activity per ticket;
> - human approval when asked;
> - a live checking-balance tracker.
>
> Make it elegant and in the style of J. Press in 1960. Give each agent a heraldic crest, following the rules of heraldry roughly but updated graphically for the 1960s, and Yale-like in style. The frontend talks to the backend on port 8000, and the backend allows the Vite page's origin (localhost:5173 or similar) so the browser can call the routes it needs. Start the board with `npm run dev`. Open it when done, and write `output/design.md`.

---

## Problem 9 — Run the Agents and Compare

**What the first prompt lacked:** the Cash tab, the resolved-ticket files, and the harness; the follow-ups added them, then asked for the board to stop freezing and for the write-ups to match the final run.

**Prompt:**
> Problem 9: resolve the tickets. Before testing the run, reset the working database (`data/campus_customs_new.db`) for a fresh start. Note the starting checking balance, then, and only then, run all three agents until the tickets are resolved. Then open `output/desk_tickets.html` from Problem 6 and fill the Actual section from the run: which agents worked when, the reasons for delegation, and the reasons for the tools they used. Keep the Expected section so we can compare.

**Follow-up prompts:**
> On the Cash tab, itemise the money: the starting checking balance, how cash changed for each ticket and why, and the ending balance (matching `cash_accounts`). Wrong cash numbers will lose me points. Output `output/resolved_tickets.json`, with a record for each ticket ID showing its final status, a short outcome, what each agent contributed, and the human approvals. Output `output/resolved_board.html`, and append them to `output/audit_trail.json`. Finish the harness so it covers the tables, the tools, the agents, the routes, the dashboard, and the safety rules.

> Open in Safari.

> So slow.

> It's stalled.

> Make it more efficient, make it fit on my screen, and do the expected-versus-actual comparison.
>
> [Clarified: Will approved both simulated payments himself on the board during the run. The first pass crashed on the 1,500-token cap per response; the cap was raised to 6,000 with low reasoning effort, and tickets 101 and 102 were rerun to resolution. Ticket 103 stays in progress, waiting on the club.]

> Stuck again.

> Simulate it and fix it up on your end before you send it to me.

> Make it run successfully in your simulation.
>
> [Clarified: Test the whole board flow before handing it back. The AI ran the real backend on a scratch database and scratch audit trail (port 8010, board on 5180), replaying the recorded Problem 9 agent steps at about an eighth of real speed, with no model calls. It drove the board as Will would: Work all, approve both payments, Work all again, Restore opening day, run one ticket, decline with a reason, and reload mid-run. It fixed five problems:
> 1. The transcript scrolled the whole page, which could no longer scroll back.
> 2. A dropped live stream left the board frozen after the run ended.
> 3. Long model calls showed no sign of life; a heartbeat line now shows them.
> 4. The approvals panel flagged the wrong payment as below the floor.
> 5. The cash tag's floor message was wrong once nothing was waiting.
> Will's real Problem 9 database and audit trail were not touched.]

> Still looks stuck. Look at the page and determine the issue.
>
> [Clarified: The board was blank because the four resolution records appended after Problem 9 (written by "report", not an agent) were counted as a run, and drawing a crest for "report" crashed the page. Fixed: `/api/runs` now counts agent runs only, the board skips unknown names, and an error boundary shows a message instead of a blank page.]

> Go go go go.

> It hasn't moved in half an hour.

> It's not moving now.

> It's been like this. (Sent with a screenshot of `output/resolved_board.html`.)
>
> [Clarified: The screenshot was the static report page, which never moves; the live board is http://localhost:5173. A 103 run started from the board at 01:26 had stopped at 01:29 on a Portkey server error (500); nothing was stuck. The reports were rebuilt to include that run.]

> It's clearly stuck. Fix it.
>
> [Clarified: Boss's final report on ticket 103 took 4.5 minutes; the model wrote 6,000 tokens of text before filing the report. Fixed with a fixed closing instruction after every prompt (file the report at once, never as plain text first) and a 90-second limit on each model call, with one retry (later shortened to 15 seconds with three retries).]

> Why do I still have a ticket open if it says complete?
>
> [Clarified: "Completed" meant the run finished, not the ticket. Ticket 103 stayed in progress under Will's rule that it waits for the club's answer.]

> OK, clearly the rule needs to change, and it needs to be fixed.
>
> [Clarified: Boss now resolves a `price_override` ticket once the offer draft is saved, and Customer Service saves only one draft per ticket. The board now says "run finished; ticket is now …" instead of "completed". Ticket 103 was rerun once: resolved in 43 seconds, with no new draft and no money moved.]

> Go.
>
> [Clarified: Restart the backend after it reached its 2-hour limit.]

> OK, all resolved.

> Open my Campus Customs website.

> Reset the website and let's run it again.

> Open the game.

> How's it doing?
>
> [Clarified: "The game" is the Campus Customs board. The run on all three tickets was still going.]

> Open the game again.

> Is there an ability to reset it?

> Should there be?
>
> [Clarified: Yes. Problem 7 requires a reset route, and the board's "Restore opening day" button calls it.]

> It seems frozen again.

> Why does it wait so long? It seems like it should run much faster.
>
> [Clarified: Every tool call takes milliseconds; the waits are calls to `gpt-6-luna` through Portkey, which usually return in 2 to 6 seconds but sometimes stall. Each model call is now cut at 15 seconds and retried up to three times.]

> It looks like it's done and the agents aren't doing anything, but it still says "Awaiting Signature" for something I signed. Look at it and tell me what is wrong.
>
> [Clarified: Boss had set ticket 102 to awaiting approval before Will signed, and approvals never start a run. The board now shows "Signed · Boss to close" with a "Close this ticket" button.]

> When it's done, should the closing screen come up?

> I just don't understand what the secondary page is.
>
> [Clarified: The board is the app; `output/desk_tickets.html` and `output/resolved_board.html` are the write-ups, which do not update live.]

> Open the write-up pages.

> Rebuild them from the new run.
>
> [Clarified: The Actual sections, the Cash tab, `resolved_tickets.json`, `resolved_board.html`, and the board screenshots were rebuilt from the run of 14 October (reset at 14:17; all three tickets resolved; checking $3,400 to $160).]

---

## Problem 10 — Reflection

**What the first prompt lacked:** my own draft had no ticket-by-ticket detail and got two facts wrong; the follow-ups asked the AI to improve it and then to put it into three paragraphs in my style.

**Prompt:**
> What is the reflection part, and where do I write it?

**Follow-up prompts:**
> Open the page where I write the reflection.

> It doesn't seem I can write anything there.
>
> [Clarified: The Reflection tab now has a writing box and a Save button. The backend serves the page at http://localhost:8000/output/desk_tickets.html#reflection, and Save writes the text into the tab and into `output/reflection.md`.]

> Create a draft of answers to the reflection questions in a text file.
>
> [Clarified: The AI drafted answers from the run's records (the audit trail, the database, and `desk_tickets.html`) in a text file outside the project, for reference.]

> Improve this:
>
> It seems that things mostly went as expected. There were a few things that did not work in the digital simulation that might have worked better in real life. For instance, I had a counteroffer feature that would have sent a counteroffer to someone asking for a big discount that did not work because there was not a real person to send the counteroffer to.
>
> The predicted course of action only differed from expected in ticket 1, where the requested t shirt was never ordered.
>
> This may have been simpler as one agent, as there was a lot of down time waiting on agents to communicate. They also seemed not to be individually able to grasp the actual whole problem they were facing, which made them make strange decisions sometimes.
>
> A more efficient version of this would help Campus Customs if they were facing a large number of very basic orders online. It might also help them better keep track of inventory and could improve user satisfaction on the website.
>
> It would not help them if Campus Customs faced an AI backlash, if it wanted to cultivate a more old-world image, or if it needed AI to analyze its business fundamentals.
>
> [Clarified: My own draft. The AI tightened it, corrected two points the run contradicted (ticket 103 also differed from the plan, and counteroffers stay drafts by design), and marked places for me to add detail.]

> Translate this into three short prose paragraphs using my style guide.
>
> [Clarified: The AI rewrote the improved version as three paragraphs in my style guide's manner. I added my reason for approving the rent and saved the result in the Reflection tab.]

> OK, it's in.

---

## Problem 11 — Submit to GitHub

**What the first prompt lacked:** it did not say what the required file layout meant or what to do first; the follow-ups asked for the fixes, then for the steps one at a time.

**Prompt:**
> Also, I don't remember what this means: "The final problem's text. You said the last problem shows the repo's file tree."

**Follow-up prompts:**
> OK, go on the fixes, but I can't do the report until the website works well and stops freezing all the time.
>
> [Clarified: Match the assignment's file layout, which differed from names chosen earlier after the Lecture 9 build:
> - `mcp/mcp_server.py` became `mcp_server/server.py`, and `mcp/README.md` became `mcp_server/README.md`;
> - `output/mcp/smoke.json` became `output/mcp_smoke.json`;
> - one `requirements.txt`, `README.md`, and `.gitignore` were added at the project root, with one shared `.venv`;
> - `resolved_board.html` gained a screenshot of the board for each ticket.
> Model calls now time out and retry instead of hanging. Earlier entries in this log keep the old names.]

> OK, walk me through the next steps, step by step.

> OK.
>
> [Clarified: The public repository https://github.com/wbarker2277yale/campus-customs was created.]

> Yes.
>
> [Clarified: Approval to push. The repo URL is in `output/github_url.txt`, and `hw5.zip` was built from the pushed commit.]

