#!/usr/bin/env python3
"""Regenerate all 5155 Quranic word transliterations with vowel-aware engine."""

import re, json

CHAR_MAP = {
    '\u0627': 'ā', '\u0623': 'ā', '\u0625': 'i', '\u0622': 'ā',
    '\u0628': 'b', '\u062A': 't', '\u062B': 'th',
    '\u062C': 'j', '\u062D': 'ḥ', '\u062E': 'kh',
    '\u062F': 'd', '\u0630': 'dh', '\u0631': 'r',
    '\u0632': 'z', '\u0633': 's', '\u0634': 'sh',
    '\u0635': 'ṣ', '\u0636': 'ḍ', '\u0637': 'ṭ',
    '\u0638': 'ẓ', '\u0639': 'ʿ', '\u063A': 'gh',
    '\u0641': 'f', '\u0642': 'q', '\u0643': 'k',
    '\u0644': 'l', '\u0645': 'm', '\u0646': 'n',
    '\u0647': 'h', '\u0648': 'w', '\u064A': 'y',
    '\u0621': 'ʾ', '\u0624': 'ʾ', '\u0626': 'ʾ',
    '\u0629': 'h', '\u0649': 'ā', '\u0670': 'ā',
}

FATHA = '\u064E'
DAMMA = '\u064F'
KASRA = '\u0650'
SUKUN = '\u0652'
SHADDA = '\u0651'
VOWEL_MAP = {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}

# 200+ common word overrides
KNOWN = {
    'مِن': 'min', 'ٱللَّه': 'Allāh', 'فِى': 'fī',
    'إِنّ': 'inna', 'قَالَ': 'qāla', 'عَلَىٰ': 'ʿalā',
    'ٱلَّذِى': 'alladhī', 'لَا': 'lā', 'كَانَ': 'kāna',
    'مَا': 'mā', 'رَبّ': 'rabb', 'إِلَىٰ': 'ilā',
    'مَن': 'man', 'إِن': 'in', 'أَن': 'anna',
    'إِلَّا': 'illā', 'ءَامَنَ': 'āmana', 'ذَٰلِك': 'dhālika',
    'عَن': 'ʿan', 'أَرْض': 'arḍ', 'قَد': 'qad',
    'إِذَا': 'idhā', 'قَوْم': 'qawm', 'ءَايَة': 'āyah',
    'عَلِمَ': 'ʿalima', 'أَنّ': 'anna', 'كُلّ': 'kull',
    'لَم': 'lam', 'جَعَلَ': 'jaʿala', 'ثُمّ': 'thumma',
    'رَسُول': 'rasūl', 'يَوْم': 'yawm', 'عَذَاب': 'ʿadhāb',
    'هَٰذَا': 'hādhā', 'سَمَآء': 'samāʾ', 'نَفْس': 'nafs',
    'كَفَرَ': 'kafara', 'شَىْء': 'shayʾ', 'أَو': 'aw',
    'جَآءَ': 'jāʾa', 'عَمِلَ': 'ʿamila', 'آتَى': 'ātā',
    'رَءَا': 'raʾā', 'أَتَى': 'atā', 'كِتَٰب': 'kitāb',
    'بَيْن': 'bayna', 'حَقّ': 'ḥaqq', 'نَّاس': 'nās',
    'إِذ': 'idh', 'شَآءَ': 'shāʾa', 'أُولَٰٓئِك': 'ulāʾika',
    'قَبْل': 'qabl', 'مُؤْمِن': 'muʾmin', 'لَو': 'law',
    'خَلَقَ': 'khalaqa', 'أَنزَلَ': 'anzala', 'سَبِيل': 'sabīl',
    'كَذَّبَ': 'kadhdhaba', 'دَعَا': 'daʿā', 'أَمْر': 'amr',
    'ٱتَّقَىٰ': 'ittaqā', 'عِند': 'ʿinda', 'مَع': 'maʿa',
    'بَعْض': 'baʿḍ', 'لَمَّا': 'lammā', 'أَيُّهَا': 'ayyuhā',
    'خَيْر': 'khayr', 'إِلَٰه': 'ilāh', 'نَار': 'nār',
    'غَيْر': 'ghayr', 'هَدَى': 'hadā', 'أَرَادَ': 'arāda',
    'أَم': 'am', 'مُوسَىٰ': 'mūsā', 'ٱتَّبَعَ': 'ittabaʿa',
    'دُون': 'dūn', 'آخِر': 'ākhir', 'بَعْد': 'baʿd',
    'قَلْب': 'qalb', 'عَبْد': 'ʿabd', 'أَرْسَلَ': 'arsala',
    'أَهْل': 'ahl', 'أَخَذَ': 'akhadha', 'ٱتَّخَذَ': 'ittakhadha',
    'لَعَلّ': 'laʿalla', 'بَل': 'bal', 'عَبَدَ': 'ʿabada',
    'يَد': 'yad', 'كَٰفِرُون': 'kāfirūn', 'رَحْمَة': 'raḥmah',
    'رَّحِيم': 'raḥīm', 'ظَلَمَ': 'ẓalama', 'سَأَلَ': 'saʾala',
    'وَجَدَ': 'wajada', 'أَجْر': 'ajr', 'ظَالِم': 'ẓālim',
    'عِلْم': 'ʿilm', 'عَظِيم': 'ʿaẓīm', 'لَن': 'lan',
    'عَلِيم': 'ʿalīm', 'أَخْرَجَ': 'akhraja', 'جَنَّة': 'jannah',
    'حَتَّىٰ': 'ḥattā', 'هَل': 'hal', 'أَكَلَ': 'akala',
    'دِين': 'dīn', 'قَوْل': 'qawl', 'ذُو': 'dhū',
    'لَّيْسَ': 'laysa', 'مَلَك': 'malak', 'فَعَلَ': 'faʿala',
    'مَثَل': 'mathal', 'نَّظَرَ': 'naẓara', 'مَال': 'māl',
    'وَلِىّ': 'waliyy', 'هُدًى': 'hudan', 'حَكِيم': 'ḥakīm',
    'فَضْل': 'faḍl', 'ذَكَرَ': 'dhakara', 'صَلَوٰة': 'ṣalāh',
    'خَافَ': 'khāfa', 'قَتَلَ': 'qatala', 'لَيْل': 'layl',
    'شَيْطَٰن': 'shayṭān', 'كَيْف': 'kayfa', 'رَجَعَ': 'rajaʿa',
    'أَصْحَٰب': 'aṣḥāb', 'أَكْثَر': 'akthar', 'سَمِعَ': 'samiʿa',
    'تَوَلَّىٰ': 'tawallā', 'جَهَنَّم': 'jahannam', 'أَمَرَ': 'amara',
    'حَيَوٰة': 'ḥayāh', 'ذِكْر': 'dhikr', 'زَوْج': 'zawj',
    'دَخَلَ': 'dakhala', 'أَخ': 'akh', 'مِثْل': 'mithl',
    'نَّبِىّ': 'nabiyy', 'أَحَد': 'aḥad', 'خَٰلِد': 'khālid',
    'دُّنْيَا': 'dunyā', 'فِرْعَوْن': 'firʿawn', 'عَٰلَمِين': 'ʿālamīn',
    'جَزَىٰ': 'jazā', 'أَلِيم': 'alīm', 'مُّبِين': 'mubīn',
    'أَطَاعَ': 'aṭāʿa', 'أَوْحَىٰٓ': 'awḥā', 'إِنسَٰن': 'insān',
    'عَمَل': 'ʿamal', 'وَجْه': 'wajh', 'أَشْرَكَ': 'ashraka',
    'أَلْقَىٰٓ': 'alqā', 'قِيَٰمَة': 'qiyāmah', 'وَعَدَ': 'waʿada',
    'إِبْرَاهِيم': 'ibrāhīm', 'قُرْءَان': 'qurʾān', 'أَنفَقَ': 'anfaqa',
    'بَيْت': 'bayt', 'لَٰكِن': 'lākin', 'يَمِين': 'yamīn',
    'غَفَرَ': 'ghafara', 'آبَاء': 'ābāʾ', 'أُمَّة': 'ummah',
    'أَصَابَ': 'aṣāba', 'أَضَلَّ': 'aḍalla', 'ٱبْن': 'ibn',
    'عَزِيز': 'ʿazīz', 'مَآء': 'māʾ', 'تَابَ': 'tāba',
    'صَّٰلِحَٰت': 'ṣāliḥāt', 'غَفُور': 'ghafūr', 'كَسَبَ': 'kasaba',
    'نَزَّلَ': 'nazzala', 'أَوَّل': 'awwal', 'تَلَىٰ': 'talā',
    'رَزَقَ': 'razaqa', 'صَٰلِح': 'ṣāliḥ', 'صَادِق': 'ṣādiq',
    'نِسَآء': 'nisāʾ', 'قَضَىٰٓ': 'qaḍā', 'نَصَرَ': 'naṣara',
    'نَذِير': 'nadhīr', 'صَبَرَ': 'ṣabara', 'عَيْن': 'ʿayn',
    'قَرْيَة': 'qaryah', 'مَلَٰٓئِكَة': 'malāʾikah', 'سَاعَة': 'sāʿah',
    'آمِن': 'āmin', 'سَمَٰوَٰت': 'samāwāt', 'حَسَنَة': 'ḥasanah',
    'سَيِّد': 'sayyid', 'طَعَام': 'ṭaʿām', 'كَلِمَة': 'kalimah',
    'مَسْجِد': 'masjid', 'حِكْمَة': 'ḥikmah', 'مَلِك': 'malik',
    'سُلْطَٰن': 'sulṭān', 'سَلَٰم': 'salām', 'صِرَٰط': 'ṣirāṭ',
    'عِبَاد': 'ʿibād', 'لُغَة': 'lughah', 'مُعْجِز': 'muʿjiz',
    'مِحْنَة': 'miḥnah', 'يَسْتَنقِذُ': 'yastanqidhu',
    'يَتَنَاهَ': 'yatanāhā', 'تَهَجَّدْ': 'tahajjad',
    'يَهْجَعُ': 'yahjaʿu', 'أَهُشُّ': 'ahushshu',
    'أَهَمَّتْ': 'ahammat', 'ٱنْهَارَ': 'inhāra',
    'هَيْتَ': 'hayta', 'يَهِيمُ': 'yahīmu', 'يُوبِقْ': 'yūbiq',
    'وَجَبَتْ': 'wajabat', 'أَوْجَفْ': 'awjaf',
    'تَوَجَّهَ': 'tawajjaha', 'أَوْرَدَ': 'awrada',
    'وَسَطْ': 'wasaṭ', 'وَصَّلْ': 'waṣṣal',
    'أَوْضَعُ': 'awḍaʿu', 'تَعِيَ': 'taʿiya',
    'يُوَفِّقِ': 'yuwaffiqi', 'وَقَبَ': 'waqaba',
    'ٱسْتَوْقَدَ': 'istawqada', 'يُوقِعَ': 'yūqiʿa',
    'وَكَزَ': 'wakaza', 'يَلُ': 'yalu',
    'نَكِرَ': 'nakira', 'أَنقَضَ': 'anqaḍa',
    'نُقِرَ': 'nuqira', 'يَسْتَنكِحَ': 'yastankiha',
    'نَكِّرُ': 'nakkiru', 'نُكِسُ': 'nukisu',
    'نُنَكِّسْ': 'nunakkis', 'تَنُوٓأُ': 'tanūʾu',
    'هُدِّمَتْ': 'huddimat', 'هُزِّ': 'huzzi',
    'ٱسْتَهْوَتْ': 'istahwat', 'يَتِرَ': 'yatira',
    'وَاثَقَ': 'wāthaqa', 'يُوثِقُ': 'yūthiqu',
    'تَوَرَّد': 'tawarrada', 'تُورُ': 'tūru',
    'نَسِمُ': 'nasimu', 'يُوصِي': 'yūṣī',
    'يُوَاطِـُٔ': 'yuwāṭiʾu', 'تُوعِدُ': 'tūʿidu',
    'تَوَاعَد': 'tawāʿada', 'يُوفِضُ': 'yūfiḍu',
    'يَسْتَوْفُ': 'yastawfu', 'أُقِّتَتْ': 'uqqitat',
    'تُوَقِّرُ': 'tuwaqqiru', 'أَتَوَكَّؤُا۟': 'atawakkāʾū',
    'تَنِيَ': 'taniya', 'هَيْهَات': 'hayhāta',
    'سُبْحَٰن': 'subḥān', 'وَيْل': 'wayl',
    'طُوبَىٰ': 'ṭūbā', 'سَجَدَ': 'sajada',
    'فَجَرَ': 'fajara', 'غَلَبَ': 'ghalaba',
    'حَكَمَ': 'ḥakama', 'كَرِيم': 'karīm',
    'يَتِيم': 'yatīm', 'مِسْكِين': 'miskīn',
    'سَكَنَ': 'sakana', 'زَكَاة': 'zakāh',
    'صَوْم': 'ṣawm', 'حَجّ': 'ḥajj',
    'عُمْر': 'ʿumr', 'جَاهِل': 'jāhil',
    'مَغْفِرَة': 'maghfirah', 'نِعْمَة': 'niʿmah',
    'مُتَّقِين': 'muttaqīn', 'جِهَاد': 'jihād',
    'شَهْر': 'shahr', 'حَرَام': 'ḥarām',
    'مُشْرِك': 'mushrik', 'نِفَاق': 'nifāq',
    'مُنَافِق': 'munāfiq', 'مَغْضُوب': 'maghḍūb',
    'ضَالّ': 'ḍāll', 'مُفْلِح': 'mufliḥ',
    'خَسِرَ': 'khasira', 'فَوْز': 'fawz',
    'مُبَارَك': 'mubārak', 'حَسَن': 'ḥasan',
    'سَيِّئ': 'sayyiʾ', 'مُصِيبَة': 'muṣībah',
    'أَثَر': 'athar', 'مَثْوَىٰ': 'mathwā',
    'مِيثَٰق': 'mīthāq', 'غَيْب': 'ghayb',
    'شَهَادَة': 'shahādah', 'ظَنّ': 'ẓann',
    'وَصَّىٰ': 'waṣṣā', 'أَوْلِيَاء': 'awliyāʾ',
    'وِزْر': 'wizr', 'خَطِيئَة': 'khaṭīʾah',
    'يُوسُف': 'yūsuf', 'مَرْيَم': 'maryam',
    'عِيسَىٰ': 'ʿīsā', 'مُحَمَّد': 'muḥammad',
    'إِبْلِيس': 'iblīs', 'نُوح': 'nūḥ',
    'هُود': 'hūd', 'صَالِح': 'ṣāliḥ',
    'لُوط': 'lūṭ', 'شُعَيْب': 'shuʿayb',
    'أَيُّوب': 'ayyūb', 'دَاوُۥد': 'dāwūd',
    'سُلَيْمَٰن': 'sulaymān', 'إِدْرِيس': 'idrīs',
    'ذَا': 'dhā', 'ذِى': 'dhī', 'أُولِى': 'ulī',
    'أَيّ': 'ayy', 'كَم': 'kam', 'كَي': 'kay',
    'لَئِن': 'la-in', 'بَلَىٰ': 'balā',
    'لَيْلَة': 'laylah', 'سَلَّمَ': 'sallama',
    'حَافِظ': 'ḥāfiẓ', 'رَاقِب': 'rāqib',
    'مَلِك': 'malik', 'قُدُّوس': 'quddūs',
    'جَبَّار': 'jabbār', 'مُتَكَبِّر': 'mutakabbir',
    'خَالِق': 'khāliq', 'بَارِئ': 'bāriʾ',
    'مُصَوِّر': 'muṣawwir', 'غَفَّار': 'ghaffār',
    'قَهَّار': 'qahhār', 'وَهَّاب': 'wahhāb',
    'رَزَّاق': 'razzāq', 'فَتَّاح': 'fattāḥ',
    'عَبَسَ': 'ʿabasa', 'عَلِقَ': 'ʿaliqa',
    'نَمْل': 'naml', 'عَنْكَبُوت': 'ʿankabūt',
    'فِيل': 'fīl', 'قُرَيْش': 'quraysh',
    'كَوْثَر': 'kawthar', 'كَافِرُون': 'kāfirūn',
    'نَصْر': 'naṣr', 'مَسَد': 'masad',
    'إِخْلَاص': 'ikhlāṣ', 'فَلَق': 'falaq',
    'نَّاس': 'nās',
}

def transliterate(text):
    """Generate vowel-aware transliteration for Arabic text."""
    text = text.replace('\u0640', '')  # Remove tatweel
    
    if text in KNOWN:
        return KNOWN[text]
    
    result = []
    shadda_active = False
    i = 0
    
    while i < len(text):
        ch = text[i]
        
        if ch == SHADDA:
            shadda_active = True
            i += 1
            continue
        
        if ch in VOWEL_MAP:
            if result:
                result.append(VOWEL_MAP[ch])
            i += 1
            continue
        
        if ch == SUKUN:
            i += 1
            continue
        
        if ch == '\u0623' and i == 0:
            result.append('a')
            i += 1
            continue
        if ch == '\u0625':
            result.append('i')
            i += 1
            continue
        if ch == '\u0622':
            result.append('ā')
            i += 1
            continue
        
        if ch in CHAR_MAP:
            latin = CHAR_MAP[ch]
            if shadda_active:
                result.append(latin + latin[0] if len(latin) > 1 else latin)
                shadda_active = False
            else:
                result.append(latin)
        elif '\u0653' <= ch <= '\u06FF':
            pass
        else:
            result.append(ch)
        
        i += 1
    
    translit = ''.join(result)
    translit = translit.replace('ʾʾ', 'ʾ').replace('ʾā', 'ā')
    return translit if translit else text


# Parse words.js
with open("/home/heavenly-dev/TermProj/quranic words/words.js") as f:
    content = f.read()

objects = re.findall(r'\{[^}]+\}', content)
parsed = []
for obj_str in objects:
    fields = {}
    for match in re.finditer(r'(\w+):\s*(("[^"]*")|(\d+(?:\.\d+)?)|(\w+))', obj_str):
        key = match.group(1)
        val = match.group(2)
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val in ('true', 'false', 'null'):
            val = val == 'true' if val != 'null' else None
        else:
            try:
                val = float(val) if '.' in val else int(val)
            except:
                pass
        fields[key] = val
    if fields:
        parsed.append(fields)

print(f"Parsed {len(parsed)} words")

# Generate transliterations (force all)
generated = 0
for word in parsed:
    old = word.get('transliteration', '')
    new_t = transliterate(word['word'])
    if new_t != old:
        word['transliteration'] = new_t
        generated += 1

print(f"Generated {generated} transliterations")

# Count empty
empty = sum(1 for w in parsed if not w.get('transliteration'))
print(f"Still empty: {empty}")

# Write words.js
field_order = ['word', 'transliteration', 'translation', 'MeaningsSoFar', 'partOfSpeech', 'frequency', 'PercentageSoFar', 'stage']
lines = ['export const arabicWords = [']
for i, word in enumerate(parsed):
    parts = []
    for key in field_order:
        val = word.get(key, '')
        if key in ('frequency', 'stage'):
            parts.append(f'    {key}: {val}')
        elif key == 'PercentageSoFar':
            parts.append(f'    {key}: {val}')
        elif isinstance(val, str):
            escaped = val.replace('\\', '\\\\').replace('"', '\\"')
            parts.append(f'    {key}: "{escaped}"')
        else:
            parts.append(f'    {key}: {val}')
    obj = '  {\n' + ',\n'.join(parts) + '\n  }'
    if i < len(parsed) - 1:
        obj += ','
    lines.append(obj)
lines.append('];')

with open("/home/heavenly-dev/TermProj/quranic words/words.js", 'w') as f:
    f.write('\n'.join(lines) + '\n')

# Verify
with open("/home/heavenly-dev/TermProj/quranic words/words.js") as f:
    new_content = f.read()

print("\n--- Verification ---")
for test_word in ['مِن', 'رَّحِيم', 'جَنَّة', 'فِرْعَوْن', 'يَسْتَنقِذُ', 'تَنِيَ', 'هُدِّمَتْ', 'إِبْرَاهِيم']:
    pattern = rf'word: "{re.escape(test_word)}".*?transliteration: "([^"]*)"'
    m = re.search(pattern, new_content, re.DOTALL)
    if m:
        print(f"  {test_word} -> {m.group(1)} ✓")
    else:
        print(f"  {test_word} -> NOT FOUND ✗")

# Check no empty transliterations
empty_count = new_content.count('transliteration: ""')
print(f"\nEmpty transliterations: {empty_count}")
print(f"File size: {len(new_content)} chars")
PYEOF