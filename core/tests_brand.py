from django.test import TestCase
from django.urls import reverse


class BrandAssetsTests(TestCase):
    def test_base_renders_favicon_and_navbar_logo(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('favicon.ico', html)
        self.assertIn('apple-touch-icon', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn('brand-mark__logo', html)
        self.assertIn('Lectura sin Límites', html)


class LevelCharacterTests(TestCase):
    def test_home_renders_character_figures_hidden_from_assistive_tech(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('css/characters.css', html)
        for name in ('turtle', 'bunny', 'fox', 'owl', 'hummingbird', 'jaguar'):
            self.assertIn(f'char char--{name}', html)
        self.assertEqual(html.count('class="char '), 6)
        self.assertNotIn('>ABC</div>', html)
