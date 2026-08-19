from django.contrib import admin

from .models import AccessibilityPreference, CurriculumCompetency, FasStep, Lesson, LessonPlan, Level, MinedReference, MinedStrategy, ParentProfile, StudentProfile, Subject, Syllable, TeacherProfile, Word


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('number', 'name', 'order', 'is_active')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'stage', 'order', 'is_active')


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ('text', 'level')


@admin.register(Syllable)
class SyllableAdmin(admin.ModelAdmin):
    list_display = ('text', 'level')


admin.site.register(StudentProfile)
admin.site.register(TeacherProfile)
admin.site.register(ParentProfile)
admin.site.register(AccessibilityPreference)
admin.site.register(Subject)
admin.site.register(LessonPlan)
admin.site.register(MinedStrategy)
admin.site.register(CurriculumCompetency)
admin.site.register(FasStep)
admin.site.register(MinedReference)
