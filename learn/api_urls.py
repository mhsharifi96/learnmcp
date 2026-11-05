from django.urls import path

from learn import api

urlpatterns = [
    path("csrf", api.csrf),
    path("auth/me", api.whoami),
    path("auth/login", api.login_view),
    path("auth/logout", api.logout_view),
    path("auth/signup", api.signup),
    # students
    path("classes/<str:code>", api.class_info),
    path("classes/<str:code>/join", api.join_class),
    path("connect/<int:enrollment_id>", api.connect_info),
    path("enrollments/<int:enrollment_id>/regenerate", api.regenerate),
    path("enrollments/<int:enrollment_id>/leave", api.leave),
    path("me", api.my_data),
    path("restore", api.restore),
    # instructors
    path("teach/courses", api.teach_courses),
    path("teach/courses/<int:course_id>", api.teach_course),
    path("teach/courses/<int:course_id>/dashboard", api.teach_dashboard),
    path("teach/courses/<int:course_id>/review", api.teach_review),
    path("teach/courses/<int:course_id>/lessons", api.teach_lessons),
    path("teach/courses/<int:course_id>/quizzes", api.teach_quizzes),
    path("teach/lessons/<int:lesson_id>", api.teach_lesson),
    path("teach/quizzes/<int:quiz_id>", api.teach_quiz),
    path("teach/quizzes/<int:quiz_id>/questions", api.teach_questions),
    path("teach/questions/<int:question_id>", api.teach_question),
    path("teach/students/<int:enrollment_id>", api.teach_student),
    path("teach/answers/<int:answer_id>", api.teach_answer),
    path("teach/problems/<int:event_id>", api.teach_problem),
]
