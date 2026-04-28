
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionManagement', '0002_questions_trial_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='questions',
            name='is_deleted',
            field=models.BooleanField(default=False, help_text='是否删除'),
        ),
    ]
