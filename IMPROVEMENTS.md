# Quranic-word-memorizer — Improvement Report

**Date:** August 27, 2026  
**Analysis Type:** Errors, Inconsistencies, Incompleteness, Missed Sections

---

## 🔴 Errors Found

### 1. Progress Not Persisted
- The `App` class creates `this.memorized = new Map()` and `this.difficult = new Map()` but **never saves to localStorage**. All progress is lost on page refresh. This is the most critical bug — the entire memorization tracking is ephemeral.

### 2. No Data Persistence of Any Kind
- No `localStorage` calls in the entire codebase. The app is completely stateless — every page load starts fresh. This defeats the purpose of a memorization tool.

### 3. Transliterations All Empty
- Every single word in `words.js` has `transliteration: ""`. The README explicitly notes this as a known issue: "fill in the transliteration section in word.js". Without transliterations, non-Arabic speakers cannot use this tool effectively.

### 4. No Back/Previous Button
- The UI only has "I Know This" and "Don't Know" buttons. There's no way to go back to a previously seen word if you tapped by mistake.

---

## 🟡 Inconsistencies

### 1. Translation Inconsistencies in words.js
Several words have inconsistent or confusing translations:
- `عَلِمَ` = "science" (should be "to know" or "knowledge")
- `عَلِم` (at frequency 105) = "science" (should be "knowledge" / "ilm")
- `أَمَرَ` = "commander" (should be "commanded" — it's a verb)
- `نَفْس` = "same" (should be "soul/self")
- `شَىْء` = "something" (should be "thing")
- `فَعَلَ` = "an act" (should be "he did" — it's a verb)
- `هُدًى` = "Hoda" (should be "guidance")
- `بُنَىّ` = "brown" (should be "built/sons")
- `وَلِىّ` = "He is gone" (should be "guardian/ally")
- `ذِكْر` = "male" (should be "remembrance")
- `دَخَلَ` = "income" (should is "he entered")
- `مَع` = translation is empty but should be "with"
- `كَذَّبَ` = "to lie" (should be "to deny/reject")
- `رَءَا` = "saw" (correct past tense, but should be "to see" for consistency)

### 2. MeaningsSoFar Field Inconsistency
- Many entries have empty `MeaningsSoFar` fields (especially in stage 2), while the README notes: "Activate word.js features like PercentageSoFar & MeaningsSoFar." This field is unused in the UI.

### 3. UI Doesn't Use PercentageSoFar
- The `PercentageSoFar` field in each word is never displayed in the UI. It was presumably meant to show cumulative coverage progress.

### 4. Ring Labels Swapped
- The "Overall" and "Current Stage" labels on the progress rings appear to be swapped — `ringOverall` shows stage-specific percentage while `ringStage` shows overall percentage. The variable names and the rendering logic (`this.drawRing('ringOverall', pct, ...)` where `pct` is stage-specific) confirm this is backwards.

---

## 🟠 Incompleteness

### 1. No Word Categories
- Words are organized by frequency and stage but there's no way to filter by:
  - Part of speech (nouns, verbs, particles)
  - Thematic category (worship, nature, judgment, etc.)
  - Root letters

### 2. No Audio
- No audio pronunciation for any word. This is a major gap for a language learning tool.

### 3. No Example Sentences
- Words are shown in isolation. Adding Quranic verse examples where each word appears would dramatically improve learning.

### 4. No Review Scheduling
- Simple SRS (spaced repetition) is not implemented. The "weakest first" mode is the closest, but it doesn't use time-based intervals.

### 5. No Word Details Panel
- When a word is shown, only the basic info is displayed. Missing:
  - Root letters breakdown
  - Word family (related words from same root)
  - Grammatical analysis
  - Multiple meanings in context

---

## 🔵 Missed Sections & Improvements

### 1. Missing Features
- **Import/Export progress** — save to file, load from file
- **Audio pronunciation** — essential for language learning
- **Verse context** — show which verses each word appears in
- **Root family view** — group words by Arabic root
- **Daily goal** — set a target number of words to review
- **Statistics dashboard** — words per day, accuracy rate, streak

### 2. Missing Content
- Only ~100 words are in the current `words.js`. The Quran contains thousands of unique words. Should expand to at least 500-1000 words.
- All transliterations need to be filled in.
- All `MeaningsSoFar` fields need to be populated.

### 3. Technical Improvements
- Switch from ES modules (`import { arabicWords } from './words.js'`) to regular script includes for broader browser compatibility.
- Add `manifest.json` for PWA.
- Add keyboard shortcuts (Enter = know, Escape = don't know).

---

## 📋 Priority Recommendations

| Priority | Issue | Impact |
|----------|-------|--------|
| 🔴 P0 | Add localStorage persistence for progress | Core feature broken |
| 🔴 P0 | Fix translation errors in words.js | Incorrect learning |
| 🔴 P0 | Fill in all transliterations | Usability for non-Arabic speakers |
| 🟡 P1 | Add audio pronunciation | Essential for language learning |
| 🟡 P1 | Expand word list to 500+ words | Content depth |
| 🟡 P1 | Fix swapped ring labels | Misleading progress |
| 🟠 P2 | Add example sentences from Quran | Contextual learning |
| 🟠 P2 | Add root family grouping | Advanced learning |
| 🔵 P3 | Add SRS scheduling (SM-2 algorithm) | Better memorization |
| 🔵 P3 | Add daily goals and streak | Gamification |
