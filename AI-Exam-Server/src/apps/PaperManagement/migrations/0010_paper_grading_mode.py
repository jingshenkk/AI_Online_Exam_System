
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('PaperManagement', '0009_alter_paper_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='paper',
            name='grading_mode',
            field=models.CharField(choices=[('LENIENT', 'Lenient'), ('STRICT', 'Strict')], default='LENIENT', help_text='评分模式', max_length=20),
        ),
    ]
