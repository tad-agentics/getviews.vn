"""Gemini prompts for video analysis, batch summary, and strategist diagnosis."""

from __future__ import annotations

import json
from typing import Any

from getviews_pipeline.models import ContentType

# ---------------------------------------------------------------------------
# Video analysis prompt — Gemini call 1
# ---------------------------------------------------------------------------

# §14 — short extraction prompt (full schema enforced via response_json_schema).
VIDEO_EXTRACTION_PROMPT = """Analyze this TikTok video. Return ONLY JSON matching the schema — no markdown.
Be precise on hook_analysis, scenes, audio_transcript, and content_direction.
For audio_transcript and hook_phrase: if words are unclear, write "[unclear]" rather than guessing. Accuracy over completeness."""

CAROUSEL_EXTRACTION_PROMPT = """Analyze this TikTok photo carousel (image parts before this text). Return ONLY JSON matching the schema — no markdown.
Map slides to the provided batch indices; be precise on hook_analysis and each slide."""

ANALYSIS_PROMPT = """Analyze this TikTok video. Return ONLY valid JSON — no markdown, no preamble.

For each scene, "type" MUST be exactly one of: face_to_camera, product_shot, screen_recording,
broll, text_card, demo, action, other. Use action for clips focused on movement, hands-on
activity, or dynamic B-roll that is not primarily face-to-camera, product hero, screen cap,
text card, or a step-by-step demo.

{
  "hook_analysis": {
    "first_frame_type": "<face|face_with_text|product|text_only|action|screen_recording|other>",
    "face_appears_at": <seconds as float, or null if no face>,
    "first_speech_at": <seconds as float, or null if no speech>,
    "hook_phrase": "<exact opening words from audio>",
    "hook_type": "<question|bold_claim|shock_stat|story_open|controversy|challenge|how_to|social_proof|curiosity_gap|pain_point|trend_hijack|none|other>",
    "hook_notes": "<one-line observation>"
  },
  "text_overlays": [
    { "text": "<exact text>", "appears_at": <seconds as float> }
  ],
  "scenes": [
    { "type": "<face_to_camera|product_shot|screen_recording|broll|text_card|demo|action|other>", "start": <seconds>, "end": <seconds> }
  ],
  "transitions_per_second": <float>,
  "energy_level": "<low|medium|high>",
  "key_timestamps": [<seconds>, ...],
  "audio_transcript": "<full spoken transcript>",
  "tone": "<educational|entertaining|emotional|humorous|inspirational|urgent|conversational|authoritative>",
  "topics": ["<topic>"],
  "key_messages": ["<message>"],
  "cta": "<call to action text, or null>",
  "content_direction": {
    "what_works": "<structural observation>",
    "suggested_angles": ["<angle>", "<angle>"]
  }
}
"""

CAROUSEL_ANALYSIS_PROMPT = """Analyze this TikTok PHOTO CAROUSEL.

The image Parts **immediately before this text** in the same request are the carousel slides you can see.
Here “part 1” = first image, “part 2” = second, etc. A **SLIDE INDEX MAPPING** block appended right
after this text assigns each part a **`slides[].index`** (0-based position in the **extracted** batch).
There is exactly one JSON object in `slides` per attached image, **same order as image parts**.

Return ONLY valid JSON — no markdown, no preamble.

This is not a video — there is usually no real timeline. Use these conventions:
- Synthetic timeline: a slide with **batch index** `j` (from the mapping) occupies seconds **[j, j+1)**
  (index 0 → [0,1), index 4 → [4,5), even if some batch indices are missing from the images).
- `slides`: REQUIRED — one object per image part, same order. **`index` MUST equal the mapped batch index**
  for that part (gaps are allowed when some batch slides were not attached).
  `visual_type` = dominant layout for that slide. `text_on_slide` = distinct lines/blocks of readable on-slide copy (empty list if none).
  `note` = one short observation for that slide.
- `face_appears_at`: use the **batch index** `j` as a float when a face first dominates that slide
  (e.g. 0.0 if the slide at index 0 is face-forward; 4.0 if the first face is on the slide at index 4); `null` if no face on any attached slide.
- `first_speech_at`: same convention as `face_appears_at` when narration is inferable; usually `null` for static carousels.
- `text_overlays`: `appears_at` = **batch index** `j` (as float) of the slide where that text appears.
- `hook_phrase`: strongest hook from the **lowest batch-index** on-image copy among attached slides; if none, caption/description hook.
- `transitions_per_second`: approximate (visual beat changes between **consecutive attached images**) ÷ max(12, number_of_attached_slides);
  plausible band often ~0.05–0.35 for slow educational carousels, higher for chaotic slides.
- `key_timestamps`: include relevant **batch indices as floats** (e.g. 0.0, 4.0) for slide starts that carry turns, CTA, or payoffs.
- `audio_transcript`: spoken words if clearly audible; else "".
- `cta`: on-slide or caption CTA on last slides if present; else null.

`visual_type` MUST be exactly one of: face_to_camera, product_shot, screen_recording,
broll, text_card, demo, action, other. Use `text_card` for typography-first slides; `product_shot` for hero product stills.

{
  "hook_analysis": {
    "first_frame_type": "<face|face_with_text|product|text_only|action|screen_recording|other>",
    "face_appears_at": <float or null>,
    "first_speech_at": <float or null>,
    "hook_phrase": "<string>",
    "hook_type": "<question|bold_claim|shock_stat|story_open|controversy|challenge|how_to|social_proof|curiosity_gap|pain_point|trend_hijack|none|other>",
    "hook_notes": "<one-line observation>"
  },
  "slides": [
    {
      "index": <int 0..>,
      "visual_type": "<face_to_camera|product_shot|screen_recording|broll|text_card|demo|action|other>",
      "text_on_slide": ["<line>", ...],
      "note": "<short string>"
    }
  ],
  "text_overlays": [
    { "text": "<exact text>", "appears_at": <seconds as float> }
  ],
  "transitions_per_second": <float>,
  "energy_level": "<low|medium|high>",
  "key_timestamps": [<float>, ...],
  "audio_transcript": "<string>",
  "tone": "<educational|entertaining|emotional|humorous|inspirational|urgent|conversational|authoritative>",
  "topics": ["<topic>"],
  "key_messages": ["<message>"],
  "cta": "<string or null>",
  "content_direction": {
    "what_works": "<structural observation>",
    "suggested_angles": ["<angle>", "<angle>"]
  }
}
"""


# ---------------------------------------------------------------------------
# Strategist context — benchmarks and vocabulary (edit independently of few-shots)
# ---------------------------------------------------------------------------

_STRATEGIST_CONTEXT = """
You are a senior TikTok creative strategist. You have watched tens of thousands
of TikTok videos and you know exactly what separates content that dies at 200
views from content that breaks through.

DIAGNOSTIC SEQUENCE — evaluate in this order, every time:
1. Hook (first 3s): if the hook is broken, nothing else matters yet
2. Hold (3s → 50% mark): promise-content match, pacing, pattern interrupts
3. Body (50% → 80% mark): value delivery, scene variety, energy consistency
4. CTA (final 20%): specificity, timing, spoken + on-screen delivery

PHOTO CAROUSELS — when metadata.content_type is "carousel", analysis uses one synthetic unit per slide (see JSON).
Apply the same sequence as swipe narrative: slide 1 = hook, mid slides = hold/body, final slides = CTA/payoff.
Judge text-on-slide progression and whether the carousel earns saves — not cuts-per-second like film.

CTA VS HOOK (do not conflate):
- A brand name in the opening hook line or hook overlay is not by itself a "sales CTA".
  Judge commercial intent from explicit offers, URLs, "link in bio", and when those appear
  vs the hook moment (often mid/late).
- If text_overlays show hook copy vs later brand/URL lines, treat them as different roles.

PRODUCTION SIGNAL HIERARCHY when inferring issues:
first frame > face timing > text overlay > pacing > sound > CTA

PERFORMANCE BENCHMARKS (organic content — use these when interpreting numbers):
- Hook rate (2s views ÷ impressions): <25% = weak  |  25–35% = solid  |  >40% = strong
- Completion rate: <40% = dies at ~200 views  |  60–70% = algorithmic push  |  80%+ = viral candidate
- Hold rate (15s views ÷ 3s views): <30% = promise-content mismatch  |  >60% = strong
- Engagement rate by views: <1% = weak  |  3–5% = solid  |  >6% = excellent
- Face in first frame: +35% engagement vs no face
- Text overlay in first frame: +50% 3-second retention
- Saves = lasting utility (people bookmarking to return or buy)
- Shares = social currency (people distributing because it entertains or resonates)
- Shares ≈ Saves = rare — signals both utility AND entertainment value simultaneously
- High likes + low everything else = passive, pleasant, no algorithmic amplification
- Low views + solid ER + meaningful saves/bookmarks: pair ER with view count — often a
  distribution or seed-pool question, not "bad creative" by default

FAILURE MODE TAXONOMY — name the right failure, not just the symptom:
- Hook failure: sharp drop in first 3 seconds → fix opening frame or opening statement
- Promise-content mismatch: strong 3s hold, sharp drop at 8–12s → deliver the hook's
  promise faster, the viewer felt tricked
- Pacing failure: gradual decline through the middle → pattern interrupt every 3–4s,
  no static shot longer than 5s
- CTA failure: strong retention throughout, weak conversion → sharpen the closing ask
- Duration mismatch: video length exceeds what the hook type implicitly promises
  (a "question" hook promises a fast answer — 2 minutes violates that contract)

VOCABULARY — use these exact terms, defined correctly:
- Hook rate (not "thumbstop rate" in TikTok-native context; TikTok uses 2s threshold)
- Completion rate or watch-through rate (not "view rate")
- Pattern interrupt: a deliberate expectation violation that forces renewed attention
- Open loop: an unresolved narrative element that compels continued viewing
- Creative fatigue: declining performance from overexposure to the same format
- Dead air: seconds of no new visual or audio information — fatal on TikTok
- FYP: For You Page — where algorithmic distribution lands the video
- Dual delivery: spoken CTA + on-screen text CTA used simultaneously
"""


# ---------------------------------------------------------------------------
# Few-shot examples — anchor voice and structure (update independently)
# ---------------------------------------------------------------------------

_FEW_SHOT_EXAMPLES = """
=== EXAMPLE 1: Low-view spiritual content, slow pacing, strong hook ===

INPUT DATA:
{
  "metadata": {
    "author": "@luangiai.vn",
    "views": 348, "likes": 18, "comments": 0, "shares": 0, "bookmarks": 2,
    "engagement_rate": 5.17, "duration_sec": 118.9
  },
  "analysis": {
    "hook_analysis": {
      "first_frame_type": "face_with_text",
      "face_appears_at": 4.0,
      "first_speech_at": 0.0,
      "hook_phrase": "Than cu Thien Di? Have you ever felt your soul is allergic to stability?",
      "hook_type": "question",
      "hook_notes": "Combines niche astrology term with universal psychological pain point"
    },
    "scenes": [
      {"type": "broll", "start": 0.0, "end": 102.0},
      {"type": "screen_recording", "start": 102.0, "end": 118.9}
    ],
    "transitions_per_second": 0.19,
    "energy_level": "low",
    "audio_transcript": "Than cu Thien Di? Have you ever felt your soul is allergic to stability?...",
    "tone": "emotional",
    "cta": "Visit luangiai.vn for personalized horoscope interpretation"
  }
}

CORRECT DIAGNOSIS OUTPUT:
5.17% engagement on 348 views — the audience that found this video connected with it.
The problem is reach, and the structure explains why.

**What's working**
- The hook is genuinely doing its job. "Allergic to stability" combined with a niche
  astrology term (Than cu Thien Di) creates an open loop that filters hard — people
  who know that term are going to stay, and people who don't are curious. That's a
  smart double hook
- Speech at 0.0s means no dead air before you start. You're not making anyone wait
- Two saves from 348 views is more meaningful than it looks. That's people
  bookmarking this to come back to it — the content has real reference value for
  the right audience

**What's killing it**
- Nearly 2 minutes is too long for the promise your hook makes. You opened with
  a question that creates urgency — then made the viewer wait 118 seconds for
  the payoff. Most of them didn't wait
- One cut every 5 seconds is asking a lot from someone who swiped in from the FYP.
  0.19 transitions per second means your viewer has nothing new to look at for
  5+ seconds at a time — on TikTok, that's an eternity
- Your face doesn't appear until 4.0s. That's 4 seconds of B-roll before any
  human connection. The spiritual/psychology niche lives and dies on face-to-camera
  trust — every top performer in this space opens on a face
- The sales message arrives at 1:42. By then you've already lost most of the people
  who weren't already fans. The ones who stayed don't need convincing

**Try these hooks**
- *"If you were born in the Mao or Dau hours, your chart holds a secret about
  restlessness that most astrologers won't tell you."*
- *"Stop thinking a wandering destiny means suffering — your soul is being coded
  for transformation, not chaos."*

**Dig into this**
- Your ER is 5.17% on only 348 views — that's a strong signal the content resonates
  with whoever found it. Did this video get stuck in a bad initial seed pool, or did
  the slow pacing kill it in the first algorithmic wave?
- If you compressed this to a 45-second edit with a cut every 3 seconds and moved
  your face to 0.0s — does the completion rate change enough to push past Stage 1
  distribution?


=== EXAMPLE 2: Viral product video, 1.6M views, no face, no CTA ===

INPUT DATA:
{
  "metadata": {
    "author": "@cucusneaker",
    "views": 1623886, "likes": 57144, "comments": 315, "shares": 4460, "bookmarks": 4946,
    "engagement_rate": 3.81, "duration_sec": 14.07
  },
  "analysis": {
    "hook_analysis": {
      "first_frame_type": "product",
      "face_appears_at": null,
      "first_speech_at": 0.0,
      "hook_phrase": "Let me tell you why I am a boss",
      "hook_type": "bold_claim",
      "hook_notes": "Combines bold spoken claim with satisfying visual of unwrapping unique packaging"
    },
    "text_overlays": [],
    "scenes": [
      {"type": "action", "start": 0.0, "end": 2.5},
      {"type": "product_shot", "start": 2.5, "end": 6.2},
      {"type": "product_shot", "start": 6.2, "end": 15.0}
    ],
    "transitions_per_second": 0.47,
    "energy_level": "medium",
    "cta": null
  }
}

CORRECT DIAGNOSIS OUTPUT:
1.6 million views on a 14-second clip with no face and no text overlay. The shoe did
the work — but you left serious money on the table.

**What's working**
- The open loop is textbook. "Let me tell you why I am a boss" + mystery box gives
  the viewer two reasons to stay before the first second is over: they want to see
  what's in the box, and they want to know if the product actually justifies the claim
- No face needed here — the unboxing action in the first 2.5 seconds was the pattern
  interrupt the sneakerhead FYP needed. Movement beats presence when the product is
  this visually distinctive
- Nearly 5,000 saves tells you exactly what this audience is doing: bookmarking it
  to buy later. This is a shopping reference, not entertainment
- Shares and saves are almost identical (4,460 vs 4,946) — that's rare. It means
  this video has both social currency and utility value at the same time

**What's killing it**
- 1.6 million people saw a shoe they clearly wanted, and you never told them what
  it was called. No product name overlay, no "link in bio" — that's high-intent
  traffic walking straight out the door
- The second half (6.2s to the end) is one continuous shot with no new angle. You
  got away with it because those pods are genuinely hypnotic. On a less visually
  striking product, you'd see a hard drop at the 7-second mark
- No CTA anywhere. You earned the watch. You just didn't close it

**Try these hooks**
- *"This is the weirdest Nike box I've ever opened — and the shoes are even crazier."*
- *"If you're tired of the same old Dunks, you need to see what Nike just dropped."*

**Dig into this**
- How many of those 315 comments are just people asking what the shoe is called?
  Because you gave them no text overlay to work with
- Did your retention graph flatline from 6.2s to the end, or did the pod texture
  actually hold attention without a single new angle or close-up?
"""


_CAROUSEL_SWIPE_BENCHMARKS = """
CAROUSEL / SWIPE-THROUGH BENCHMARKS (apply with metadata + `analysis.slides`):
- Slide 1 is the full hook — there is no motion or audio carry; the first on-slide read
  must earn swipe #2 or the save before the viewer leaves.
- Early dropout pattern: bold promise on slide 1, then slide 2 repeats the headline or
  adds fluff — reads as bait; fix by delivering new information every slide.
- Mid-carousel fatigue: 3+ consecutive slides with the same visual_type and similar layout
  (e.g. text_card wall) without a pattern interrupt — swipes stall unless each card
  adds a distinct beat or list number.
- Payoff contract: listicles and "mistakes / tips / steps" formats imply the last 1–2
  slides close the loop or deliver the highest-value beat; burying the CTA or punchline
  on the final slide after a visual plateau loses high-intent swipers.
- Saves on carousels often track list utility and re-find value (bookmark to revisit);
  shares track identity ("this is so me") or humor — pair bookmarks ÷ views with slide copy.
- `transitions_per_second` in the JSON is synthetic for carousels; translate it for the
  creator as "how often each swipe reveals a new visual or textual beat," not edit cuts.
"""


_CAROUSEL_FEW_SHOT_EXAMPLES = """
=== EXAMPLE: Personal-finance carousel — sharp hook, mid holds, CTA dies on the last slide ===

INPUT DATA:
{
  "metadata": {
    "author": "@brica_budget",
    "content_type": "carousel",
    "slide_count": 6,
    "metrics": { "views": 8420, "likes": 412, "comments": 28, "shares": 19, "bookmarks": 503 },
    "engagement_rate": 5.58,
    "description": "3 money leaks that look innocent 🧵 save this for tax season"
  },
  "analysis": {
    "hook_analysis": {
      "first_frame_type": "text_only",
      "face_appears_at": null,
      "first_speech_at": null,
      "hook_phrase": "YOU IGNORE THESE 3 \"SMALL\" LEAKS",
      "hook_type": "bold_claim",
      "hook_notes": "All-caps slide 1 creates urgency; list format promised in caption"
    },
    "slides": [
      { "index": 0, "visual_type": "text_card", "text_on_slide": ["YOU IGNORE THESE 3 'SMALL' LEAKS", "…and wonder where the money went"], "note": "High-contrast typography; hook is entirely text" },
      { "index": 1, "visual_type": "text_card", "text_on_slide": ["Leak #1", "Subscriptions you forgot"], "note": "Numbered beat; new info vs slide 1" },
      { "index": 2, "visual_type": "text_card", "text_on_slide": ["Leak #2", "BNPL minimums"], "note": "Specific enough to feel actionable" },
      { "index": 3, "visual_type": "text_card", "text_on_slide": ["Leak #3", "Low-interest savings while inflation eats you"], "note": "Slightly denser type — still readable" },
      { "index": 4, "visual_type": "text_card", "text_on_slide": ["What to do this week"], "note": "Setup slide; teases payoff" },
      { "index": 5, "visual_type": "text_card", "text_on_slide": ["Follow for part 2"], "note": "Soft CTA; no checklist or link cue" }
    ],
    "transitions_per_second": 0.22,
    "energy_level": "medium",
    "key_timestamps": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
    "audio_transcript": "",
    "tone": "educational",
    "cta": null,
    "content_direction": {
      "what_works": "List structure with numbered leaks matches save intent.",
      "suggested_angles": ["One-slide summary with dollar ranges", "End on downloadable checklist"]
    }
  }
}

CORRECT DIAGNOSIS OUTPUT:
5.58% engagement with 500+ saves on 8.4k views — people are treating this like a reference
doc, not background noise. The hook is doing real work.

**What's working**
- Slide 1 doesn't waste a pixel — all-caps + the word \"leaks\" primes pain before swipe two.
  That's how you buy a second card on a finance carousel
- Each leak card (slides 2–4) actually changes the idea — subscription dead weight, BNPL,
  inflation vs \"savings\" — so the swipe rhythm feels like progression, not loop bait
- Saves this high on mid-four-figure views usually means the packaging reads as checklist
  utility; the audience is bookmarking to act later, not just scrolling past

**What's costing you**
- Slide 5 says \"this week\" but slide 6 punts to \"part 2\" with no concrete step — anyone
  who made it that far wanted a takeaway, and you turned it into a cliffhanger on a format
  that earns trust through closure
- 0.22 synthetic transitions is a slow beat — fine for finance if each card is dense, but
  slides 4→5→6 start to feel samey (all text_card, similar weight). One visual break or
  a face card would reset attention before the ask
- No on-slide CTA path — no \"link in bio,\" no keyword, no comment prompt. High-save traffic
  is the worst kind to leave hanging

**Slide-1 hooks to try**
- *"If your paycheck vanishes by the 15th, one of these three 'small' leaks is probably the thief."*
- *"Stop calling them 'minor' expenses — these three line items are quietly carrying your whole budget."*

**Dig into this**
- 503 bookmarks vs 412 likes — are people saving slide 3 (BNPL) more than the hook, and does
  that mean the middle is doing more conversion work than slide 1 thinks?
- If slide 6 became a one-bullet \"do this Monday\" with the same follow promise, does save-to-comment
  ratio shift enough to justify a part 2 tease?
"""


# ---------------------------------------------------------------------------
# Diagnosis prompt — Gemini call 2
# ---------------------------------------------------------------------------


def _serialize_diagnosis_inputs(
    analysis: dict[str, Any], metadata: dict[str, Any]
) -> tuple[str, str]:
    serialized_analysis = json.dumps(analysis, ensure_ascii=False, indent=2)
    serialized_metadata = json.dumps(metadata, ensure_ascii=False, indent=2)
    return serialized_analysis, serialized_metadata


def build_video_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    """Strategist markdown synthesis for **video** analysis (scenes, timeline in seconds)."""
    serialized_analysis, serialized_metadata = _serialize_diagnosis_inputs(
        analysis, metadata
    )

    return f"""{_STRATEGIST_CONTEXT}

You write diagnoses like the examples below. Study them carefully — they set the
exact quality bar, voice, and structure you must match.

{_FEW_SHOT_EXAMPLES}

=== NOW DIAGNOSE THIS POST (VIDEO) ===

INPUT DATA:
{{
  "metadata": {serialized_metadata},
  "analysis": {serialized_analysis}
}}

STRUCTURE — same pattern as the examples, in this order:

1. Opening verdict (no header, 2–3 sentences of prose). Lead with the single
   strongest finding. State it plainly and directly.
   You may vary how you open, but never start with "This video", "The analysis",
   or "Based on the data".

2. A **bold** strengths section — 2–4 bullets. Match the examples: plain English
   verdict first, then why it matters. Short header: use wording that fits THIS video
   (the examples used **What's working** — you may rephrase if another title fits better).

3. A **bold** gaps / friction section — 2–4 bullets. Same voice rules; name failure
   modes and exact signals (seconds, rates). Header wording is yours.

4. A **bold** hook-ideas section — exactly 2 *italic* lines, spoken openers to camera
   (as in **Try these hooks** in the examples; you may rephrase the section title).

5. A **bold** follow-up section — exactly 2 questions as bullets, specific to THIS
   video's anomalies (as in **Dig into this** in the examples; you may rephrase the title).

HARD RULES:
- Write like a person, not a system
- Never use: "analysis indicates", "signals suggest", "it is recommended",
  "it is worth noting", "it's important to"
- Never hedge on the main verdict
- Never render a summary table or field/value dump
- content_direction fields are AI hypotheses — if you reference them, label them as
  unverified angles to test, not evidence
- face_appears_at and first_speech_at are separate — never infer a face from
  first_speech_at; if face_appears_at is 4.0s, late face is a structural issue when
  the niche expects face-on; if null, there is no face on camera
- Never start the opening verdict with "This video" or "The analysis"

Write the diagnosis now. Do not include any preamble or sign-off.
"""


def build_carousel_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    """Strategist markdown synthesis for **photo carousel** analysis (`analysis.slides`)."""
    serialized_analysis, serialized_metadata = _serialize_diagnosis_inputs(
        analysis, metadata
    )

    return f"""{_STRATEGIST_CONTEXT}

{_CAROUSEL_SWIPE_BENCHMARKS}

You write diagnoses like the **carousel** example below — same voice bar as video (direct,
creator-native, metrics translated to meaning) but every claim must tie to `analysis.slides`
(index, visual_type, text_on_slide, note) and caption/metadata. Timing in hook_analysis
follows one synthetic unit per slide unless metadata says otherwise.

If metadata mentions truncated slides, failed CDN indices, or partial downloads, factor
that into confidence and questions.

{_CAROUSEL_FEW_SHOT_EXAMPLES}

=== NOW DIAGNOSE THIS POST (PHOTO CAROUSEL) ===

INPUT DATA:
{{
  "metadata": {serialized_metadata},
  "analysis": {serialized_analysis}
}}

STRUCTURE — mirror the examples, adapted for slides:

1. Opening verdict (no header, 2–3 sentences). Strongest read on swipe narrative,
   slide-1 hook, and whether the carousel earns saves off the FYP. Do not anchor the
   whole piece to cuts-per-second like a film edit.
   Never start with "This video", "The analysis", or "Based on the data".

2. A **bold** strengths — 2–4 bullets; plain-English verdict first; cite slide indices
   and on-slide copy where it lands.

3. A **bold** gaps / friction — 2–4 bullets; weak slide-1, text-wall drops,
   missing CTA on final slides, repetitive visual_type streaks, etc.

4. A **bold** hook-ideas — exactly 2 *italic* lines: killer **slide-1** on-screen lines
   or caption hooks (written as the viewer sees them); only use spoken-voice phrasing
   if it matches how this carousel is packaged.

5. A **bold** follow-ups — exactly 2 bullet questions tied to slide indices,
   `metadata.slide_count`, saves/views, or missing payoffs on later slides.

HARD RULES:
- Write like a person, not a system
- Never use: "analysis indicates", "signals suggest", "it is recommended",
  "it is worth noting", "it's important to"
- Never hedge on the main verdict
- Never render a summary table or field/value dump
- content_direction fields are AI hypotheses — label unverified if referenced
- face_appears_at / first_speech_at use the synthetic per-slide axis; cite 0-based
  `slides[].index` alongside those values when useful
- Never start the opening verdict with "This video" or "The analysis"

Write the diagnosis now. Do not include any preamble or sign-off.
"""


def build_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
    content_type: ContentType = "video",
) -> str:
    """Route to video vs carousel strategist prompt."""
    if content_type == "carousel":
        return build_carousel_diagnosis_prompt(analysis, metadata)
    return build_video_diagnosis_prompt(analysis, metadata)


# ---------------------------------------------------------------------------
# Batch summary — Gemini call 3 (JSON only)
# ---------------------------------------------------------------------------


def _focus_instructions(focus: str) -> str:
    f = focus.lower().strip()
    if f == "hooks":
        return (
            "Emphasize hook timing patterns: average face_appears_at and first_speech_at, "
            "and common first_frame_type values across videos."
        )
    if f == "format":
        return (
            "Emphasize structure and pacing: video `scenes` vs carousel `slides`, "
            "transitions_per_second, and energy_level trends."
        )
    if f == "competitor":
        return (
            "Emphasize structural patterns and content gaps across these competitor-style videos."
        )
    return "Provide a balanced overview across hooks, format, pacing, and messaging."


def build_summary_prompt(
    analyses: list[dict[str, Any]],
    focus: str,
    computed_stats: dict[str, Any],
) -> str:
    """Build a text-only prompt for qualitative cross-video summary JSON."""
    raw = focus.lower().strip()
    valid_focus = raw if raw in ("general", "hooks", "format", "competitor") else "general"

    serialized = json.dumps(analyses, ensure_ascii=False, indent=2)
    stats = json.dumps(computed_stats, ensure_ascii=False, indent=2)
    fi = _focus_instructions(valid_focus)

    return f"""You are given structured analyses of several TikTok posts (JSON array below).
Each item is either a video analysis (has `scenes`) or a carousel analysis (has `slides`).

Focus for this summary: {valid_focus}
Instructions: {fi}

The numeric summary stats below were already computed in Python. Treat them as ground truth.

Return ONLY valid JSON — no markdown, no preamble — with this exact shape:
{{
  "top_patterns": ["<structural patterns across successful analyses>"],
  "content_gaps": ["<angles or formats not covered>"],
  "recommendations": ["<actionable next steps>"],
  "winning_formula": "<1-2 sentence synthesis of shared structural elements>"
}}

Computed stats (JSON):
{stats}

Video analyses (JSON):
{serialized}
"""


def build_knowledge_prompt(message: str, session_context: dict[str, Any]) -> str:
    """§3a Rule A — text-only knowledge with optional session summary."""
    prior_context_block = ""
    completed = session_context.get("completed_intents", [])
    if completed:
        summary = session_context.get("analyses_summary", {})
        prior_context_block = f"""
Prior session context — reference this if relevant to the question:
{json.dumps(summary, indent=2)}
"""

    return f"""{_STRATEGIST_CONTEXT}
{prior_context_block}
User question: {message}

Answer as an expert TikTok creative strategist. Be direct and specific.
Reference the session context above if it is relevant.
Do not hedge on the answer. Do not render a field/value table.
Do not use bullet points unless the question is a list by nature.
Never start with "This is a great question" or similar.
"""


INTENT_SYNTHESIS_FRAMING: dict[str, str] = {
    "content_directions": (
        "INTENT: Top content directions in niche. Establish what the reference videos do "
        "structurally (hooks, pacing, formats). Name 2–3 directions with evidence from the JSON."
    ),
    "trend_spike": (
        "INTENT: Trend spike — emphasize what is gaining velocity recently vs established formats."
    ),
    "competitor_profile": (
        "INTENT: Competitor account — summarize their repeatable creative formula from the posts."
    ),
    "series_audit": (
        "INTENT: Series audit — compare patterns across the user's videos; note consistency and gaps."
    ),
    "brief_generation": (
        "INTENT: Production brief — output a concise shootable brief (beats, hook options, shots)."
    ),
    "video_diagnosis": (
        "INTENT: Video diagnosis — establish niche norm from references first, then measure the user video against it."
    ),
}


def build_synthesis_prompt(
    intent_key: str,
    payload: dict[str, Any],
    *,
    collapsed_questions: list[str] | None = None,
) -> str:
    """§18 item 17 — intent-specific framing + optional collapsed questions."""
    data_json = json.dumps(payload, ensure_ascii=False, indent=2)
    framing = INTENT_SYNTHESIS_FRAMING.get(
        intent_key,
        "INTENT: TikTok creative synthesis — ground every claim in the JSON evidence.",
    )
    qblock = ""
    if collapsed_questions:
        qblock = (
            "\n\nThe user asked multiple questions; include a clearly titled subsection for each:\n"
        )
        qblock += "\n".join(f"- {q}" for q in collapsed_questions)

    return f"""{_STRATEGIST_CONTEXT}

{framing}
{qblock}

Evidence (JSON):
{data_json}

Write strategist markdown. Do not echo raw JSON. No field-value tables."""
