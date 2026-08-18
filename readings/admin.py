from django.contrib import admin

from .models import Reading, ReadingAnswer, ReadingQuestion


class ReadingAnswerInline(admin.TabularInline):
    model = ReadingAnswer
    extra = 3


class ReadingQuestionInline(admin.StackedInline):
    model = ReadingQuestion
    extra = 1


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'difficulty', 'is_active')
    inlines = [ReadingQuestionInline]


admin.site.register(ReadingQuestion)
admin.site.register(ReadingAnswer)
