from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("connexion/", views.CustomerLoginView.as_view(), name="customer_login"),
    path("inscription/", views.customer_signup, name="customer_signup"),
    path("mes-commandes/", views.mes_commandes, name="mes_commandes"),
    path("commander/<int:book_id>/", views.commander_livre, name="commander_livre"),
    path("dashboard/login/", views.DashboardLoginView.as_view(), name="dashboard_login"),
    path("livres/", views.livres, name="livres"),
    path("dashboard/", views.dashboard_admin, name="dashboard_admin"),
    path("dashboard/logout/", views.dashboard_logout, name="dashboard_logout"),
    path("emprunts/", views.emprunts, name="emprunts"),
    path("contact/", views.contact, name="contact"),
]
