
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    BookForm,
    CategoryForm,
    CustomerAuthenticationForm,
    CustomerSignupForm,
    DashboardAuthenticationForm,
    LibraryForm,
    LoanRequestForm,
    OrderPlacementForm,
)
from .models import Book, Category, Library, Loan, Order


class DashboardLoginView(LoginView):
    template_name = "pages/dashboard_login.html"
    authentication_form = DashboardAuthenticationForm
    next_page = "dashboard_admin"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect("dashboard_admin")
        return super().dispatch(request, *args, **kwargs)


class CustomerLoginView(LoginView):
    template_name = "pages/customer_login.html"
    authentication_form = CustomerAuthenticationForm
    next_page = "livres"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            destination = "dashboard_admin" if request.user.is_staff else "mes_commandes"
            return redirect(destination)
        return super().dispatch(request, *args, **kwargs)


def accueil(request):
    stats = [
        {"label": "Livres", "value": "1 240", "description": "Titres disponibles"},
        {"label": "Membres", "value": "860", "description": "Utilisateurs actifs"},
        {"label": "Emprunts", "value": "326", "description": "En cours"},
        {"label": "Avis", "value": "4.8/5", "description": "Satisfaction"},
    ]

    books = [
        {"title": "Le Prince de la Nuit", "category": "Roman", "author": "Nadia El Alaoui", "rating": 5},
        {"title": "L'Art de la Science", "category": "Culture générale", "author": "Omar Benali", "rating": 4},
        {"title": "Voyage au cœur du code", "category": "Technologie", "author": "Imane Rachid", "rating": 5},
    ]

    activity = [
        {"title": "Nouvelle acquisition", "text": "12 nouveaux titres ajoutés au catalogue cette semaine."},
        {"title": "Campagne de lecture", "text": "La semaine de la littérature jeunesse démarre lundi prochain."},
        {"title": "Retours de prêt", "text": "18 livres ont été rendus et réessayés aujourd'hui."},
    ]

    context = {
        "nom_projet": "BiblioLearn",
        "modules": ["Catalogue", "Comptes et rôles", "Emprunts", "Mini-cours"],
        "stats": stats,
        "books": books,
        "activity": activity,
    }
    return render(request, "pages/accueil.html", context)


def livres(request):
    categories = Category.objects.all()
    books = Book.objects.select_related("category")
    selected_category_id = None
    category_id = request.GET.get("category")
    if category_id:
        if not category_id.isdecimal():
            raise Http404("Catégorie introuvable.")
        selected_category = get_object_or_404(Category, pk=int(category_id))
        selected_category_id = selected_category.pk
        books = books.filter(category_id=selected_category_id)
    return render(
        request,
        "pages/livres.html",
        {
            "books": books,
            "categories": categories,
            "selected_category_id": selected_category_id,
        },
    )


@staff_member_required(login_url="dashboard_login")
def dashboard_admin(request):
    form = BookForm()
    category_form = CategoryForm()
    library_form = LibraryForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_book":
            form = BookForm(request.POST)
            if form.is_valid():
                book = form.save()
                messages.success(request, f"Le livre « {book.title} » a été ajouté au catalogue.")
                return redirect("dashboard_admin")
        elif action == "add_category":
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                category = category_form.save()
                messages.success(request, f"La catégorie « {category.name} » a été ajoutée.")
                return redirect("dashboard_admin")
        elif action == "add_library":
            library_form = LibraryForm(request.POST)
            if library_form.is_valid():
                library = library_form.save()
                messages.success(request, f"La bibliothèque « {library.name} » a été ajoutée.")
                return redirect("dashboard_admin")
        elif action in {"approve_loan", "reject_loan", "return_loan"}:
            loan_id = request.POST.get("loan_id")
            with transaction.atomic():
                loan = get_object_or_404(
                    Loan.objects.select_for_update().select_related("book"),
                    pk=loan_id,
                )
                if action == "approve_loan" and loan.status == Loan.Status.PENDING:
                    book = Book.objects.select_for_update().get(pk=loan.book_id)
                    if book.status != Book.Status.AVAILABLE:
                        messages.error(
                            request,
                            f"« {book.title} » n'est plus disponible; la demande reste en attente.",
                        )
                    else:
                        loan.approve()
                        loan.save(update_fields=["status", "due_date"])
                        book.status = Book.Status.BORROWED
                        book.save(update_fields=["status"])
                        messages.success(request, "La demande d'emprunt a été acceptée.")
                elif action == "reject_loan" and loan.status == Loan.Status.PENDING:
                    loan.status = Loan.Status.REJECTED
                    loan.save(update_fields=["status"])
                    messages.success(request, "La demande d'emprunt a été refusée.")
                elif action == "return_loan" and loan.status == Loan.Status.APPROVED:
                    loan.status = Loan.Status.RETURNED
                    loan.save(update_fields=["status"])
                    loan.book.status = Book.Status.AVAILABLE
                    loan.book.save(update_fields=["status"])
                    messages.success(request, "Le retour du livre a été enregistré.")
                else:
                    messages.error(request, "Cette action n'est pas valide pour le statut actuel.")
            return redirect("dashboard_admin")

    books = Book.objects.select_related("category")
    categories = Category.objects.annotate(book_count=Count("books"))
    libraries = Library.objects.all()
    orders = Order.objects.select_related("customer", "book")[:20]
    loans = Loan.objects.select_related("customer", "book")[:50]
    context = {
        "form": form,
        "category_form": category_form,
        "library_form": library_form,
        "books": books,
        "categories": categories,
        "libraries": libraries,
        "orders": orders,
        "loans": loans,
        "total_books": books.count(),
        "total_categories": categories.count(),
        "total_libraries": libraries.count(),
        "total_orders": Order.objects.count(),
        "total_loans": Loan.objects.count(),
        "pending_loans": Loan.objects.filter(status=Loan.Status.PENDING).count(),
        "available_books": books.filter(status=Book.Status.AVAILABLE).count(),
        "borrowed_books": books.filter(status=Book.Status.BORROWED).count(),
    }
    return render(request, "pages/dashboard_admin.html", context)


def customer_signup(request):
    if request.user.is_authenticated:
        destination = "dashboard_admin" if request.user.is_staff else "mes_commandes"
        return redirect(destination)

    form = CustomerSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        next_url = request.POST.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("livres")

    return render(
        request,
        "pages/customer_signup.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@login_required(login_url="customer_login")
def commander_livre(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    if book.price <= 0:
        messages.error(
            request,
            "Ce livre n'a pas encore de prix. Contactez l'administration.",
        )
        return redirect("livres")

    form = OrderPlacementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = Order.objects.create(
            customer=request.user,
            book=book,
            quantity=form.cleaned_data["quantity"],
            unit_price=book.price,
        )
        messages.info(
            request,
            f"La commande #{order.pk} est enregistrée, mais aucun paiement n'a été effectué. "
            "Le paiement CMI sera disponible après la configuration du compte marchand.",
        )
        return redirect("mes_commandes")

    return render(
        request,
        "pages/confirm_order.html",
        {"book": book, "form": form},
    )


@login_required(login_url="customer_login")
def mes_commandes(request):
    orders = Order.objects.select_related("book").filter(customer=request.user)
    return render(request, "pages/mes_commandes.html", {"orders": orders})


@require_POST
def dashboard_logout(request):
    logout(request)
    return redirect("accueil")


@login_required(login_url="customer_login")
def emprunts(request):
    form = LoanRequestForm(
        request.POST or None,
        initial={"book": request.GET.get("book")},
    )
    if request.method == "POST" and form.is_valid():
        book = form.cleaned_data["book"]
        has_active_request = Loan.objects.filter(
            customer=request.user,
            book=book,
            status__in=[Loan.Status.PENDING, Loan.Status.APPROVED],
        ).exists()
        if has_active_request:
            messages.error(request, "Vous avez déjà une demande active pour ce livre.")
        else:
            Loan.objects.create(customer=request.user, book=book)
            messages.success(
                request,
                "Votre demande d'emprunt a été envoyée à l'administration.",
            )
            return redirect("emprunts")

    loans = Loan.objects.select_related("book").filter(customer=request.user)
    return render(
        request,
        "pages/emprunts.html",
        {
            "form": form,
            "loans": loans,
            "available_books_count": Book.objects.filter(
                status=Book.Status.AVAILABLE
            ).count(),
        },
    )


def contact(request):
    return render(request, "pages/contact.html")