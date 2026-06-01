# ARCHITECTURE.md — System Architecture Deep Dive
## Shesheer CMO Agent — Engineering Blueprint

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Telegram Bot │  │  Streamlit   │  │  WhatsApp (v2)   │  │
│  │  (Primary)   │  │  Web UI      │  │  (Phase 9)       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼───────────────────┼────────────┘
          │                 │                   │
          ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  /chat  /ingest  /memory  /health  /cost_tracker       │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
┌──────────────────────┐      ┌─────────────────────────────┐
│   ORCHESTRATOR       │      │    INGESTION PIPELINE       │
│   (Core Agent Loop)  │      │                             │
│                      │      │  ┌─────────────────────┐    │
│  1. Receive query    │      │  │ YouTube Transcriber │    │
│  2. Load context     │      │  │ (yt-dlp + whisper)  │    │
│  3. Decompose query  │      │  └─────────────────────┘    │
│  4. Retrieve chunks  │      │  ┌─────────────────────┐    │
│  5. Build prompt     │      │  │  Web Scraper        │    │
│  6. Call Gemini API  │      │  │  (httpx + BS4)      │    │
│  7. Format output    │      │  └─────────────────────┘    │
│  8. Update memory    │      │  ┌─────────────────────┐    │
│  9. Return response  │      │  │  PDF Processor      │    │
└──────────┬───────────┘      │  │  (pypdf + pdfplumb) │    │
           │                  │  └─────────────────────┘    │
           │                  │  ┌─────────────────────┐    │
           │                  │  │  Manual Annotator   │    │
           │                  │  │  (CLI tool)         │    │
           │                  │  └─────────────────────┘    │
           │                  └──────────────┬──────────────┘
           │                                 │
           │                  ┌──────────────▼──────────────┐
           │                  │   EMBEDDING PIPELINE        │
           │                  │                             │
           │                  │  sentence-transformers      │
           │                  │  (all-MiniLM + multilingual)│
           │                  │  → 384/768 dim vectors      │
           │                  └──────────────┬──────────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   KNOWLEDGE LAYER                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  ChromaDB                           │   │
│  │                                                     │   │
│  │  col: founders_mindsets     col: campaign_studies   │   │
│  │  col: cmo_profiles          col: market_data        │   │
│  │  col: consumer_psychology   col: books_annotations  │   │
│  │  col: social_intelligence   col: startup_context    │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   RETRIEVAL ENGINE                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Agentic RAG Pipeline                      │   │
│  │                                                     │   │
│  │  Query → Decompose into 3-5 sub-questions           │   │
│  │        → Retrieve top-5 per sub-question            │   │
│  │        → Deduplicate across collections             │   │
│  │        → Rank by relevance + recency                │   │
│  │        → Build structured context package           │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   REASONING ENGINE                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Gemini API                             │   │
│  │                                                     │   │
│  │  System Prompt:  Indian CMO Persona                 │   │
│  │  Context:        Retrieved knowledge chunks         │   │
│  │  Startup State:  Your current metrics/situation     │   │
│  │  History:        Last N conversations (compressed)  │   │
│  │                                                     │   │
│  │  Output Format:  Strategic Memo                     │   │
│  │  ├── SITUATION ANALYSIS                             │   │
│  │  ├── INDIAN MARKET PRECEDENT                        │   │
│  │  ├── THE MOVE                                       │   │
│  │  ├── THE TRAP TO AVOID                              │   │
│  │  └── THE QUESTION YOU HAVEN'T ASKED                 │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   MEMORY LAYER (SQLite)                     │
│                                                             │
│  startup_context    → Live startup state                   │
│  conversations      → Full history (compressed after 30d)  │
│  decisions_log      → Every consulted decision             │
│  pivots_log         → Suggested + taken pivots             │
│  cost_tracker       → Gemini API cost per call             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow — Single Conversation

```
YOU: "Should I use freemium or paid trial for my EdTech platform?"

STEP 1 — CONTEXT LOAD
┌─────────────────────────────────────────┐
│ Memory Layer pulls:                     │
│ - Your startup: AI EdTech, 0 users,    │
│   targeting Class 9-12, Tier 2 cities  │
│ - Last conversation: discussed pricing  │
│ - Your last decision: postponed pricing │
└─────────────────────────────────────────┘

STEP 2 — QUERY DECOMPOSITION
┌─────────────────────────────────────────┐
│ Orchestrator breaks into sub-questions: │
│ Q1: What did PW do on pricing and why? │
│ Q2: What did Byju's do wrong?          │
│ Q3: How does Indian student/parent     │
│     psychology react to free vs paid?  │
│ Q4: What does Kunal Shah's Delta 4     │
│     say about behavior change?         │
│ Q5: What works in Tier 2 specifically? │
└─────────────────────────────────────────┘

STEP 3 — RETRIEVAL
┌─────────────────────────────────────────┐
│ ChromaDB returns for each sub-question: │
│ - PW pricing case study annotation     │
│ - Byju's toxic sales culture chunk     │
│ - Rama Bijapurkar HPI framework        │
│ - Delta 4 framework (Kunal Shah)       │
│ - Kuku FM Bharat payment proof         │
└─────────────────────────────────────────┘

STEP 4 — PROMPT BUILD
┌─────────────────────────────────────────┐
│ System Prompt: Indian CMO Persona       │
│ + Retrieved knowledge (5 chunks)        │
│ + Your startup context                  │
│ + Last 5 conversations summary          │
│ + Your specific question                │
└─────────────────────────────────────────┘

STEP 5 — CLAUDE REASONING
┌─────────────────────────────────────────┐
│ Gemini 2.5 Flash 4.6 processes everything  │
│ Reasons through Indian market lens      │
│ Applies CMO persona thinking            │
│ Generates Strategic Memo                │
└─────────────────────────────────────────┘

STEP 6 — OUTPUT
┌─────────────────────────────────────────┐
│ SITUATION ANALYSIS                      │
│ You're at zero users. Every pricing     │
│ decision you make now will be hard to   │
│ reverse. Here is what is actually       │
│ happening vs what you think...          │
│                                         │
│ INDIAN MARKET PRECEDENT                 │
│ PW kept it ₹999/year. Not because       │
│ they couldn't charge more. Because      │
│ Alakh understood that in Tier 2 India,  │
│ price is a trust signal...              │
│                                         │
│ THE MOVE                                │
│ Do not do freemium. Do radical          │
│ affordability with full access...       │
│                                         │
│ THE TRAP TO AVOID                       │
│ Freemium in India creates a usage       │
│ class that never converts...            │
│                                         │
│ THE QUESTION YOU HAVEN'T ASKED          │
│ Who is actually making the payment      │
│ decision — the student or the parent?   │
└─────────────────────────────────────────┘

STEP 7 — MEMORY UPDATE
┌─────────────────────────────────────────┐
│ Conversation logged to SQLite           │
│ Decision logged: pricing question       │
│ Cost tracked: 847 tokens, ₹12.40        │
└─────────────────────────────────────────┘
```

---

## Knowledge Schema — Annotation Format

Every piece of content ingested follows this exact schema:

```json
{
  "source_id": "pw_pricing_001",
  "source_type": "case_study",
  "person": "Alakh Pandey",
  "company": "Physics Wallah",
  "topic": "Pricing strategy for Indian EdTech",
  "market_phase": "0_to_1",
  "insight_type": "pricing_psychology",
  "applicable_segment": "Tier2_Tier3_students",
  "indian_market_applicable": true,
  "western_framework_override": "Freemium works",
  "override_reason": "Freemium creates non-converting free class in price-sensitive Tier 2",
  "key_belief": "In Tier 2 India, radical affordability IS the trust signal",
  "outcome": "₹0 to ₹10,000 Cr valuation on community trust before monetization",
  "contradicts": "Western SaaS freemium-to-paid conversion playbook",
  "year": "2016-2022",
  "verified": true,
  "content": "Full annotated text of the case study...",
  "tags": ["pricing", "trust", "tier2", "edtech", "community_first"]
}
```

---

## Agentic RAG — Query Decomposition Logic

```python
# Conceptual flow (actual code built in Phase 3)

def decompose_query(user_query: str, startup_context: dict) -> list[str]:
    """
    Takes a founder's question and breaks it into
    specific sub-questions that can be answered
    by the knowledge base independently.

    Example:
    Input:  "Should I run offline events?"
    Output: [
        "What Indian EdTech companies used offline
         events and what happened?",
        "How do Tier 2 parents make trust decisions
         about education products?",
        "What is the unit economics of offline
         acquisition vs digital in India?",
        "What did Byju's learn from offline BDAs?",
        "What does PW's zero-offline model prove?"
    ]
    """
```

---

## The Persona Engine — System Prompt Architecture

The system prompt has 6 layers:

```
LAYER 1: IDENTITY
Who this agent is — the composite Indian CMO persona

LAYER 2: KNOWLEDGE ANCHORS
The specific people and frameworks it reasons through
(Kunal Shah's Delta 4, Alakh Pandey's trust-first,
Nithin Kamath's product-led, Rama Bijapurkar's HPI)

LAYER 3: REASONING RULES
How it thinks — not what it knows
(Indian market first, Bharat lens default,
Western framework override protocol,
conviction over balance)

LAYER 4: OUTPUT FORMAT
Strategic Memo structure — always, no exceptions

LAYER 5: CHALLENGER MODE
Mandatory assumption interrogation before strategy

LAYER 6: STARTUP CONTEXT INJECTION
Dynamic — your live startup state injected per call
```

---

## Challenger Mode — Logic Flow

```
Founder asks: "I want to run Instagram ads"

CHALLENGER MODE FIRES:

Before giving strategy, agent must ask:
├── "What is your current CAC from organic?"
├── "Have you validated demand with zero paid spend?"
├── "Is your target segment on Instagram or on YouTube?"
├── "What did PW do with zero ad spend for 3 years?"
└── "Are you solving a distribution problem or a
     demand problem? These need different tools."

THEN gives the strategy.

This is Challenger Mode.
It asks you the question you weren't asking yourself.
```

---

## Memory Compression Strategy

Conversations older than 30 days get compressed:

```
Full conversation (Day 1-30):    Stored verbatim
Compressed summary (Day 31+):   "In October, you consulted
                                  on pricing strategy. Decision
                                  made: radical affordability
                                  ₹499/year. Outcome: TBD."

This prevents context window explosion while
preserving institutional memory of your startup journey.
```

---

## Security Architecture

```
Single-user system:
├── Telegram user ID whitelist (only you can chat)
├── .env never committed to git
├── .gitignore covers all sensitive files
├── No external API keys stored in code
└── SQLite database not exposed externally

Gemini API key rotation:
└── Monthly rotation recommended
```

---

*This architecture is designed to be built by one person
using Antigravity 2.0 as the primary agent-first IDE,
in 9 structured phases, with zero compromise on quality.*