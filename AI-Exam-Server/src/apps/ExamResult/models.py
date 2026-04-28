# -*- coding: utf-8 -*-
# @File    : models.py
# @Describe: ExamResult应用模型

import uuid

from django.db import models
from django.utils import timezone


class ExamResult(models.Model):
    class Meta:
        db_table = 'exam_result'

    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 考试ID
    exam_id = models.CharField(max_length=255, help_text='考试ID')
    # 学生ID
    student_id = models.CharField(max_length=255, help_text='学生ID')
    # 总得分
    result_mark = models.FloatField(default=0, help_text='学生考试得分')
    # 学生开始考试的时间
    start_time = models.DateTimeField(blank=True, null=True, verbose_name='学生开始考试的时间')
    # 学生结束考试的时间
    end_time = models.DateTimeField(blank=True, null=True, verbose_name='学生结束考试的时间')
    # 结束状态
    ending_status = models.BooleanField(default=True, help_text='是否是正常结束考试')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, null=True, help_text='更新时间')


class ExamResultDetail(models.Model):
    class Meta:
        db_table = 'exam_result_detail'
        
    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 考试结果ID
    exam_result_id = models.CharField(max_length=255, help_text='考试结果ID')
    # 试题ID
    question_id = models.CharField(max_length=255, help_text='试题ID')
    # 试题得分
    mark = models.FloatField(default=0, help_text='试题得分')
    # 学生作答结果
    solution = models.TextField(max_length=5000, blank=True, null=True, help_text='学生作答结果')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')


class AnswerRecord(models.Model):
    """主观题答题记录"""
    class Meta:
        db_table = 'answer_record'
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 关联题目ID
    question_id = models.CharField(max_length=255, help_text='关联题目ID')
    # 学生ID
    student_id = models.CharField(max_length=255, help_text='学生ID')
    # 关联考试结果ID
    exam_result_id = models.CharField(max_length=255, blank=True, null=True, help_text='关联考试结果ID')
    # 学生答案文本
    answer_text = models.TextField(help_text='学生答案文本')
    # 评分模式
    GRADING_MODE_CHOICES = [('LENIENT', 'Lenient'), ('STRICT', 'Strict')]
    grading_mode = models.CharField(max_length=20, choices=GRADING_MODE_CHOICES, help_text='评分模式')
    # 最终得分
    final_score = models.FloatField(null=True, blank=True, help_text='最终得分')
    # 评分状态
    STATUS_CHOICES = [('PENDING', 'Pending'), ('SCORING', 'Scoring'), ('SCORED', 'Scored')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', help_text='评分状态')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, null=True, help_text='更新时间')


class ScorePointDetail(models.Model):
    """逐点评分明细"""
    class Meta:
        db_table = 'score_point_detail'
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 关联答题记录ID
    answer_record_id = models.CharField(max_length=255, help_text='关联答题记录ID')
    # 关联评分细则ID
    scoring_point_id = models.CharField(max_length=255, help_text='关联评分细则ID')
    # LLM-1 评分
    llm_1_hit = models.CharField(max_length=10, null=True, blank=True, help_text='LLM-1命中: FULL/MISS')
    llm_1_score = models.FloatField(null=True, blank=True, help_text='LLM-1该点得分')
    llm_1_reason = models.CharField(max_length=500, null=True, blank=True, help_text='LLM-1判定理由')
    # LLM-2 评分（严格模式）
    llm_2_hit = models.CharField(max_length=10, null=True, blank=True, help_text='LLM-2命中: FULL/MISS')
    llm_2_score = models.FloatField(null=True, blank=True, help_text='LLM-2该点得分')
    llm_2_reason = models.CharField(max_length=500, null=True, blank=True, help_text='LLM-2判定理由')
    # LLM-3 评分（严格模式）
    llm_3_hit = models.CharField(max_length=10, null=True, blank=True, help_text='LLM-3命中: FULL/MISS')
    llm_3_score = models.FloatField(null=True, blank=True, help_text='LLM-3该点得分')
    llm_3_reason = models.CharField(max_length=500, null=True, blank=True, help_text='LLM-3判定理由')
    # 最终结果
    final_hit = models.CharField(max_length=10, null=True, blank=True, help_text='最终命中: FULL/MISS')
    final_score = models.FloatField(null=True, blank=True, help_text='最终该点得分')
    # 投票计数（严格模式）
    vote_count = models.IntegerField(null=True, blank=True, help_text='投票计数')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')


class AnswerDraft(models.Model):
    """答案草稿"""
    class Meta:
        db_table = 'answer_draft'
        unique_together = ('exam_result_id', 'question_id')
    
    id = models.CharField(primary_key=True, default=uuid.uuid4, editable=False, max_length=255)
    # 关联考试结果ID
    exam_result_id = models.CharField(max_length=255, help_text='关联考试结果ID')
    # 关联题目ID
    question_id = models.CharField(max_length=255, help_text='关联题目ID')
    # 草稿答案文本
    answer = models.TextField(blank=True, default='', help_text='草稿答案文本')
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, help_text='创建时间')
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, null=True, help_text='更新时间')


if __name__ == '__main__':
    pass
