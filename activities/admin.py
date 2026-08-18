from django.contrib import admin

from .models import Activity, ActivityOption


class ActivityOptionInline(admin.TabularInline):
    model = ActivityOption
    extra = 3


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'activity_type', 'level', 'difficulty', 'is_active')
    inlines = [ActivityOptionInline]
