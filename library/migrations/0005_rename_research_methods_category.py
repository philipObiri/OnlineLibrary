from django.db import migrations


def rename_category(apps, schema_editor):
    Category = apps.get_model('library', 'Category')
    Category.objects.filter(name='Research Methods & Methodology').update(
        name='Research Methods',
        slug='research-methods',
    )


def reverse_rename_category(apps, schema_editor):
    Category = apps.get_model('library', 'Category')
    Category.objects.filter(name='Research Methods').update(
        name='Research Methods & Methodology',
        slug='research-methods-methodology',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0004_add_performance_indexes'),
    ]

    operations = [
        migrations.RunPython(rename_category, reverse_code=reverse_rename_category),
    ]
