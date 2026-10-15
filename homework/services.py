from typing import Iterable

from learning.models import StudentProfile, TeacherProfile

from .models import Task, TaskAssignment


def group_students(teacher: TeacherProfile, grade: str):
    return teacher.students.filter(grade=grade)


def assign_students(task: Task, students: Iterable[StudentProfile]) -> int:
    """Create the missing assignments for the teacher's own students; return how many were created."""
    allowed = set(task.teacher.students.values_list('pk', flat=True))
    wanted = {student.pk for student in students} & allowed
    existing = set(task.assignments.filter(student_id__in=wanted).values_list('student_id', flat=True))
    created = TaskAssignment.objects.bulk_create(
        TaskAssignment(task=task, student_id=pk) for pk in sorted(wanted - existing)
    )
    return len(created)
