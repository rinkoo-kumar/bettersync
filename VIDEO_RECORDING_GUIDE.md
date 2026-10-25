# Video Walkthrough Recording Guide & Teleprompter
**BetterUp AI Automation Engineer Take-Home Exercise**

---

## 🎬 Two Easy Ways to Produce Your Video Walkthrough

You have two ready-to-use options to produce your demo video for **Jessica Brewer** (`jessica.brewer@betterup.co`):

---

### Option A: Interactive Animated Player (`video_demo.html`) — *Easiest & Cleanest*

We built a self-contained video player in [`video_demo.html`](file:///D:/Projects/ai_assignment/video_demo.html).

1. **Open the Player**: Double-click `video_demo.html` or open it in Google Chrome / Microsoft Edge:
   ```powershell
   Start-Process chrome.exe "D:\Projects\ai_assignment\video_demo.html"
   ```
2. **Start Screen Recorder**:
   * **Loom** (recommended by BetterUp prompt): Open [Loom](https://www.loom.com) and select "Record Screen".
   * Or **Windows Built-in Game Bar**: Press `Win + Alt + R` to start instant HD recording (press `Win + Alt + R` again to stop). Recorded MP4 is saved directly to your `Videos/Captures` folder!
3. **Hit "Play Video"**: The player automatically types commands, streams the terminal execution output, scrubs through the chapters, and displays live synchronized narration subtitles.
4. **Speak Along or Mute**: You can speak along using the subtitles as a teleprompter, or let the subtitles speak for themselves!

---

### Option B: Live Terminal Recording (`run_demo.py`)

If you prefer to show your live PowerShell terminal:

1. **Open PowerShell** in `D:\Projects\ai_assignment`:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
2. **Start Loom or Windows Screen Recorder** (`Win + Alt + R`).
3. **Execute the Walkthrough**:
   ```powershell
   python run_demo.py
   ```
4. **Follow the 3-Minute Script Below**:

---

## 🎙 3-Minute Speaker Script & Teleprompter

```markdown
[0:00 - 0:40] Introduction & The Problem
"Hi Jessica, today I'm demonstrating BetterSync, the People systems orchestration engine 
I built for BetterUp's onboarding workflow.

Rather than building a brittle point-to-point automation or an open-ended chatbot, 
I targeted the highest-leverage operational bottleneck: Unified Change Propagation, 
Invariant Gatekeeping, and Claude as an agentic exception handler.

Today, when a candidate signs an offer and then shifts their start date or updates their address, 
or an off-cycle hire is created directly in Workday, downstream systems fall out of sync. Laptops get 
shipped to old addresses, Okta accounts activate on wrong dates, and nobody catches missed T-7 day milestones."

[0:40 - 1:25] Scenario 1: Post-Offer Change Propagation
"Let's look at Scenario 1 in the terminal.
Elena Rostova accepts an offer for Nov 2, but later moves her start date to Nov 16 and updates 
her residential address to 450 Mission Street.

In BetterSync, this event is captured, schema-normalized, and rippled across Workday Core HCM, 
Okta scheduled activation, and ExpoIT hardware logistics in one atomic, idempotent flow. 
Zero manual IT tickets required."

[1:25 - 2:05] Scenario 2: Bad Data Cascades & Claude AI Triage
"In Scenario 2, we show how we prevent bad data cascading. 
Ashby has '100 main street ste 400', while Workday has '100 Main St, Suite 400'. 

Instead of throwing an error or creating a duplicate order, our Claude Agentic Resolver is invoked 
via Model Context Protocol. It reasons over US Postal standards, confirms semantic equivalence with 
96% confidence, and auto-resolves the discrepancy to the standardized format, preventing FedEx/UPS address fees."

[2:05 - 2:40] Scenario 3: SLA Gatekeeper (Unmonitored Deadlines)
"In Scenario 3, our SLA Gatekeeper watches time-critical milestones. 
Candidate Priya Patel is starting in 5 days (T-5), but her IT hardware form is missing and her 
background check is pending. 

The Gatekeeper catches both breaches and generates structured Slack alerts with clear auto-remediation actions."

[2:40 - 3:00] Scenarios 4 & 5: Idempotency & Cryptographic Audit Trail
"Finally, in Scenario 4, we demonstrate strict hash-based idempotency. Replaying the exact same event 
key is immediately identified as an 'ALREADY_PROCESSED' safe no-op.

In Scenario 5, every single write and AI decision is committed to an append-only SHA-256 hash chain, 
providing full tamper evidence for SOC 2 and GDPR compliance.

All 9 unit tests are passing. The repo also includes a runnable MCP server and enterprise OAuth security blueprint. 
Thank you, and I look forward to discussing this in our debrief!"
```

---

## 📤 Submission Checklist for Jessica Brewer

* [x] **Repository URL**: `https://github.com/rinkoo-kumar/bettersync`
* [x] **Systems Map**: `SYSTEMS_MAP.md`
* [x] **Build Note**: `BUILD_NOTE.md`
* [x] **Runnable Prototype**: `run_demo.py` & `video_demo.html`
* [x] **Video Link**: Paste your Loom / YouTube / Google Drive link into your submission email.
