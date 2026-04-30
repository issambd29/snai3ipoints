from django.urls import path
from .views import (
    signin_view, signout_view, home,
    dashboard, student_dashboard, admin_dashboard,
    add_teacher, delete_teacher,
    add_student, get_student, update_student,
    add_points, subtract_points, delete_student,
)

urlpatterns = [
    path('',                                      home,              name='home'),
    path('signin/',                               signin_view,       name='signin'),
    path('signout/',                              signout_view,      name='signout'),
    # dashboards
    path('dashboard/',                            dashboard,         name='dashboard'),
    path('student/',                              student_dashboard, name='student_dashboard'),
    path('admin-panel/',                          admin_dashboard,   name='admin_dashboard'),
    # admin — teacher management
    path('add-teacher/',                          add_teacher,       name='add_teacher'),
    path('delete-teacher/<int:teacher_id>/',      delete_teacher,    name='delete_teacher'),
    # teacher — student management
    path('add-student/',                          add_student,       name='add_student'),
    path('get-student/<int:student_id>/',         get_student,       name='get_student'),
    path('update-student/<int:student_id>/',      update_student,    name='update_student'),
    path('add-points/<int:student_id>/',          add_points,        name='add_points'),
    path('subtract-points/<int:student_id>/',     subtract_points,   name='subtract_points'),
    path('delete-student/<int:student_id>/',      delete_student,    name='delete_student'),
]