# Quranic Vocab — Master Quranic Arabic

A comprehensive Quranic Arabic vocabulary memorization tool with 5,155 words, spaced repetition, transliterations, verse context, and audio pronunciation.

## ✨ Features

- 📖 **5,155 Quranic words** — Every unique word in the Quran with frequency data
- 🔤 **Full transliterations** — Roman script pronunciation for every word
- 🎯 **Stage-based learning** — 52 progressive difficulty stages
- 🔊 **Audio pronunciation** — Web Speech API for Arabic TTS
- 📚 **Verse context** — See which verses each word appears in (up to 2023 verses for common words)
- 💡 **Cumulative meanings** — Track multiple meanings per word
- 📊 **Progress rings** — Visual overall and stage-specific progress
- ⌨️ **Keyboard shortcuts** — Space (know), Arrow keys (navigate), A (audio)
- 💾 **Persistent progress** — Saved to localStorage (survives refresh)
- 🎲 **3 study modes** — Random, Weakest First, Sequential
- 📈 **Learning stats** — Difficult words tracker, recently learned list

## Quick Start

```bash
cd Quranic-word-memorizer
python3 -m http.server 8080
# Open http://localhost:8080
```

No build step required. Pure HTML/CSS/JS.

## Data Structure

Each word in `words.js` contains:
```javascript
{
  word: "مِن",                    // Arabic text
  transliteration: "min",         // Roman pronunciation
  translation: "from",            // English meaning
  MeaningsSoFar: "in, from",      // Cumulative meanings
  partOfSpeech: "Preposition",    // Grammar category
  frequency: 3226,                // Occurrences in Quran
  PercentageSoFar: 4.35,          // Cumulative coverage %
  stage: 1,                       // Difficulty stage (1-52)
  verseCount: 2023,               // Number of verses containing this word
  versesFound: "2:4, 2:5, ..."    // Specific verse references
}
```

## Audio Generation (Optional)

For pre-generated audio files instead of Web Speech API:

```bash
# Install dependencies
pip install edge-tts

# Generate audio for all words
python3 pregenerate_audio.py

# Generate transliterations (if needed)
python3 generate_transliterations.py

# Cross-reference words with Quran text
python3 crossref_words.py
```

## Study Modes

| Mode | Description |
|------|-------------|
| **Random** | Random words from the filtered set |
| **Weakest First** | Prioritizes words you haven't mastered yet |
| **Sequential** | Goes through words in frequency order |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` / `→` | Mark as "I Know This" |
| `↓` | Mark as "Don't Know" |
| `←` | Undo last action |
| `A` | Listen to pronunciation |

## File Structure

```
Quranic-word-memorizer/
├── index.html              # Main application (consolidated)
├── words.js                # 5,155 Quranic words with transliterations
├── quran-data.js           # Complete Quran text data
├── pregenerate_audio.py    # Audio generation script
├── voicegen.py             # TTS voice generation
├── generate_transliterations.py  # Transliteration generation
├── crossref_words.py       # Word-verse cross-referencing
├── server.py               # Local development server
├── manifest.json           # PWA manifest
├── LICENSE
└── README.md
```

## Origin

This project consolidates two previous projects:
- **Quranic-word-memorizer** — Polished UI with flashcards, progress rings, and SRS
- **quranic words** — Audio generation pipeline and complete transliteration data

The consolidated version combines the best of both: the beautiful UI and the complete data.

## License

See LICENSE file.
