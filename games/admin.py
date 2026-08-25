from django.contrib import admin

from .models import Game, GameAttempt, GameAttemptAnswer


class GameAttemptAnswerInline(admin.TabularInline):
    model = GameAttemptAnswer
    extra = 0
    readonly_fields = ('subject', 'question', 'correct_answer', 'selected_answer', 'is_correct', 'attempts_used', 'order')
    can_delete = False


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'game_type', 'level', 'is_active')
    list_filter = ('game_type', 'level', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(GameAttempt)
class GameAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'game', 'correct_answers', 'total_questions', 'score', 'completed', 'completed_at')
    list_filter = ('completed', 'game')
    inlines = (GameAttemptAnswerInline,)


@admin.register(GameAttemptAnswer)
class GameAttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'subject', 'is_correct', 'attempts_used', 'correct_answer')
    list_filter = ('subject', 'is_correct')
    search_fields = ('question', 'correct_answer', 'selected_answer')
