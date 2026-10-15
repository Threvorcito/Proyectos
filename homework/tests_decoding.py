from unittest import mock

from django.template import Context, Template
from django.test import SimpleTestCase

from .decoding import decode_map, decode_word, propose_hard_words
from .phonemes import PHONEME_AUDIO, audio_for

# Names of continuant letters: a child must hear the sound, never these.
CONTINUANT_LETTER_NAMES = {
    'eme', 'ese', 'ele', 'ene', 'efe', 'erre', 'jota', 'ye', 'i griega', 'eñe', 'elle',
}


def blends(d):
    return [[d['letters'][i]['say'] for i in s['blend']] for s in d['syllables']]


class DecodeWordTests(SimpleTestCase):
    def test_continuants_elongated(self):
        d = decode_word('leyeron')
        self.assertEqual([l['text'] for l in d['letters']], ['l', 'e', 'y', 'e', 'r', 'o', 'n'])
        self.assertEqual(blends(d), [['lll', 'e'], ['yyy', 'e'], ['rrr', 'o', 'nnn']])

    def test_stops_said_as_syllable(self):
        self.assertEqual(blends(decode_word('pato')), [['pa'], ['to']])
        self.assertEqual(decode_word('pato')['letters'][0]['say'], 'pa')
        self.assertEqual(blends(decode_word('tren')), [['tre', 'nnn']])
        self.assertEqual(blends(decode_word('queso')), [['que'], ['sss', 'o']])

    def test_soft_c_and_g(self):
        self.assertEqual(blends(decode_word('cena')), [['sss', 'e'], ['nnn', 'a']])
        self.assertEqual(blends(decode_word('gente')), [['jjj', 'e', 'nnn'], ['te']])
        self.assertEqual(blends(decode_word('gato')), [['ga'], ['to']])

    def test_silent_h_and_coda_stop(self):
        self.assertEqual(blends(decode_word('hola')), [['o'], ['lll', 'a']])
        self.assertEqual(blends(decode_word('insecto')), [['i', 'nnn'], ['sss', 'e'], ['to']])

    def test_never_letter_names(self):
        text = 'mamá nene sol efe jirafa perro yema llave ñandú zorro hola gente tren'
        for word in text.split():
            for letter in decode_word(word)['letters']:
                self.assertNotIn(letter['say'], CONTINUANT_LETTER_NAMES, word)

    def test_audio_override(self):
        with mock.patch.dict(PHONEME_AUDIO, {'mmm': '/static/audio/m.mp3'}):
            self.assertEqual(decode_word('mesa')['letters'][0]['audio'], '/static/audio/m.mp3')
        self.assertEqual(audio_for('mmm'), '')

    def test_case_accents_and_punctuation(self):
        self.assertEqual(decode_map('¿Leyeron?')['leyeron'], decode_word('leyeron'))
        self.assertEqual(decode_map('Pingüino')['pingüino'], decode_word('pingüino'))
        self.assertEqual(decode_map('Ñandú')['ñandú'], decode_word('ñandú'))
        self.assertEqual(blends(decode_word('ñandú'))[0], ['ñññ', 'a', 'nnn'])
        self.assertEqual(decode_word('pingüino')['letters'][3]['say'], 'gu')

    def test_nfc_normalization(self):
        self.assertEqual(set(decode_map('Pingüino Ñandú')), {'pingüino', 'ñandú'})


class DecodeMapTests(SimpleTestCase):
    def test_decode_map_keys_are_lowercase_words(self):
        self.assertEqual(set(decode_map('¿Leyeron el libro? ¡Leyeron!')), {'leyeron', 'el', 'libro'})

    def test_limit(self):
        self.assertEqual(list(decode_map('a b c d', limit=2)), ['a', 'b'])

    def test_propose_hard_words(self):
        self.assertEqual(
            propose_hard_words('El murciélago y la mariposa leyeron un libro', 3),
            ['murciélago', 'mariposa', 'leyeron'],
        )


class TemplateTagTests(SimpleTestCase):
    def test_template_tag_outputs_json_script(self):
        out = Template('{% load decoding %}{% decode_map text %}').render(Context({'text': 'Leyeron'}))
        self.assertIn('id="decode-map-', out)
        self.assertIn('"leyeron"', out)
