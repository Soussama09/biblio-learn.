from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import Book, Category, Library


class DashboardAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "current-password"}
        )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError("Ce compte n'a pas accès au tableau de bord.")


class BookForm(forms.ModelForm):
    price = forms.DecimalField(
        label="Prix (MAD)",
        min_value=Decimal("0.01"),
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "0.01", "step": "0.01"}
        ),
    )

    class Meta:
        model = Book
        fields = ("title", "author", "category", "rating", "price", "status")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Titre du livre"}),
            "author": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom de l'auteur"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "rating": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ex. Roman, Histoire..."}
            ),
        }


class LibraryForm(forms.ModelForm):
    class Meta:
        model = Library
        fields = ("name", "city", "address", "phone")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom de la bibliothèque"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ville"}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Adresse complète"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Téléphone (facultatif)"}),
        }


class CustomerAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "current-password"}
        )


class CustomerSignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "autocomplete": "email"}
        ),
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username"}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "new-password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "new-password"}
        )


class OrderPlacementForm(forms.Form):
    quantity = forms.IntegerField(
        label="Quantité",
        min_value=1,
        max_value=20,
        initial=1,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": 1, "max": 20}
        ),
    )


class LoanRequestForm(forms.Form):
    book = forms.ModelChoiceField(
        label="Livre à emprunter",
        queryset=Book.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["book"].queryset = Book.objects.filter(
            status=Book.Status.AVAILABLE
        ).order_by("title")
