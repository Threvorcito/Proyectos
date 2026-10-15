"""Metodo FAS phoneme table: what the child hears for each letter.

Continuants are elongated; stops are said with their following vowel. The
letter name is never used. Recording a sound later only needs an entry in
PHONEME_AUDIO, keyed by the spoken string.
"""

SOUND_TABLE = {
    'm': 'mmm', 'n': 'nnn', 'ñ': 'ñññ', 'l': 'lll', 's': 'sss', 'z': 'sss',
    'f': 'fff', 'j': 'jjj', 'r': 'rrr', 'rr': 'rrr', 'y': 'yyy', 'll': 'yyy',
    'h': '', 'w': 'u',
}
STOPS = frozenset({'p', 't', 'c', 'k', 'qu', 'b', 'v', 'd', 'g', 'gu', 'ch', 'x'})
SOFT_BEFORE_E_I = {'c': 'sss', 'g': 'jjj'}
SOFT_TRIGGERS = frozenset('eéií')

# spoken string ('mmm', 'pa', ...) -> static audio URL
PHONEME_AUDIO = {}


def audio_for(say):
    return PHONEME_AUDIO.get(say, '')
