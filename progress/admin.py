from django.contrib import admin

from .models import ActivityAttempt, StudentDifficulty, StudentProgress


admin.site.register(ActivityAttempt)
admin.site.register(StudentProgress)
admin.site.register(StudentDifficulty)
