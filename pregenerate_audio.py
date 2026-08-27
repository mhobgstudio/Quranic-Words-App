#!/usr/bin/env python3
"""Pre-generate all Arabic + English audio files for 5155 Quranic words.

Structure:
  audio/ar/00001.wav ... 05155.wav  (Arabic pronunciation)
  audio/en/00001.wav ... 05155.wav  (English transliteration)
  audio/manifest.json                 (index → word mapping)
"""

import asyncio, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).parent
AUDIO_DIR = HERE / "audio"
AR_DIR = AUDIO_DIR / "ar"
EN_DIR = AUDIO_DIR / "en"
MANIFEST = AUDIO_DIR / "manifest.json"
WORDS_JS = HERE / "words.js"

# Voice config
AR_VOICE = "ar-SA-HamedNeural"
EN_VOICE = "en-US-AriaNeural"
DELAY_SEC = 0.3       # respectful delay between calls
BATCH_SIZE = 25        # parallel batch size

import importlib.util
spec = importlib.util.spec_from_file_location("voicegen", str(HERE / "voicegen.py"))
vg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vg)
VoiceGenerator = vg.VoiceGenerator

def parse_words():
    """Parse words.js and return list of {word, transliteration, ...} dicts."""
    import re
    with open(WORDS_JS) as f:
        content = f.read()
    objects = re.findall(r'\{[^}]+\}', content)
    result = []
    for obj_str in objects:
        fields = {}
        for match in re.finditer(r'(\w+):\s*(("[^"]*")|(\d+(?:\.\d+)?)|(\w+))', obj_str):
            key = match.group(1)
            val = match.group(2)
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val in ('true', 'false', 'null'):
                val = None
            else:
                try:
                    val = float(val) if '.' in val else int(val)
                except:
                    pass
            fields[key] = val
        if fields:
            result.append(fields)
    return result


async def synth_one(text: str, voice: str, out_path: str, lang: str) -> bool:
    """Generate TTS audio for one text."""
    try:
        import edge_tts
        if not text or not text.strip():
            return False
        c = edge_tts.Communicate(text.strip(), voice)
        await c.save(out_path)
        p = Path(out_path)
        return p.exists() and p.stat().st_size > 500
    except Exception as e:
        print(f"    ✗ {e}")
        return False


async def main():
    words = parse_words()
    print(f"Loaded {len(words)} words")

    AR_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    # Check resume state
    manifest = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        print(f"Found existing manifest with {len(manifest)} entries")

    # Build task list
    pending = []
    for i, w in enumerate(words):
        idx = i + 1
        ar_path = AR_DIR / f"{idx:05d}.wav"
        en_path = EN_DIR / f"{idx:05d}.wav"
        ar_done = ar_path.exists() and ar_path.stat().st_size > 500
        en_done = en_path.exists() and en_path.stat().st_size > 500
        if not ar_done or not en_done:
            pending.append((idx, w, ar_path, en_path, ar_done, en_done))

    total = len(words)
    done_count = total - len(pending)
    print(f"Already done: {done_count}/{total} pairs")
    print(f"Pending: {len(pending)}")
    print(f"Estimated time: {len(pending) * 2 * DELAY_SEC / 60:.1f} min\n")

    if not pending:
        print("Nothing to generate.")
        return

    # Batch generation
    ar_fails = 0
    en_fails = 0
    for batch_start in range(0, len(pending), BATCH_SIZE):
        batch = pending[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\nBatch {batch_num}/{total_batches} (words {batch[0][0]}–{batch[-1][0]})")

        tasks = []
        for idx, w, ar_path, en_path, ar_done, en_done in batch:
            word_text = w.get("word", "")
            en_text = w.get("transliteration", w.get("translation", ""))

            if not ar_done and word_text:
                tasks.append(synth_one(word_text, AR_VOICE, str(ar_path), "ar-SA"))
            else:
                tasks.append(asyncio.sleep(0))  # no-op placeholder

            if not en_done and en_text:
                tasks.append(synth_one(en_text, EN_VOICE, str(en_path), "en-US"))
            else:
                tasks.append(asyncio.sleep(0))

        results = await asyncio.gather(*tasks)

        # Count failures
        for i, (idx, w, ar_path, en_path, ar_done, en_done) in enumerate(batch):
            ar_result = results[i * 2]
            en_result = results[i * 2 + 1]
            if not ar_result and not ar_done:
                ar_fails += 1
                print(f"  [{idx:05d}] AR FAIL: {w.get('word', '')}")
            if not en_result and not en_done:
                en_fails += 1
                print(f"  [{idx:05d}] EN FAIL: {w.get('transliteration', '')}")

            # Update manifest
            manifest[str(idx)] = {
                "word": w.get("word", ""),
                "transliteration": w.get("transliteration", ""),
                "translation": w.get("translation", ""),
                "stage": w.get("stage", 0),
                "ar": f"ar/{idx:05d}.wav",
                "en": f"en/{idx:05d}.wav",
            }

        # Write manifest after each batch
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

        done_now = done_count + min(batch_start + BATCH_SIZE, len(pending))
        pct = done_now / total * 100
        print(f"  Progress: {done_now}/{total} ({pct:.1f}%) | AR fails: {ar_fails} | EN fails: {en_fails}")

        # Rate limit between batches
        if batch_start + BATCH_SIZE < len(pending):
            await asyncio.sleep(DELAY_SEC)

    print(f"\n{'='*50}")
    print(f"Complete! Generated {total} word pairs")
    print(f"  Arabic failures: {ar_fails}")
    print(f"  English failures: {en_fails}")
    print(f"  Manifest: {MANIFEST}")
    print(f"  Total size: {sum(f.stat().st_size for f in AR_DIR.iterdir()) / 1024 / 1024:.1f} MB (ar) + "
          f"{sum(f.stat().st_size for f in EN_DIR.iterdir()) / 1024 / 1024:.1f} MB (en)")


if __name__ == "__main__":
    asyncio.run(main())
