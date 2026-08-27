#!/usr/bin/env python3
"""
Cross-reference words.js with Quran_DB.csv to find which verse(s) each word appears in.
Adds verseCount and versesFound fields to each word entry.
"""

import csv
import re
import os
import sys

CWD = os.path.dirname(os.path.abspath(__file__))

# Arabic diacritics to strip (tashkeel)
ARABIC_DIACRITICS = re.compile(r'[\u064B-\u065F\u0610-\u061A\u06D6-\u06ED]')
# Tatweel (kashida)
TATWEEL = re.compile(r'\u0640')

# Normalization table for Arabic character variants
# Alif variants -> plain alif (U+0627)
ALIF_MAP = str.maketrans({
    '\u0622': '\u0627',  # آ alif with maddah -> plain alif
    '\u0623': '\u0627',  # أ alif with hamza above -> plain alif
    '\u0625': '\u0627',  # إ alif with hamza below -> plain alif
})

# Alif maddah combining form: alif (U+0627) + maddah above (U+0653) -> plain alif
ALIF_MADDAH_COMBINING = re.compile('\u0627\u0653')

# Hamza on seat -> base letter
HAMZA_MAP = str.maketrans({
    '\u0624': '\u0648',  # ؤ waw with hamza -> waw
    '\u0626': '\u064A',  # ئ ya with hamza -> yaa
})

# Ta marbuta -> ha
TA_MARBUTA = str.maketrans({
    '\u0629': '\u0647',  # ة ta marbuta -> ha
})

# Alef maksura -> yaa
ALEF_MAKSURA = str.maketrans({
    '\u0649': '\u064A',  # ى alif maksura -> yaa
})

def normalize_arabic(text):
    """Comprehensively normalize Arabic text for matching.
    
    Steps:
    1. Remove tatweel (kashida)
    2. Remove all diacritics (tashkeel)
    3. Normalize alif variants to plain alif
    4. Normalize hamza-on-seat to base letter
    5. Normalize ta marbuta to ha
    6. Normalize alef maksura to yaa
    """
    text = TATWEEL.sub('', text)
    text = ARABIC_DIACRITICS.sub('', text)
    text = ALIF_MADDAH_COMBINING.sub('\u0627', text)  # آ -> ا
    text = text.translate(ALIF_MAP)
    text = text.translate(HAMZA_MAP)
    text = text.translate(TA_MARBUTA)
    text = text.translate(ALEF_MAKSURA)
    return text

def build_verse_index(csv_path):
    """
    Build a dict: normalized_word -> list of "surah:ayah" strings.
    Each word form is recorded once per verse (set dedup within verse).
    """
    word_to_verses = {}
    total_verses = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_verses += 1
            surah = int(row['surah_no'])
            ayah = int(row['ayah_no_surah'])
            text = row['text_ar']

            # Split verse into individual words
            words_in_verse = text.split()
            seen_in_verse = set()
            for w in words_in_verse:
                norm = normalize_arabic(w)
                if norm and norm not in seen_in_verse:
                    seen_in_verse.add(norm)
                    ref = f"{surah}:{ayah}"
                    if norm not in word_to_verses:
                        word_to_verses[norm] = []
                    word_to_verses[norm].append(ref)

    print(f"  Parsed {total_verses} verses, {len(word_to_verses)} unique word forms in Quran")
    return word_to_verses

def process_words_js(words_js_path, word_to_verses, output_path):
    """Read words.js, add verse references, write output."""
    with open(words_js_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    output_lines = []
    i = 0
    word_count = 0
    match_count = 0
    zero_count = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect start of a word object: "  {" at start of line (indented)
        if stripped == '{' and not line.startswith('{') and i > 0:
            # Accumulate lines until the object closes
            obj_lines = [line]
            i += 1
            brace_count = 1
            while i < len(lines) and brace_count > 0:
                current = lines[i]
                obj_lines.append(current)
                brace_count += current.count('{') - current.count('}')
                i += 1

            # Parse the accumulated object text
            obj_text = ''.join(obj_lines)
            word_match = re.search(r'word:\s*"([^"]*)"', obj_text)

            if word_match:
                arabic_word = word_match.group(1)
                normalized = normalize_arabic(arabic_word)
                word_count += 1

                verses = word_to_verses.get(normalized, [])
                if verses:
                    match_count += 1
                else:
                    zero_count += 1

                # Only add fields if not already present
                if 'verseCount' not in obj_text and 'versesFound' not in obj_text:
                    indent = '    '  # 4 spaces

                    # Find the closing brace line and pop it off
                    # The last line of obj_lines should be close to "  },\n" or "  }\n"
                    closing_line = obj_lines.pop() if obj_lines else ''
                    # Clean up trailing whitespace but keep newline
                    closing_line = closing_line.rstrip('\n\r')

                    # Ensure the last field line has a trailing comma (JS requires commas between properties)
                    if obj_lines:
                        last_field = obj_lines[-1]
                        last_stripped = last_field.rstrip('\n\r').rstrip()
                        if last_stripped and not last_stripped.endswith(','):
                            obj_lines[-1] = last_field.rstrip('\n\r') + ',\n'

                    if verses:
                        MAX_VERSES = 30
                        if len(verses) <= MAX_VERSES:
                            verses_str = ', '.join(verses)
                        else:
                            verses_str = ', '.join(verses[:MAX_VERSES]) + ', ...'

                        obj_lines.append(f'{indent}verseCount: {len(verses)},\n')
                        obj_lines.append(f'{indent}versesFound: "{verses_str}"\n')
                    else:
                        obj_lines.append(f'{indent}verseCount: 0,\n')
                        obj_lines.append(f'{indent}versesFound: ""\n')

                    # Put the closing line back (preserve comma or no-comma)
                    obj_lines.append(f'{closing_line}\n')

                output_lines.extend(obj_lines)
            else:
                output_lines.extend(obj_lines)
        else:
            output_lines.append(line)
            i += 1

    print(f"  Processed {word_count} words: {match_count} with verse matches, {zero_count} without")

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    print(f"  Written to {output_path}")

def main():
    csv_path = os.path.join(CWD, 'Quran_DB.csv')
    words_js_path = os.path.join(CWD, 'words.js')
    output_path = os.path.join(CWD, 'words.js')  # overwrite

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(words_js_path):
        print(f"Error: {words_js_path} not found", file=sys.stderr)
        sys.exit(1)

    print("Step 1: Building verse index from Quran_DB.csv...")
    word_to_verses = build_verse_index(csv_path)

    print("Step 2: Processing words.js...")
    process_words_js(words_js_path, word_to_verses, output_path)

    print("Done!")

if __name__ == '__main__':
    main()
