from django.shortcuts import render

from django.http import JsonResponse
from datetime import datetime

def days_until_new_year(request):

    now = datetime.now()
    next_year = now.year + 1
    new_year = datetime(next_year, 1, 1)
    delta = new_year - now
    return JsonResponse({"days_before_new_year": delta.days})