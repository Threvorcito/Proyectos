"""Decode maps: per-word letter sounds and syllable blends for the child."""
import unicodedata

from .phonemes import SOFT_BEFORE_E_I, SOFT_TRIGGERS, SOUND_TABLE, STOPS, audio_for
from .syllables import VOWELS, WORD, syllable_units


def _vowel_say(text):
    if text == 'ü':
        return 'u'
    return 'i' if text == 'y' else text


def _spoken(text):
    return text.replace('ü', 'u')


def decode_word(word):
    word = unicodedata.normalize('NFC', word).lower()
    letters = []
    syllables = []
    flat = [unit for syl in syllable_units(word) for unit in syl]
    pos = 0
    for syl in syllable_units(word):
        start = pos
        texts = [u.text for u in syl]
        syllable_text = ''.join(texts)
        covered = set()
        coda_stops = set()
        for offset, unit in enumerate(syl):
            idx = start + offset
            nxt = flat[idx + 1].text if idx + 1 < len(flat) else ''
            if unit.is_vowel:
                say = _vowel_say(unit.text)
            elif unit.text in SOFT_BEFORE_E_I and nxt[:1] in SOFT_TRIGGERS:
                say = SOFT_BEFORE_E_I[unit.text]
            elif unit.text in SOUND_TABLE:
                say = SOUND_TABLE[unit.text]
            elif unit.text in STOPS:
                vowel = next((o for o in range(offset + 1, len(syl)) if syl[o].is_vowel), None)
                if vowel is None:
                    say = _spoken(syllable_text)
                    coda_stops.add(idx)
                else:
                    say = _spoken(''.join(texts[offset:vowel + 1]))
                    covered.update(start + o for o in range(offset + 1, vowel + 1))
            else:
                say = unit.text
            letters.append({'text': unit.text, 'say': say, 'audio': audio_for(say)})
        if coda_stops:
            # A closed stop syllable is blended whole ('doc', 'dad'), never split.
            blend = [min(coda_stops)]
        else:
            blend = [
                start + o for o in range(len(syl))
                if letters[start + o]['say'] != '' and (start + o) not in covered
            ]
        syllables.append({'text': syllable_text, 'blend': blend})
        pos += len(syl)
    return {'word': word, 'letters': letters, 'syllables': syllables}


def _words(text):
    return WORD.findall(unicodedata.normalize('NFC', text))


def decode_map(text, limit=400):
    result = {}
    for match in _words(text):
        key = match.lower()
        if key not in result:
            if len(result) >= limit:
                break
            result[key] = decode_word(key)
    return result


def propose_hard_words(text, count=6):
    seen = []
    for match in _words(text):
        key = match.lower()
        if len(key) >= 3 and key not in seen:
            seen.append(key)
    ranked = sorted(seen, key=lambda w: (-len(syllable_units(w)), -len(w)))
    return ranked[:count]
