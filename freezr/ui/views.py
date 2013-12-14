from django.shortcuts import render
from django.conf import settings


def index(request):
    context = {'api_root': settings.FREEZR_API_ROOT}
    return render(request, 'index.html', context)
