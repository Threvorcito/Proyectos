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


class KidNavCharacterTests(TestCase):
    def setUp(self):
        from accounts.models import CustomUser
        from learning.models import Level, StudentProfile

        level = Level.objects.create(number=1, name='Inicial')
        user = CustomUser.objects.create_user(
            username='kidchars', email='kidchars@example.com', password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        StudentProfile.objects.create(
            user=user, name='Kid Chars', grade='1', reading_level=level, current_level=level,
        )
        self.user = user
        self.teacher = CustomUser.objects.create_user(
            username='teachchars', email='teachchars@example.com', password='Demo12345!',
            role=CustomUser.Role.TEACHER,
        )

    def test_kid_nav_pages_render_a_character_badge(self):
        self.client.force_login(self.user)
        for name, character in (
            ('activities:list', 'hummingbird'), ('games:index', 'jaguar'),
            ('readings:list', 'fox'), ('progress:overview', 'jaguar'),
        ):
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertIn('css/characters.css?v=20261016-chars-3', html)
                self.assertIn(f'char-badge char-badge--{character}', html)
                self.assertIn(f'char char--{character}', html)

    def test_practice_grade_cards_show_level_characters(self):
        self.client.force_login(self.teacher)
        html = self.client.get(reverse('activities:list')).content.decode()
        for name in ('turtle', 'bunny', 'fox'):
            self.assertIn(f'activity-grade-card__char char-badge char-badge--{name}', html)
