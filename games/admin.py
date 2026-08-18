from django.contrib import admin

from .models import Game, GameAttempt


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'game_type', 'level', 'is_active')
    list_filter = ('game_type', 'level', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(GameAttempt)
class GameAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'game', 'correct_answers', 'total_questions', 'score', 'completed', 'completed_at')
    list_filter = ('completed', 'game')
