
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionManagement', '0006_questions_options_alter_questions_answer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='errorarchive',
            name='difficulty',
            field=models.CharField(choices=[('E', 'Easy'), ('M', 'Medium'), ('H', 'Hard')], default='M', help_text='错题难度', max_length=10),
        ),
    ]
