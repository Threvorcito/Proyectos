import json
from unittest import mock

from django.template import Context, Template
from django.test import SimpleTestCase
from django.urls import reverse

from readings.models import Reading

from .decoding import decode_map, decode_word, propose_hard_words
from .models import DecodeHelpEvent, TaskAssignment
from .phonemes import PHONEME_AUDIO, audio_for
from .services import append_step, record_decode_help
from .tests_student import StudentTaskTestCase

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
        self.assertEqual(blends(decode_word('insecto')), [['i', 'nnn'], ['sec'], ['to']])

    def test_coda_stop_syllable_blended_whole(self):
        self.assertEqual(blends(decode_word('doctor')), [['doc'], ['to', 'rrr']])
        self.assertEqual(blends(decode_word('ciudad'))[-1], ['dad'])
        self.assertEqual(blends(decode_word('acción'))[0], ['ac'])
        self.assertEqual(blends(decode_word('acto')), [['ac'], ['to']])
        self.assertEqual(blends(decode_word('extra'))[0], ['ex'])

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


class DecodeHelpTests(StudentTaskTestCase):
    def help_url(self, assignment=None):
        return reverse('homework:decode_help', args=[(assignment or self.assignment).pk])

    def send(self, body):
        return self.client.post(self.help_url(), data=json.dumps(body), content_type='application/json')

    def test_decode_help_records_event(self):
        response = self.send({'word': 'Leyeron', 'step_order': 2})
        self.assertEqual(response.json(), {'saved': True})
        event = DecodeHelpEvent.objects.get()
        self.assertEqual((event.word, event.step.order, event.assignment), ('leyeron', 2, self.assignment))

    def test_decode_help_without_known_step_is_saved_with_no_step(self):
        self.send({'word': 'sol', 'step_order': None})
        self.send({'word': 'luz', 'step_order': 99})
        self.assertEqual(
            list(DecodeHelpEvent.objects.order_by('pk').values_list('word', 'step')), [('sol', None), ('luz', None)]
        )

    def test_decode_help_rejects_empty_word(self):
        self.assertEqual(self.send({'word': '   ', 'step_order': 1}).status_code, 400)
        self.assertEqual(self.send({'step_order': 1}).status_code, 400)
        self.assertEqual(self.send({'word': 12}).status_code, 400)
        self.assertFalse(DecodeHelpEvent.objects.exists())

    def test_decode_help_rejects_bad_json_and_bad_step_order(self):
        response = self.client.post(self.help_url(), data='nope', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.send({'word': 'sol', 'step_order': 'x'}).status_code, 400)
        self.assertEqual(self.send({'word': 'sol', 'step_order': True}).status_code, 400)

    def test_decode_help_is_post_only(self):
        self.assertEqual(self.client.get(self.help_url()).status_code, 405)

    def test_decode_help_other_student_404(self):
        self.client.login(username='beto', password='x')
        self.assertEqual(self.send({'word': 'sol'}).status_code, 404)
        self.assertFalse(DecodeHelpEvent.objects.exists())

    def test_decode_help_not_for_teachers(self):
        self.client.login(username='maestra', password='x')
        self.assertNotEqual(self.send({'word': 'sol'}).status_code, 200)
        self.assertFalse(DecodeHelpEvent.objects.exists())

    def test_record_decode_help_normalizes_and_truncates(self):
        event = record_decode_help(self.assignment, None, '  ' + 'Á' * 100 + ' ')
        self.assertEqual(event.word, 'á' * 80)
        self.assertEqual(DecodeHelpEvent.objects.get().word, 'á' * 80)


class DecodableChildTextTests(StudentTaskTestCase):
    def test_contesta_step_ships_decode_map_and_decodable_text(self):
        self.mira.delete()
        html = self.client.get(self.step_url(2)).content.decode()
        self.assertIn('data-decodable', html)
        self.assertIn('id="decode-map-', html)
        self.assertIn('"conejo"', html)
        self.assertIn('class="decode-overlay"', html)
        self.assertIn('js/homework/decode.js', html)

    def test_contesta_options_get_a_sounds_button(self):
        self.mira.delete()
        html = self.client.get(self.step_url(2)).content.decode()
        self.assertIn('data-decode-option="zanahoria"', html)

    def test_mira_step_is_decodable(self):
        html = self.client.get(self.step_url(1)).content.decode()
        self.assertIn('data-decodable', html)
        self.assertIn('"conejo"', html)

    def test_lectura_step_text_is_decodable(self):
        task = self._task(title='Leer')
        append_step(task, 'lectura', {'text': 'Los pingüinos nadan'})
        assignment = TaskAssignment.objects.create(task=task, student=self.ana)
        html = self.client.get(self.step_url(1, assignment=assignment)).content.decode()
        self.assertIn('data-decode-text', html)
        self.assertIn('"ping' + chr(92) + 'u00fcinos"', html)  # json_script escapes non-ASCII
        self.assertIn('class="decode-overlay"', html)

    def test_student_step_tells_the_player_where_to_log_help(self):
        html = self.client.get(self.step_url(1)).content.decode()
        self.assertIn('data-help-url="%s"' % reverse('homework:decode_help', args=[self.assignment.pk]), html)
        self.assertIn('data-step-order="1"', html)

    def test_preview_has_overlay_but_no_help_url(self):
        self.client.login(username='maestra', password='x')
        html = self.client.get(reverse('homework:task_preview', args=[self.task.pk])).content.decode()
        self.assertEqual(html.count('class="decode-overlay"'), 1)
        self.assertIn('data-decodable', html)
        self.assertNotIn('/ayuda/', html)

    def test_overlay_copy(self):
        html = self.client.get(self.step_url(1)).content.decode()
        for text in ('Vamos a leer esta palabra', 'Toca cada letra para escuchar su sonido.',
                     'Juntar los sonidos', 'Otra vez', 'aria-label="Cerrar"'):
            self.assertIn(text, html)

    def test_reading_detail_is_decodable(self):
        reading = Reading.objects.create(title='R', content='Leyeron un libro', level=self.level, grade='1')
        html = self.client.get(reverse('readings:detail', args=[reading.pk])).content.decode()
        self.assertIn('data-decodable', html)
        self.assertIn('"leyeron"', html)
        self.assertIn('class="decode-overlay"', html)
        self.assertIn('js/homework/decode.js', html)


class PalabrasStepTests(StudentTaskTestCase):
    def setUp(self):
        super().setUp()
        self.palabras_task = self._task(title='Palabras')
        append_step(self.palabras_task, 'palabras', {'words': ['leyeron', 'libro', 'sol']})
        self.palabras_assignment = TaskAssignment.objects.create(task=self.palabras_task, student=self.ana)

    def done(self, index):
        return self.client.post(
            self.step_url(1, 'step_done', self.palabras_assignment),
            data=json.dumps({'item_index': index}),
            content_type='application/json',
        ).json()

    def test_palabras_step_renders_one_card_per_word(self):
        html = self.client.get(self.step_url(1, assignment=self.palabras_assignment)).content.decode()
        self.assertEqual(html.count('data-palabra="'), 3)
        self.assertIn('data-step-type="palabras"', html)
        self.assertIn('"leyeron"', html)

    def test_palabras_items_complete_step(self):
        self.assertFalse(self.done(0)['step_done'])
        self.assertFalse(self.done(1)['step_done'])
        self.assertTrue(self.done(2)['step_done'])

    def test_finished_words_come_back_starred(self):
        self.done(1)
        html = self.client.get(self.step_url(1, assignment=self.palabras_assignment)).content.decode()
        self.assertEqual(html.count('is-done'), 1)
