from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from .models import Book, Category, Library, Loan, Order


class BookAdminTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Roman")
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username="library-admin",
            email="admin@example.com",
            password="test-password",
        )

    def test_admin_can_add_book_to_public_catalogue(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:pages_book_add"),
            {
                "title": "Le livre de test",
                "author": "Auteur Test",
                "category": self.category.pk,
                "rating": 4,
                "price": "25.00",
                "status": "disponible",
                "_save": "Enregistrer",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le livre de test")
        catalogue_response = self.client.get(reverse("livres"))
        self.assertContains(catalogue_response, "Le livre de test")


class BookDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username="dashboard-admin",
            email="dashboard@example.com",
            password="test-password",
        )

    def test_staff_can_add_book_from_dashboard(self):
        self.client.force_login(self.admin_user)
        category_response = self.client.post(
            reverse("dashboard_admin"),
            {"action": "add_category", "name": "Science-fiction"},
        )

        self.assertRedirects(category_response, reverse("dashboard_admin"))
        category = Category.objects.get(name="Science-fiction")
        response = self.client.post(
            reverse("dashboard_admin"),
            {
                "action": "add_book",
                "title": "Le livre du dashboard",
                "author": "Auteur Dashboard",
                "category": category.pk,
                "rating": 5,
                "price": "42.50",
                "status": "disponible",
            },
        )

        self.assertRedirects(response, reverse("dashboard_admin"))
        self.assertContains(
            self.client.get(reverse("dashboard_admin")),
            "Le livre du dashboard",
        )
        self.assertContains(
            self.client.get(reverse("livres")),
            "Le livre du dashboard",
        )
        self.assertContains(
            self.client.get(reverse("livres")),
            "Science-fiction",
        )

    def test_catalogue_can_filter_by_category(self):
        category = Category.objects.create(name="Histoire")
        other_category = Category.objects.create(name="Poésie")
        Book.objects.create(
            title="Histoire du Maroc",
            author="Auteur A",
            category=category,
        )
        Book.objects.create(
            title="Poèmes du soir",
            author="Auteur B",
            category=other_category,
        )

        response = self.client.get(
            reverse("livres"),
            {"category": category.pk},
        )

        self.assertContains(response, "Histoire du Maroc")
        self.assertNotContains(response, "Poèmes du soir")

    def test_staff_can_add_library_from_dashboard(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("dashboard_admin"),
            {
                "action": "add_library",
                "name": "Bibliothèque Centrale",
                "city": "Casablanca",
                "address": "10 avenue Hassan II",
                "phone": "+212 5 22 00 00 00",
            },
        )

        self.assertRedirects(response, reverse("dashboard_admin"))
        self.assertTrue(Library.objects.filter(name="Bibliothèque Centrale").exists())
        self.assertContains(
            self.client.get(reverse("dashboard_admin")),
            "Bibliothèque Centrale",
        )

    def test_dashboard_redirects_non_staff_users(self):
        reader = get_user_model().objects.create_user(
            username="reader",
            password="test-password",
        )
        self.client.force_login(reader)

        response = self.client.get(reverse("dashboard_admin"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard_login"), response.url)

    def test_dashboard_redirects_guests_to_custom_login(self):
        response = self.client.get(reverse("dashboard_admin"))

        self.assertRedirects(
            response,
            f"{reverse('dashboard_login')}?next={reverse('dashboard_admin')}",
        )

    def test_only_staff_accounts_can_log_in(self):
        reader = get_user_model().objects.create_user(
            username="reader",
            password="test-password",
        )

        response = self.client.post(
            reverse("dashboard_login"),
            {"username": "reader", "password": "test-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tableau de bord")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_staff_account_can_log_in_and_reach_dashboard(self):
        response = self.client.post(
            reverse("dashboard_login"),
            {"username": "dashboard-admin", "password": "test-password"},
        )

        self.assertRedirects(response, reverse("dashboard_admin"))
        self.assertEqual(
            self.client.get(reverse("dashboard_admin")).status_code,
            200,
        )


class CustomerOrderTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Roman")
        self.book = Book.objects.create(
            title="Livre à commander",
            author="Auteur",
            category=self.category,
            price=Decimal("19.50"),
        )

    def test_customer_can_register_and_place_unpaid_order(self):
        order_url = reverse("commander_livre", args=[self.book.pk])
        signup_response = self.client.post(
            reverse("customer_signup") + f"?next={order_url}",
            {
                "username": "lecteur",
                "email": "lecteur@example.com",
                "password1": "StrongPass#2026",
                "password2": "StrongPass#2026",
                "next": order_url,
            },
        )

        self.assertRedirects(signup_response, order_url)
        confirmation_response = self.client.post(order_url, {"quantity": 2})

        self.assertRedirects(confirmation_response, reverse("mes_commandes"))
        order = Order.objects.get(customer__username="lecteur")
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.unit_price, Decimal("19.50"))
        self.assertEqual(order.total_price, Decimal("39.00"))
        self.assertEqual(order.payment_status, Order.PaymentStatus.NOT_CONFIGURED)
        self.assertContains(
            self.client.get(reverse("mes_commandes")),
            "CMI non configuré",
        )

    def test_guest_must_create_an_account_before_ordering(self):
        order_url = reverse("commander_livre", args=[self.book.pk])
        catalogue_response = self.client.get(reverse("livres"))

        self.assertContains(catalogue_response, "Connexion / inscription pour commander")
        order_response = self.client.post(order_url, {"quantity": 1})

        self.assertEqual(order_response.status_code, 302)
        self.assertIn(reverse("customer_login"), order_response.url)
        self.assertFalse(Order.objects.exists())

    def test_order_history_only_shows_current_customer_orders(self):
        customer = get_user_model().objects.create_user(
            username="customer",
            password="StrongPass#2026",
        )
        other_customer = get_user_model().objects.create_user(
            username="other",
            password="StrongPass#2026",
        )
        Order.objects.create(
            customer=customer,
            book=self.book,
            unit_price=self.book.price,
        )
        other_book = Book.objects.create(
            title="Commande privée",
            author="Auteur",
            category=self.category,
            price=Decimal("10.00"),
        )
        Order.objects.create(
            customer=other_customer,
            book=other_book,
            unit_price=other_book.price,
        )
        self.client.force_login(customer)

        response = self.client.get(reverse("mes_commandes"))

        self.assertContains(response, "Livre à commander")
        self.assertNotContains(response, "Commande privée")

    def test_staff_dashboard_displays_customer_orders(self):
        customer = get_user_model().objects.create_user(
            username="buyer",
            password="StrongPass#2026",
        )
        Order.objects.create(
            customer=customer,
            book=self.book,
            unit_price=self.book.price,
        )
        admin_user = get_user_model().objects.create_superuser(
            username="order-admin",
            email="order-admin@example.com",
            password="StrongPass#2026",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("dashboard_admin"))

        self.assertContains(response, "buyer")
        self.assertContains(response, "Livre à commander")


class CustomerLoanTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Roman")
        self.book = Book.objects.create(
            title="Livre à emprunter",
            author="Auteur",
            category=self.category,
        )
        self.reader = get_user_model().objects.create_user(
            username="lecteur-emprunt",
            password="StrongPass#2026",
        )
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin-emprunt",
            email="admin-emprunt@example.com",
            password="StrongPass#2026",
        )

    def test_guest_must_log_in_before_requesting_a_loan(self):
        response = self.client.post(
            reverse("emprunts"),
            {"book": self.book.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("customer_login"), response.url)
        self.assertFalse(Loan.objects.exists())

    def test_reader_request_is_visible_to_admin_and_can_be_approved_and_returned(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            reverse("emprunts"),
            {"book": self.book.pk},
        )

        self.assertRedirects(response, reverse("emprunts"))
        loan = Loan.objects.get(customer=self.reader, book=self.book)
        self.assertEqual(loan.status, Loan.Status.PENDING)
        self.assertEqual(self.book.status, Book.Status.AVAILABLE)

        self.client.force_login(self.admin_user)
        admin_response = self.client.get(reverse("dashboard_admin"))
        self.assertContains(admin_response, "lecteur-emprunt")
        self.assertContains(admin_response, "Livre à emprunter")

        approval_response = self.client.post(
            reverse("dashboard_admin"),
            {"action": "approve_loan", "loan_id": loan.pk},
        )
        self.assertRedirects(approval_response, reverse("dashboard_admin"))
        loan.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.APPROVED)
        self.assertEqual(
            loan.due_date,
            timezone.localdate() + timedelta(days=14),
        )
        self.assertEqual(self.book.status, Book.Status.BORROWED)

        return_response = self.client.post(
            reverse("dashboard_admin"),
            {"action": "return_loan", "loan_id": loan.pk},
        )
        self.assertRedirects(return_response, reverse("dashboard_admin"))
        loan.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.RETURNED)
        self.assertEqual(self.book.status, Book.Status.AVAILABLE)

    def test_admin_can_reject_loan_request_without_changing_availability(self):
        loan = Loan.objects.create(customer=self.reader, book=self.book)
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("dashboard_admin"),
            {"action": "reject_loan", "loan_id": loan.pk},
        )

        self.assertRedirects(response, reverse("dashboard_admin"))
        loan.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.REJECTED)
        self.assertEqual(self.book.status, Book.Status.AVAILABLE)
