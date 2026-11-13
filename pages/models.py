from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Category(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"

    def __str__(self):
        return self.name


class Library(models.Model):
    name = models.CharField("nom", max_length=150, unique=True)
    city = models.CharField("ville", max_length=100)
    address = models.CharField("adresse", max_length=255)
    phone = models.CharField("téléphone", max_length=30, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "bibliothèque"
        verbose_name_plural = "bibliothèques"

    def __str__(self):
        return f"{self.name} — {self.city}"


class Book(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "disponible", "Disponible"
        RESERVED = "reserve", "Réservé"
        BORROWED = "emprunte", "Emprunté"

    title = models.CharField("titre", max_length=200)
    author = models.CharField("auteur", max_length=150)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="books",
        verbose_name="catégorie",
    )
    rating = models.PositiveSmallIntegerField(
        "note",
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    price = models.DecimalField(
        "prix (MAD)",
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        "statut",
        max_length=12,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    class Meta:
        ordering = ["title"]
        verbose_name = "livre"
        verbose_name_plural = "livres"

    def __str__(self):
        return self.title


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PROCESSING = "processing", "En préparation"
        COMPLETED = "completed", "Terminée"
        CANCELLED = "cancelled", "Annulée"

    class PaymentStatus(models.TextChoices):
        NOT_CONFIGURED = "not_configured", "CMI non configuré"
        PENDING = "pending", "En attente"
        PAID = "paid", "Payé"
        FAILED = "failed", "Échec"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="book_orders",
        verbose_name="client",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="livre",
    )
    quantity = models.PositiveSmallIntegerField(
        "quantité",
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    unit_price = models.DecimalField(
        "prix unitaire (MAD)",
        max_digits=8,
        decimal_places=2,
    )
    status = models.CharField(
        "statut",
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_status = models.CharField(
        "paiement",
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_CONFIGURED,
    )
    created_at = models.DateTimeField("date de commande", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "commande"
        verbose_name_plural = "commandes"

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"Commande #{self.pk} — {self.book.title}"


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Accepté"
        REJECTED = "rejected", "Refusé"
        RETURNED = "returned", "Retourné"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="book_loans",
        verbose_name="lecteur",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="loans",
        verbose_name="livre",
    )
    status = models.CharField(
        "statut",
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    requested_at = models.DateTimeField("date de demande", auto_now_add=True)
    due_date = models.DateField("date de retour prévue", null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "demande d'emprunt"
        verbose_name_plural = "demandes d'emprunt"

    def approve(self):
        self.status = self.Status.APPROVED
        self.due_date = timezone.localdate() + timedelta(days=14)

    def __str__(self):
        return f"Emprunt #{self.pk} — {self.book.title}"
