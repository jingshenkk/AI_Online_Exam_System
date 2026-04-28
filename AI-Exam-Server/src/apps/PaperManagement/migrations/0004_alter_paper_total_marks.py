
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('PaperManagement', '0003_papermodule'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paper',
            name='total_marks',
            field=models.PositiveIntegerField(default=0, help_text='总分数'),
        ),
    ]
