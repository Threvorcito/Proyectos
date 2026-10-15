from django.contrib import admin

from .models import DecodeHelpEvent, OmissionEvent, StepResult, Task, TaskAssignment, TaskStep


class TaskStepInline(admin.TabularInline):
    model = TaskStep
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'subject', 'grade', 'due_date', 'is_active')
    inlines = [TaskStepInline]


@admin.register(TaskStep)
class TaskStepAdmin(admin.ModelAdmin):
    list_display = ('task', 'order', 'step_type')


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'student', 'status', 'started_at', 'completed_at')


@admin.register(StepResult)
class StepResultAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'step', 'item_index', 'attempts', 'first_try_correct')


@admin.register(DecodeHelpEvent)
class DecodeHelpEventAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'word', 'created_at')


@admin.register(OmissionEvent)
class OmissionEventAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'target', 'missing_unit', 'position')
