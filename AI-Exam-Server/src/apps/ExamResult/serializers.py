# -*- coding: utf-8 -*-
# @File    : serializers.py
# @Describe: ExamResult应用-序列化

from rest_framework import serializers

from .models import ExamResult, ExamResultDetail, AnswerRecord, ScorePointDetail, AnswerDraft
from ..UserManagement.models import Student
from ..ExamManagement.models import Exam
from ..QuestionManagement.models import Questions, ScoringPoint


class ExamResultSerializer(serializers.ModelSerializer):
    student_info = serializers.SerializerMethodField()
    exam_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamResult
        fields = '__all__'
        # 添加额外的字段
        extra_field = ['student_info']
        # 格式化日期时间
        extra_kwargs = {
            'created_at': { 'format': '%Y-%m-%d %H:%M:%S' },
            'updated_at': { 'format': '%Y-%m-%d %H:%M:%S' },
            'start_time': { 'format': '%Y-%m-%d %H:%M:%S' },
            'end_time': { 'format': '%Y-%m-%d %H:%M:%S' },
        }

    # 获取学生信息
    def get_student_info(self, obj):
        student_instance = Student.objects.filter(id=obj.student_id).first()
        if student_instance:
            return {
                'id': student_instance.id,
                'name': student_instance.name, 
                'student_id': student_instance.student_id
                # 可以再加需要的数据
            }
        else:
            return None
    
    # 获取考试信息
    def get_exam_info(self, obj):
        exam_instance = Exam.objects.filter(id=obj.exam_id).first()
        if exam_instance:
            return {
                'id': exam_instance.id,
                'title': exam_instance.title,
                'paper_id': exam_instance.paper_id
                # 可以再加需要的数据
            }
        else:
            return None


class ExamResultDetailSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ExamResultDetail
        fields = '__all__'
        # 格式化日期时间
        extra_kwargs = {
            'created_at': { 'format': '%Y-%m-%d %H:%M:%S' },
        } 

class AnswerRecordSerializer(serializers.ModelSerializer):
    student_info = serializers.SerializerMethodField()
    question_info = serializers.SerializerMethodField()
    point_details = serializers.SerializerMethodField()
    
    class Meta:
        model = AnswerRecord
        fields = '__all__'
        extra_field = ['student_info', 'question_info', 'point_details']
        extra_kwargs = {
            'created_at': { 'format': '%Y-%m-%d %H:%M:%S' },
            'updated_at': { 'format': '%Y-%m-%d %H:%M:%S' },
        }
    
    def get_student_info(self, obj):
        student_instance = Student.objects.filter(id=obj.student_id).first()
        if student_instance:
            return {
                'id': student_instance.id,
                'name': student_instance.name,
                'student_id': student_instance.student_id
            }
        return None
    
    def get_question_info(self, obj):
        question = Questions.objects.filter(id=obj.question_id).first()
        if question:
            return {
                'id': question.id,
                'topic': question.topic,
                'type': question.type,
                'total_score': question.answer,
                'grading_mode': question.grading_mode
            }
        return None
    
    def get_point_details(self, obj):
        details = ScorePointDetail.objects.filter(answer_record_id=obj.id)
        return ScorePointDetailSerializer(details, many=True).data

class ScorePointDetailSerializer(serializers.ModelSerializer):
    scoring_point_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ScorePointDetail
        fields = '__all__'
        extra_field = ['scoring_point_info']
        extra_kwargs = {
            'created_at': { 'format': '%Y-%m-%d %H:%M:%S' },
        }
    
    def get_scoring_point_info(self, obj):
        point = ScoringPoint.objects.filter(id=obj.scoring_point_id).first()
        if point:
            return {
                'id': point.id,
                'description': point.description,
                'score': point.score,
                'acceptable_expressions': point.acceptable_expressions
            }
        return None

class AnswerDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerDraft
        fields = '__all__'
        extra_kwargs = {
            'created_at': { 'format': '%Y-%m-%d %H:%M:%S' },
            'updated_at': { 'format': '%Y-%m-%d %H:%M:%S' },
        }

if __name__ == '__main__':
    pass