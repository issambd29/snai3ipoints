from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Student, Teacher, Classroom
import json


# =========================
# AUTH
# =========================

def signin_view(request):
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        # find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'signin.html', {'error': 'No account found with that email.'})

        user = authenticate(request, username=user.username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'signin.html', {'error': 'Wrong password.'})

    return render(request, 'signin.html')


def signout_view(request):
    logout(request)
    return redirect('signin')


# =========================
# ROLE ROUTER
# =========================

@login_required(login_url='/signin/')
def home(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    if Teacher.objects.filter(user=request.user).exists():
        return redirect('dashboard')
    if Student.objects.filter(user=request.user).exists():
        return redirect('student_dashboard')
    # unknown role — sign out
    logout(request)
    return redirect('signin')


# =========================
# TEACHER DASHBOARD
# =========================

def get_teacher_classroom(user):
    try:
        teacher = Teacher.objects.get(user=user)
        return Classroom.objects.filter(teacher=teacher).first()
    except Teacher.DoesNotExist:
        return None


@login_required(login_url='/signin/')
def dashboard(request):
    if not Teacher.objects.filter(user=request.user).exists():
        return redirect('home')

    classroom = get_teacher_classroom(request.user)
    students  = []
    if classroom:
        students = classroom.students.select_related('user').order_by('-points')

    return render(request, 'dashboard.html', {
        'students':  students,
        'classroom': classroom,
    })


# =========================
# STUDENT DASHBOARD
# =========================

@login_required(login_url='/signin/')
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('home')

    classroom           = Classroom.objects.filter(students=student).first()
    rank                = 1
    total_students      = 1
    points_to_next_coin = 10
    progress_pct        = 0

    if classroom:
        rank                = classroom.students.filter(points__gt=student.points).count() + 1
        total_students      = classroom.students.count()

    points_in_block     = student.points % 10
    points_to_next_coin = 10 - points_in_block if points_in_block > 0 else 10
    progress_pct        = (points_in_block / 10) * 100

    return render(request, 'student_dashboard.html', {
        'student':             student,
        'classroom':           classroom,
        'rank':                rank,
        'total_students':      total_students,
        'points_to_next_coin': points_to_next_coin,
        'progress_pct':        int(progress_pct),
    })


# =========================
# ADMIN DASHBOARD
# =========================

@login_required(login_url='/signin/')
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('home')

    classrooms   = Classroom.objects.select_related('teacher__user').prefetch_related('students__user')
    all_students = []
    seen_ids     = set()

    for classroom in classrooms:
        for student in classroom.students.select_related('user').order_by('-points'):
            if student.id not in seen_ids:
                seen_ids.add(student.id)
                all_students.append({
                    'student':        student,
                    'classroom_name': classroom.name,
                    'teacher_name':   f'{classroom.teacher.user.first_name} {classroom.teacher.user.last_name}',
                })

    all_students.sort(key=lambda x: x['student'].points, reverse=True)

    teachers = Teacher.objects.select_related('user').prefetch_related('classroom_set__students')
    totals   = Student.objects.aggregate(tp=Sum('points'), tc=Sum('coins'))

    return render(request, 'admin_dashboard.html', {
        'students':         all_students,
        'classrooms':       classrooms,
        'teachers':         teachers,
        'total_students':   len(all_students),
        'total_classrooms': classrooms.count(),
        'total_teachers':   teachers.count(),
        'total_points':     totals['tp'] or 0,
        'total_coins':      totals['tc'] or 0,
    })


# =========================
# ADMIN — ADD / DELETE TEACHER
# =========================

@csrf_exempt
@login_required(login_url='/signin/')
def add_teacher(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Forbidden'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})

        first          = data.get('first_name', '').strip()
        last           = data.get('last_name', '').strip()
        email          = data.get('email', '').strip()
        password       = data.get('password', '').strip()
        classroom_name = data.get('classroom_name', 'My Class').strip() or 'My Class'

        if not first or not email or not password:
            return JsonResponse({'success': False, 'error': 'First name, email and password are required.'})

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'A user with that email already exists.'})

        user = User.objects.create_user(
            username=email, email=email, password=password,
            first_name=first, last_name=last,
        )
        teacher = Teacher.objects.create(user=user)
        Classroom.objects.create(name=classroom_name, teacher=teacher)

        return JsonResponse({
            'success':      True,
            'teacher_id':   teacher.id,
            'name':         f'{first} {last}',
            'email':        email,
            'classroom':    classroom_name,
        })

    return JsonResponse({'success': False, 'error': 'Invalid method'})


@csrf_exempt
@login_required(login_url='/signin/')
def delete_teacher(request, teacher_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Forbidden'})

    if request.method == 'POST':
        teacher = get_object_or_404(Teacher, id=teacher_id)
        # remove classrooms; students remain in DB but lose classroom link
        Classroom.objects.filter(teacher=teacher).delete()
        user = teacher.user
        teacher.delete()
        user.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid method'})


# =========================
# TEACHER — ADD / EDIT / DELETE STUDENT
# =========================

@csrf_exempt
@login_required(login_url='/signin/')
def add_student(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})

        name     = data.get('name', '').strip()
        division = data.get('division', '').strip()
        email    = data.get('email', '').strip()
        password = data.get('password', '').strip()
        age      = data.get('age', 0)

        if not name or not email or not password:
            return JsonResponse({'success': False, 'error': 'Name, email and password are required.'})

        try:
            age = int(age)
        except (ValueError, TypeError):
            age = 0

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'A user with that email already exists.'})

        classroom = get_teacher_classroom(request.user)
        if classroom is None:
            return JsonResponse({'success': False, 'error': 'No classroom found for your account.'})

        first, last = name.split(' ', 1) if ' ' in name else (name, '')

        student_user = User.objects.create_user(
            username=email, email=email, password=password,
            first_name=first, last_name=last,
        )
        student = Student.objects.create(
            user=student_user, division=division, age=age, points=0, coins=0,
        )
        classroom.students.add(student)

        return JsonResponse({'success': True, 'student_id': student.id})

    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required(login_url='/signin/')
def get_student(request, student_id):
    classroom = get_teacher_classroom(request.user)
    if not classroom:
        return JsonResponse({'success': False, 'error': 'No classroom'})
    student = get_object_or_404(classroom.students, id=student_id)
    return JsonResponse({
        'success':  True,
        'name':     f'{student.user.first_name} {student.user.last_name}',
        'age':      student.age,
        'division': student.division,
        'email':    student.user.email,
    })


@csrf_exempt
@login_required(login_url='/signin/')
def update_student(request, student_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})

        classroom = get_teacher_classroom(request.user)
        if not classroom:
            return JsonResponse({'success': False, 'error': 'No classroom'})

        student  = get_object_or_404(classroom.students, id=student_id)
        name     = data.get('name', '').strip()
        division = data.get('division', '').strip()
        age      = data.get('age', 0)

        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required.'})

        try:
            age = int(age)
        except (ValueError, TypeError):
            age = 0

        first, last = name.split(' ', 1) if ' ' in name else (name, '')
        student.user.first_name = first
        student.user.last_name  = last
        student.user.save()
        student.division = division
        student.age      = age
        student.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid method'})


@csrf_exempt
@login_required(login_url='/signin/')
def add_points(request, student_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}

        try:
            amount = int(data.get('amount', 1))
        except (ValueError, TypeError):
            amount = 1

        if amount < 1:
            return JsonResponse({'success': False, 'error': 'Amount must be at least 1.'})

        classroom = get_teacher_classroom(request.user)
        if not classroom:
            return JsonResponse({'success': False, 'error': 'No classroom'})

        student        = get_object_or_404(classroom.students, id=student_id)
        coins_before   = student.points // 10
        student.points += amount
        coins_after    = student.points // 10
        new_coins      = coins_after - coins_before
        student.coins += new_coins
        student.save()

        return JsonResponse({
            'success':   True,
            'points':    student.points,
            'coins':     student.coins,
            'new_coins': new_coins,
        })

    return JsonResponse({'success': False, 'error': 'Invalid method'})


@csrf_exempt
@login_required(login_url='/signin/')
def delete_student(request, student_id):
    if request.method == 'POST':
        classroom = get_teacher_classroom(request.user)
        if not classroom:
            return JsonResponse({'success': False, 'error': 'No classroom'})

        student      = get_object_or_404(classroom.students, id=student_id)
        classroom.students.remove(student)
        student_user = student.user
        student.delete()
        student_user.delete()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid method'})