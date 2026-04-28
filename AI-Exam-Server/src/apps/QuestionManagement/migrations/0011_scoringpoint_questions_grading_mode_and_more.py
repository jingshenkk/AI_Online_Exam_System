
from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionManagement', '0010_alter_errorarchive_id_alter_questions_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScoringPoint',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, max_length=255, primary_key=True, serialize=False)),
                ('question_id', models.CharField(help_text='关联题目ID', max_length=255)),
                ('description', models.CharField(help_text='得分点描述', max_length=500)),
                ('score', models.FloatField(help_text='该得分点分值')),
                ('acceptable_expressions', models.JSONField(blank=True, default=list, help_text='可接受的同义表达')),
                ('sort_order', models.IntegerField(default=0, help_text='排序序号')),
                ('is_approved', models.BooleanField(default=False, help_text='是否已审核通过')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, help_text='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='更新时间', null=True)),
            ],
            options={
                'db_table': 'scoring_point',
            },
        ),
        migrations.AddField(
            model_name='questions',
            name='grading_mode',
            field=models.CharField(choices=[('LENIENT', 'Lenient'), ('STRICT', 'Strict')], default='LENIENT', help_text='评分模式', max_length=20),
        ),
        migrations.AddField(
            model_name='questions',
            name='max_chars',
            field=models.IntegerField(default=1000, help_text='主观题字数上限'),
        ),
        migrations.AlterField(
            model_name='questions',
            name='answer',
            field=models.TextField(help_text='试题参考答案', max_length=2000),
        ),
        migrations.AlterField(
            model_name='questions',
            name='type',
            field=models.CharField(choices=[('select', 'Select'), ('judge', 'Judge'), ('essay', 'Essay')], default='select', help_text='试题类型', max_length=10),
        ),
    ]
