from django.test import SimpleTestCase

from homework.writing import build_tiles, check_build, split_units


class WritingTests(SimpleTestCase):
    def test_split_units(self):
        self.assertEqual(split_units('carro', 'letter'), ['c', 'a', 'rr', 'o'])
        self.assertEqual(split_units('mariposa', 'syllable'), ['ma', 'ri', 'po', 'sa'])
        self.assertEqual(split_units('El gato come.', 'word'), ['El', 'gato', 'come'])
        with self.assertRaises(ValueError):
            split_units('el gato', 'syllable')
        with self.assertRaises(ValueError):
            split_units('el gato', 'letter')

    def test_build_tiles_counts_and_distractors(self):
        tiles = build_tiles(['ca', 'sa'], 'syllable', seed=1)
        self.assertEqual(len(tiles), 4)
        self.assertTrue({'ca', 'sa'} <= set(tiles))
        tiles = build_tiles(['m', 'a', 'm', 'á'], 'letter', seed=1)
        self.assertEqual(len(tiles), 7)
        self.assertIn('n', tiles)

    def test_confusable_syllable_swap(self):
        self.assertIn('da', build_tiles(['ba', 'sa'], 'syllable', seed=3))

    def test_word_fallback_pool(self):
        tiles = build_tiles(['sol'], 'word', seed=2)
        self.assertEqual(len(tiles), 3)

    def test_build_tiles_deterministic(self):
        a = build_tiles(['ma', 'ri', 'po', 'sa'], 'syllable', seed=7)
        self.assertEqual(a, build_tiles(['ma', 'ri', 'po', 'sa'], 'syllable', seed=7))
        self.assertTrue(any(
            build_tiles(['ma', 'ri', 'po', 'sa'], 'syllable', seed=s) != a for s in range(20)
        ))

    def test_distractors_never_equal_targets(self):
        for seed in range(20):
            tiles = build_tiles(['b', 'd', 'a'], 'letter', seed=seed)
            self.assertEqual(len(tiles), 6)
            self.assertEqual(sorted(t for t in tiles if t in ('b', 'd', 'a')), ['a', 'b', 'd'])
            self.assertEqual(len({t.casefold() for t in tiles}), 6)

    def test_check_build(self):
        self.assertEqual(check_build(['ca', 'sa'], ['Ca', 'sa']).status, 'correct')
        c = check_build(['ma', 'ri', 'po', 'sa'], ['ma', 'po', 'sa'])
        self.assertEqual((c.status, c.missing, c.hole_index), ('omission', [(1, 'ri')], 1))
        self.assertEqual(check_build(['g', 'a', 't', 'o'], ['g', 'a']).missing, [(2, 't'), (3, 'o')])
        self.assertEqual(check_build(['g', 'a', 't', 'o'], ['g', 'a', 'd', 'o']).status, 'wrong')
        self.assertEqual(check_build(['ca', 'sa'], ['sa', 'ca']).status, 'wrong')

    def test_wrong_has_no_missing(self):
        c = check_build(['ca', 'sa'], ['sa', 'ca'])
        self.assertEqual((c.missing, c.hole_index), ([], None))

    def test_missing_unit_is_capped_to_model_limit(self):
        c = check_build(['x' * 50, 'a'], ['a'])
        self.assertEqual(c.status, 'omission')
        self.assertEqual(len(c.missing[0][1]), 30)
