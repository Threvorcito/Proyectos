from dashboard.views import (
    is_admin_user,
    is_report_admin_user,
    is_teacher,
    teacher_can_access_student,
    teacher_has_permission,
)


def can_manage_tasks(user) -> bool:
    return bool(is_teacher(user) and teacher_has_permission(user, 'can_assign_lesson_plans'))


def can_view_task(user, task) -> bool:
    if is_admin_user(user):
        return True
    return bool(can_manage_tasks(user) and task.teacher_id == user.teacher_profile.pk)


def can_view_difficulty_data(user, student) -> bool:
    # Ley 787: not user_can_view_student_report, which also admits parents.
    return bool(
        is_report_admin_user(user)
        or (teacher_has_permission(user, 'can_view_student_reports') and teacher_can_access_student(user, student))
    )


def difficulty_viewer(user):
    """Resolve the viewer once; the returned callable answers can_view_difficulty_data(user, student) per student."""
    if is_report_admin_user(user):
        return lambda student: True
    teacher = getattr(user, 'teacher_profile', None)
    if not (teacher_has_permission(user, 'can_view_student_reports') and is_teacher(user) and teacher is not None and teacher.is_active):
        return lambda student: False
    linked = set(teacher.students.values_list('pk', flat=True))
    return lambda student: student.pk in linked
