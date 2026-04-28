
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionManagement', '0005_errorarchive'),
    ]

    operations = [
        migrations.AddField(
            model_name='questions',
            name='options',
            field=models.TextField(default='T&F', help_text='试题选项', max_length=500),
        ),
        migrations.AlterField(
            model_name='questions',
            name='answer',
            field=models.CharField(help_text='试题参考答案', max_length=50),
        ),
    ]
