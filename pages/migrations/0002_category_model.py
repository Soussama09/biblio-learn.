from django.db import migrations, models
import django.db.models.deletion


def create_categories_from_existing_books(apps, schema_editor):
    database = schema_editor.connection.alias
    Book = apps.get_model("pages", "Book")
    Category = apps.get_model("pages", "Category")

    for book in Book.objects.using(database).all().iterator():
        name = book.category_name.strip() or "Autres"
        category, _ = Category.objects.using(database).get_or_create(name=name)
        book.category_id = category.pk
        book.save(using=database, update_fields=["category"])


def restore_existing_category_names(apps, schema_editor):
    database = schema_editor.connection.alias
    Book = apps.get_model("pages", "Book")

    for book in Book.objects.using(database).select_related("category").iterator():
        book.category_name = book.category.name
        book.save(using=database, update_fields=["category_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="nom")),
            ],
            options={
                "verbose_name": "catégorie",
                "verbose_name_plural": "catégories",
                "ordering": ["name"],
            },
        ),
        migrations.RenameField(
            model_name="book",
            old_name="category",
            new_name="category_name",
        ),
        migrations.AlterField(
            model_name="book",
            name="category_name",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                verbose_name="ancienne catégorie",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="books",
                to="pages.category",
                verbose_name="catégorie",
            ),
        ),
        migrations.RunPython(
            create_categories_from_existing_books,
            restore_existing_category_names,
        ),
        migrations.AlterField(
            model_name="book",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="books",
                to="pages.category",
                verbose_name="catégorie",
            ),
        ),
        migrations.RemoveField(
            model_name="book",
            name="category_name",
        ),
    ]
