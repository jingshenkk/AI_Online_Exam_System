# @File    : urls.py
# @Describe: Question应用URL 

from django.urls import path

from .views import QuestionBaseView
from .views import QuestionFavoriteView
from .views import QuestionsWarehouseForPaper
from .views import UploadFileForQuestionsView
from .views import RandomSelectQuestionsView
from .views import ScoringPointView, ScoringPointDetailView, ScoringPointApproveView, ScoringPointBatchApproveView
from .views import RubricGenerateView

urlpatterns = [
    path('question', QuestionBaseView.as_view(), name='QuestionsOpts'),
    path('question/<str:id>', QuestionBaseView.as_view(), name='QuestionsOpts'),
    path('qFavorite', QuestionFavoriteView.as_view(), name='QuestionsFavoriteOpts'),
    path('qFavorite/<str:id>', QuestionFavoriteView.as_view(), name='QuestionsFavoriteOpts'),
    path('questionWarehouse', QuestionsWarehouseForPaper.as_view(), name='QuestionWarehouseOpts'),
    path('uploadFileForQuestions', UploadFileForQuestionsView.as_view(), name='UploadFileForQuestionsOpts'),
    path('randomSelectQuestions', RandomSelectQuestionsView.as_view(), name='RandomSelectQuestionsOpts'),
    path('scoringPoints/<str:question_id>', ScoringPointView.as_view(), name='ScoringPointOpts'),
    path('scoringPoints', ScoringPointView.as_view(), name='ScoringPointCreate'),
    path('scoringPoint/<str:id>', ScoringPointDetailView.as_view(), name='ScoringPointDetailOpts'),
    path('scoringPoint/<str:id>/approve', ScoringPointApproveView.as_view(), name='ScoringPointApprove'),
    path('scoringPointBatchApprove', ScoringPointBatchApproveView.as_view(), name='ScoringPointBatchApprove'),
    path('rubricGenerate/<str:question_id>', RubricGenerateView.as_view(), name='RubricGenerate'),
]


if __name__ == '__main__':
    pass