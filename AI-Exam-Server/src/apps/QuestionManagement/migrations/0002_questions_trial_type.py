
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionManagement', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='questions',
            name='trial_type',
            field=models.CharField(choices=[('public', 'Public'), ('private', 'Private')], default='select', help_text='所属题库类型', max_length=10),
        ),
    ]
