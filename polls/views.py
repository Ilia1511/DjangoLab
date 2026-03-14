from django.shortcuts import render

from django.http import JsonResponse
from datetime import datetime
from django.contrib.auth.hashers import make_password
def days_until_new_year(request):
    hash1 = make_password("test123")
    hash2 = make_password("test123")
    now = datetime.now()
    next_year = now.year + 1
    new_year = datetime(next_year, 1, 1)
    delta = new_year - now
    return JsonResponse({"fdsfds":hash1})

