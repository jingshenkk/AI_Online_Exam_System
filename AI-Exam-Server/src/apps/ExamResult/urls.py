# -*- coding: utf-8 -*-
# @File    : urls.py
# @Describe: ExamResult应用URL

from django.urls import path

from .views import ExamResultBaseView
from .views import ExamResultDetailBaseView
from .views import ExamOnlineGetResultView
from .views import ExamResultStudentView
from .views import GenerateExamResultExcel
from .views import AnswerRecordView, AnswerDraftView, AdjustScoreView

urlpatterns = [
    path('examResult', ExamResultBaseView.as_view(), name='ExamResultOpts'),
    path('examResult/<str:id>', ExamResultBaseView.as_view(), name='ExamResultOpts'),
    path('examResultDetail', ExamResultDetailBaseView.as_view(), name='ExamResultDetailOpts'),
    path('examResultDetail/<str:id>', ExamResultDetailBaseView.as_view(), name='ExamResultDetailOpts'),
    path('examOnlineGetResult', ExamOnlineGetResultView.as_view(), name='ExamOnlineGetResultOpts'),
    path('examResultStu', ExamResultStudentView.as_view(), name='ExamResultStudentOpts'),
    path('generateExamResultExcel', GenerateExamResultExcel.as_view(), name='GenerateExamResultExcel'),
    path('answerRecord', AnswerRecordView.as_view(), name='AnswerRecordOpts'),
    path('answerRecord/<str:id>', AnswerRecordView.as_view(), name='AnswerRecordDetail'),
    path('answerDraft', AnswerDraftView.as_view(), name='AnswerDraftOpts'),
    path('adjustScore/<str:id>', AdjustScoreView.as_view(), name='AdjustScoreOpts'),
]
