
# Create your views here.
from django.http import HttpResponse

def accueil(request):
    return HttpResponse("<h1>Bienvenue sur BiblioLearn</h1>")