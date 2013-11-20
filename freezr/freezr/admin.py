from django.contrib import admin
from freezr.models import *

def setup():
    admin.autodiscover()
    admin.site.register(Domain)
    admin.site.register(Account)
    admin.site.register(Project)
