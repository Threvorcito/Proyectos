from django.test import SimpleTestCase

from homework.syllables import WORD, split_syllables, syllable_units, word_units

CASES = {
    'leyeron': ['le', 'ye', 'ron'], 'construyó': ['cons', 'tru', 'yó'], 'carro': ['ca', 'rro'],
    'muchacho': ['mu', 'cha', 'cho'], 'guitarra': ['gui', 'ta', 'rra'], 'árbol': ['ár', 'bol'],
    'pájaro': ['pá', 'ja', 'ro'], 'aéreo': ['a', 'é', 're', 'o'], 'blanco': ['blan', 'co'],
    'insecto': ['in', 'sec', 'to'], 'queso': ['que', 'so'], 'pingüino': ['pin', 'güi', 'no'],
    'río': ['rí', 'o'], 'país': ['pa', 'ís'], 'ciudad': ['ciu', 'dad'], 'ahora': ['a', 'ho', 'ra'],
    'hoy': ['hoy'], 'muy': ['muy'], 'rey': ['rey'], 'reyes': ['re', 'yes'], 'camión': ['ca', 'mión'],
    'atleta': ['a', 'tle', 'ta'], 'extraño': ['ex', 'tra', 'ño'], 'calle': ['ca', 'lle'],
    'pequeño': ['pe', 'que', 'ño'], 'agua': ['a', 'gua'], 'guerra': ['gue', 'rra'],
    'instante': ['ins', 'tan', 'te'], 'hablar': ['ha', 'blar'], 'y': ['y'], 'león': ['le', 'ón'],
}


class SyllablesTests(SimpleTestCase):
    def test_split_cases(self):
        for word, expected in CASES.items():
            with self.subTest(word=word):
                self.assertEqual(split_syllables(word), expected)

    def test_case_accents_and_punctuation(self):
        self.assertEqual(split_syllables('Leyeron'), ['Le', 'ye', 'ron'])
        self.assertEqual(split_syllables('Ñandú'), ['Ñan', 'dú'])
        self.assertEqual(split_syllables('Pingüino'), ['Pin', 'güi', 'no'])
        self.assertEqual(WORD.findall('¿Leyeron el Pingüino?'), ['Leyeron', 'el', 'Pingüino'])

    def test_units_digraphs(self):
        self.assertEqual([u.text for u in word_units('carro')], ['c', 'a', 'rr', 'o'])
        self.assertEqual([u.text for u in word_units('queso')], ['qu', 'e', 's', 'o'])
        self.assertEqual([u.is_vowel for u in word_units('rey')], [False, True, True])

    def test_join_is_identity(self):
        for word in CASES:
            with self.subTest(word=word):
                self.assertEqual(''.join(split_syllables(word)), word)
                self.assertEqual(''.join(u.text for s in syllable_units(word) for u in s), word)

    def test_no_vowel_word(self):
        self.assertEqual(split_syllables('psst'), ['psst'])
