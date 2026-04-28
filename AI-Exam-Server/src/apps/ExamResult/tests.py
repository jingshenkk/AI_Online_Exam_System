from unittest.mock import patch, MagicMock
from django.test import TestCase
from .models import ExamResult, ExamResultDetail, AnswerRecord, ScorePointDetail, AnswerDraft
from src.apps.QuestionManagement.models import Questions, ScoringPoint


class ExamResultModelTest(TestCase):
    """考试结果模型测试"""

    def test_exam_result_creation(self):
        """测试考试结果创建"""
        result = ExamResult.objects.create(
            exam_id='exam_001',
            student_id='student_001',
            result_mark=85.5,
        )
        self.assertEqual(result.exam_id, 'exam_001')
        self.assertEqual(result.student_id, 'student_001')
        self.assertEqual(result.result_mark, 85.5)
        self.assertTrue(result.ending_status)

    def test_exam_result_default_mark(self):
        """测试默认分数为0"""
        result = ExamResult.objects.create(
            exam_id='exam_002',
            student_id='student_002',
        )
        self.assertEqual(result.result_mark, 0)

    def test_exam_result_detail_creation(self):
        """测试考试结果明细创建"""
        detail = ExamResultDetail.objects.create(
            exam_result_id='result_001',
            question_id='question_001',
            mark=8.0,
            solution='TCP三次握手是建立可靠连接的过程',
        )
        self.assertEqual(detail.mark, 8.0)
        self.assertEqual(detail.question_id, 'question_001')


class AnswerRecordModelTest(TestCase):
    """答题记录模型测试"""

    def test_answer_record_creation(self):
        """测试答题记录创建"""
        record = AnswerRecord.objects.create(
            question_id='q_001',
            student_id='s_001',
            answer_text='TCP通过三次握手建立连接',
            grading_mode='LENIENT',
        )
        self.assertEqual(record.status, 'PENDING')
        self.assertIsNone(record.final_score)
        self.assertEqual(record.grading_mode, 'LENIENT')

    def test_answer_record_status_transition(self):
        """测试答题记录状态流转"""
        record = AnswerRecord.objects.create(
            question_id='q_001',
            student_id='s_001',
            answer_text='测试答案',
            grading_mode='STRICT',
        )
        self.assertEqual(record.status, 'PENDING')

        record.status = 'SCORING'
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.status, 'SCORING')

        record.status = 'SCORED'
        record.final_score = 7.5
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.status, 'SCORED')
        self.assertEqual(record.final_score, 7.5)


class ScorePointDetailModelTest(TestCase):
    """逐点评分明细模型测试"""

    def test_lenient_mode_detail(self):
        """测试宽松模式评分明细（只有llm_1）"""
        detail = ScorePointDetail.objects.create(
            answer_record_id='record_001',
            scoring_point_id='point_001',
            llm_1_hit='FULL',
            llm_1_score=3.0,
            llm_1_reason='学生正确描述了三次握手的目的',
            final_hit='FULL',
            final_score=3.0,
            vote_count=1,
        )
        self.assertEqual(detail.final_hit, 'FULL')
        self.assertEqual(detail.final_score, 3.0)
        self.assertIsNone(detail.llm_2_hit)
        self.assertIsNone(detail.llm_3_hit)

    def test_strict_mode_detail(self):
        """测试严格模式评分明细（三个LLM投票）"""
        detail = ScorePointDetail.objects.create(
            answer_record_id='record_002',
            scoring_point_id='point_001',
            llm_1_hit='FULL',
            llm_1_score=3.0,
            llm_1_reason='命中',
            llm_2_hit='FULL',
            llm_2_score=3.0,
            llm_2_reason='命中',
            llm_3_hit='MISS',
            llm_3_score=0.0,
            llm_3_reason='未命中',
            final_hit='FULL',
            final_score=3.0,
            vote_count=2,
        )
        self.assertEqual(detail.final_hit, 'FULL')
        self.assertEqual(detail.vote_count, 2)


class AnswerDraftModelTest(TestCase):
    """答案草稿模型测试"""

    def test_draft_creation(self):
        """测试草稿创建"""
        draft = AnswerDraft.objects.create(
            exam_result_id='result_001',
            question_id='q_001',
            answer='这是一个草稿答案',
        )
        self.assertEqual(draft.answer, '这是一个草稿答案')

    def test_draft_unique_constraint(self):
        """测试草稿唯一约束（同一考试结果+同一题目只能有一个草稿）"""
        AnswerDraft.objects.create(
            exam_result_id='result_001',
            question_id='q_001',
            answer='第一次草稿',
        )
        with self.assertRaises(Exception):
            AnswerDraft.objects.create(
                exam_result_id='result_001',
                question_id='q_001',
                answer='重复草稿',
            )


class StrictGradingVoteTest(TestCase):
    """严格模式投票逻辑测试（核心算法）"""

    def setUp(self):
        from src.services.grading_service import StrictGradingService
        self.service = StrictGradingService()

        # 创建一个模拟的 ScoringPoint 对象
        self.mock_point = MagicMock()
        self.mock_point.score = 3.0

    def test_vote_all_full(self):
        """测试三票全部FULL"""
        votes = [
            {'hit': 'FULL', 'earned': 3.0, 'reason': '正确'},
            {'hit': 'FULL', 'earned': 3.0, 'reason': '正确'},
            {'hit': 'FULL', 'earned': 3.0, 'reason': '正确'},
        ]
        final_hit, final_score, vote_count = self.service._vote(votes, self.mock_point)
        self.assertEqual(final_hit, 'FULL')
        self.assertEqual(final_score, 3.0)
        self.assertEqual(vote_count, 3)

    def test_vote_all_miss(self):
        """测试三票全部MISS"""
        votes = [
            {'hit': 'MISS', 'earned': 0.0, 'reason': '错误'},
            {'hit': 'MISS', 'earned': 0.0, 'reason': '错误'},
            {'hit': 'MISS', 'earned': 0.0, 'reason': '错误'},
        ]
        final_hit, final_score, vote_count = self.service._vote(votes, self.mock_point)
        self.assertEqual(final_hit, 'MISS')
        self.assertEqual(final_score, 0.0)
        self.assertEqual(vote_count, 3)

    def test_vote_two_full_one_miss(self):
        """测试两票FULL一票MISS（多数票FULL）"""
        votes = [
            {'hit': 'FULL', 'earned': 3.0, 'reason': '正确'},
            {'hit': 'FULL', 'earned': 3.0, 'reason': '正确'},
            {'hit': 'MISS', 'earned': 0.0, 'reason': '错误'},
        ]
        final_hit, final_score, vote_count = self.service._vote(votes, self.mock_point)
        self.assertEqual(final_hit, 'FULL')
        self.assertEqual(final_score, 3.0)
        self.assertEqual(vote_count, 2)

    def test_vote_one_full_two_miss(self):
        """测试一票FULL两票MISS（多数票MISS）"""
        votes = [
            {'hit': 'FULL', 'earned': 3.0, 'reason': '正确'},
            {'hit': 'MISS', 'earned': 0.0, 'reason': '错误'},
            {'hit': 'MISS', 'earned': 0.0, 'reason': '错误'},
        ]
        final_hit, final_score, vote_count = self.service._vote(votes, self.mock_point)
        self.assertEqual(final_hit, 'MISS')
        self.assertEqual(final_score, 0.0)
        self.assertEqual(vote_count, 2)

    def test_vote_score_rounding(self):
        """测试投票结果的分数精度"""
        self.mock_point.score = 2.5
        votes = [
            {'hit': 'FULL', 'earned': 2.5, 'reason': '正确'},
            {'hit': 'FULL', 'earned': 2.5, 'reason': '正确'},
            {'hit': 'MISS', 'earned': 0.0, 'reason': '错误'},
        ]
        final_hit, final_score, vote_count = self.service._vote(votes, self.mock_point)
        self.assertEqual(final_score, 2.5)


class GradingOrchestratorTest(TestCase):
    """评分编排器测试"""

    def setUp(self):
        self.question = Questions.objects.create(
            topic='简述TCP三次握手',
            options='',
            answer='建立可靠连接',
            type='essay',
            created_user='teacher_001',
        )
        ScoringPoint.objects.create(
            question_id=str(self.question.id),
            description='正确说明目的',
            score=5.0,
            sort_order=1,
            is_approved=True,
        )
        ScoringPoint.objects.create(
            question_id=str(self.question.id),
            description='正确描述过程',
            score=5.0,
            sort_order=2,
            is_approved=True,
        )

    @patch('src.services.grading_service.LLMService')
    def test_lenient_grading(self, mock_llm_class):
        """测试宽松模式评分流程（mock LLM调用）"""
        mock_llm_instance = mock_llm_class.return_value
        points = list(ScoringPoint.objects.filter(
            question_id=str(self.question.id), is_approved=True
        ))
        mock_llm_instance.score_answer.return_value = {
            'point_scores': [
                {'point_id': str(points[0].id), 'hit': 'FULL', 'earned': 5.0, 'reason': '正确'},
                {'point_id': str(points[1].id), 'hit': 'MISS', 'earned': 0.0, 'reason': '未提及'},
            ],
            'total': 5.0,
        }

        record = AnswerRecord.objects.create(
            question_id=str(self.question.id),
            student_id='student_001',
            answer_text='TCP三次握手的目的是建立可靠连接',
            grading_mode='LENIENT',
        )

        from src.services.grading_service import GradingOrchestrator
        orchestrator = GradingOrchestrator()
        scored_record = orchestrator.score_answer(str(record.id))

        self.assertEqual(scored_record.status, 'SCORED')
        self.assertEqual(scored_record.final_score, 5.0)

        details = ScorePointDetail.objects.filter(answer_record_id=str(record.id))
        self.assertEqual(details.count(), 2)

    @patch('src.services.grading_service.LLMService')
    def test_strict_grading(self, mock_llm_class):
        """测试严格模式评分流程（mock LLM调用，三次投票）"""
        mock_llm_instance = mock_llm_class.return_value
        points = list(ScoringPoint.objects.filter(
            question_id=str(self.question.id), is_approved=True
        ))

        # 模拟三次LLM调用返回不同结果
        mock_llm_instance.score_answer.side_effect = [
            {
                'point_scores': [
                    {'point_id': str(points[0].id), 'hit': 'FULL', 'earned': 5.0, 'reason': '正确'},
                    {'point_id': str(points[1].id), 'hit': 'FULL', 'earned': 5.0, 'reason': '正确'},
                ],
                'total': 10.0,
            },
            {
                'point_scores': [
                    {'point_id': str(points[0].id), 'hit': 'FULL', 'earned': 5.0, 'reason': '正确'},
                    {'point_id': str(points[1].id), 'hit': 'MISS', 'earned': 0.0, 'reason': '不够准确'},
                ],
                'total': 5.0,
            },
            {
                'point_scores': [
                    {'point_id': str(points[0].id), 'hit': 'FULL', 'earned': 5.0, 'reason': '正确'},
                    {'point_id': str(points[1].id), 'hit': 'MISS', 'earned': 0.0, 'reason': '缺失'},
                ],
                'total': 5.0,
            },
        ]

        record = AnswerRecord.objects.create(
            question_id=str(self.question.id),
            student_id='student_001',
            answer_text='TCP三次握手的目的是建立可靠连接',
            grading_mode='STRICT',
        )

        from src.services.grading_service import GradingOrchestrator
        orchestrator = GradingOrchestrator()
        scored_record = orchestrator.score_answer(str(record.id))

        self.assertEqual(scored_record.status, 'SCORED')
        # 得分点1: 3票FULL → FULL(5分)，得分点2: 1票FULL+2票MISS → MISS(0分)
        self.assertEqual(scored_record.final_score, 5.0)

        details = ScorePointDetail.objects.filter(answer_record_id=str(record.id))
        self.assertEqual(details.count(), 2)

        # 验证得分点1的投票结果
        point1_detail = details.get(scoring_point_id=str(points[0].id))
        self.assertEqual(point1_detail.final_hit, 'FULL')
        self.assertEqual(point1_detail.vote_count, 3)

        # 验证得分点2的投票结果
        point2_detail = details.get(scoring_point_id=str(points[1].id))
        self.assertEqual(point2_detail.final_hit, 'MISS')
        self.assertEqual(point2_detail.vote_count, 2)
