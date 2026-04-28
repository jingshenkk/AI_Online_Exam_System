
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('MenuManagement', '0002_menu_parent_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='menu',
            name='id',
            field=models.CharField(default=uuid.uuid4, editable=False, max_length=255, primary_key=True, serialize=False),
        ),
    ]
