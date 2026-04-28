# @File    : models.py
# @Describe: Questions应用模型 


import uuid
from django.db import models
from django.utils import timezone


class Questions(models.Model):
    class Meta:
        db_table = 'questions'
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 试题标题
    topic = models.TextField(max_length=500, help_text='试题标题')
    # 试题选项
    options = models.TextField(default='T&F', max_length=500, help_text='试题选项')
    # 试题答案（客观题为标准答案，主观题为参考答案）
    answer = models.TextField(max_length=2000, help_text='试题参考答案')
    # 试题类型
    TYPE_CHOICES = [('select', 'Select'), ('judge', 'Judge'), ('essay', 'Essay')]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='select', help_text='试题类型')
    # 试库类型
    TRIAL_TYPE_CHOICES = [('public', 'Public'),('private', 'Private')]
    trial_type = models.CharField(max_length=10, choices=TRIAL_TYPE_CHOICES, default='private', help_text='所属题库类型')
    # 主观题字数上限（默认1000）
    max_chars = models.IntegerField(default=1000, help_text='主观题字数上限')
    # 评分模式：LENIENT(宽松-单LLM) / STRICT(严格-三LLM投票)
    GRADING_MODE_CHOICES = [('LENIENT', 'Lenient'), ('STRICT', 'Strict')]
    grading_mode = models.CharField(max_length=20, choices=GRADING_MODE_CHOICES, default='LENIENT', help_text='评分模式')
    # 试题状态
    status = models.BooleanField(default=True, help_text='试题状态')
    # 试题是否被删除
    is_deleted = models.BooleanField(default=False, help_text='是否删除')
    # 创建人
    created_user = models.CharField(max_length=255, help_text='创建人')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')
    # 更新人
    updated_user = models.CharField(max_length=255, null=True, help_text='更新人')
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, null=True, help_text='更新时间')


class ScoringPoint(models.Model):
    """评分细则/得分点"""
    class Meta:
        db_table = 'scoring_point'
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 关联题目ID
    question_id = models.CharField(max_length=255, help_text='关联题目ID')
    # 得分点描述
    description = models.CharField(max_length=500, help_text='得分点描述')
    # 该得分点分值
    score = models.FloatField(help_text='该得分点分值')
    # 可接受的同义表达（JSON数组）
    acceptable_expressions = models.JSONField(default=list, blank=True, help_text='可接受的同义表达')
    # 排序序号
    sort_order = models.IntegerField(default=0, help_text='排序序号')
    # 是否已审核通过
    is_approved = models.BooleanField(default=False, help_text='是否已审核通过')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, null=True, help_text='更新时间')


class QuestionsFavorite(models.Model):
    class Meta:
        db_table = 'questions_favorite'
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 试题ID
    question_id = models.CharField(max_length=255, help_text='试题ID')
    # 收藏者ID
    collector = models.CharField(max_length=255, help_text='收藏者ID')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')




if __name__ == '__main__':
    pass
