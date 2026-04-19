from django.db import models
from django.contrib.auth.models import User


class Student(models.Model):
    user     = models.OneToOneField(User, on_delete=models.CASCADE)
    points   = models.IntegerField(default=0)
    coins    = models.IntegerField(default=0)   # FIX: stored field, not a method
    age      = models.IntegerField(default=0)   # FIX: added age
    division = models.CharField(max_length=50, default="Class A")

    def __str__(self):
        return self.user.username


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class Classroom(models.Model):
    name     = models.CharField(max_length=100)
    teacher  = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    students = models.ManyToManyField(Student)

    def __str__(self):
        return self.name