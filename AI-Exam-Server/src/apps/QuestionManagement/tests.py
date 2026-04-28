from django.test import TestCase
from .models import Questions, ScoringPoint, QuestionsFavorite


class QuestionsModelTest(TestCase):
    """试题模型测试"""

    def setUp(self):
        self.essay_question = Questions.objects.create(
            topic='简述TCP三次握手过程',
            options='',
            answer='客户端发送SYN，服务器回复SYN+ACK，客户端发送ACK',
            type='essay',
            trial_type='public',
            grading_mode='LENIENT',
            created_user='teacher_001',
        )
        self.select_question = Questions.objects.create(
            topic='HTTP默认端口号是？',
            options='A.21|B.80|C.443|D.8080',
            answer='B',
            type='select',
            created_user='teacher_001',
        )

    def test_essay_question_creation(self):
        """测试主观题创建"""
        self.assertEqual(self.essay_question.topic, '简述TCP三次握手过程')
        self.assertEqual(self.essay_question.type, 'essay')
        self.assertEqual(self.essay_question.grading_mode, 'LENIENT')

    def test_select_question_creation(self):
        """测试客观题创建"""
        self.assertEqual(self.select_question.type, 'select')
        self.assertEqual(self.select_question.answer, 'B')

    def test_default_values(self):
        """测试默认值"""
        self.assertTrue(self.essay_question.status)
        self.assertFalse(self.essay_question.is_deleted)
        self.assertEqual(self.essay_question.max_chars, 1000)
        self.assertEqual(self.essay_question.trial_type, 'public')

    def test_question_type_choices(self):
        """测试题目类型选项"""
        judge_question = Questions.objects.create(
            topic='TCP是面向连接的协议',
            options='T&F',
            answer='T',
            type='judge',
            created_user='teacher_001',
        )
        self.assertEqual(judge_question.type, 'judge')

    def test_grading_mode_choices(self):
        """测试评分模式选项"""
        strict_question = Questions.objects.create(
            topic='解释进程和线程的区别',
            options='',
            answer='进程是资源分配的基本单位，线程是CPU调度的基本单位',
            type='essay',
            grading_mode='STRICT',
            created_user='teacher_001',
        )
        self.assertEqual(strict_question.grading_mode, 'STRICT')


class ScoringPointModelTest(TestCase):
    """评分细则模型测试"""

    def setUp(self):
        self.question = Questions.objects.create(
            topic='简述TCP三次握手过程',
            options='',
            answer='建立可靠连接，同步序列号',
            type='essay',
            created_user='teacher_001',
        )
        self.scoring_point = ScoringPoint.objects.create(
            question_id=str(self.question.id),
            description='正确说明三次握手的目的：建立可靠连接',
            score=3.0,
            acceptable_expressions=['建立可靠连接', '确保连接可靠', '建立可靠通道'],
            sort_order=1,
            is_approved=True,
        )

    def test_scoring_point_creation(self):
        """测试评分细则创建"""
        self.assertEqual(self.scoring_point.description, '正确说明三次握手的目的：建立可靠连接')
        self.assertEqual(self.scoring_point.score, 3.0)
        self.assertEqual(self.scoring_point.question_id, str(self.question.id))

    def test_acceptable_expressions_json(self):
        """测试同义表达JSON字段"""
        expressions = self.scoring_point.acceptable_expressions
        self.assertIsInstance(expressions, list)
        self.assertEqual(len(expressions), 3)
        self.assertIn('建立可靠连接', expressions)

    def test_scoring_point_approval(self):
        """测试评分细则审核状态"""
        self.assertTrue(self.scoring_point.is_approved)

        unapproved_point = ScoringPoint.objects.create(
            question_id=str(self.question.id),
            description='正确描述第一次握手',
            score=2.0,
            sort_order=2,
        )
        self.assertFalse(unapproved_point.is_approved)

    def test_filter_approved_points(self):
        """测试按审核状态过滤评分细则"""
        ScoringPoint.objects.create(
            question_id=str(self.question.id),
            description='未审核的得分点',
            score=2.0,
            sort_order=2,
            is_approved=False,
        )
        approved_points = ScoringPoint.objects.filter(
            question_id=str(self.question.id),
            is_approved=True,
        )
        self.assertEqual(approved_points.count(), 1)

    def test_scoring_points_total_score(self):
        """测试多个评分细则分值汇总"""
        ScoringPoint.objects.create(
            question_id=str(self.question.id),
            description='正确描述第一次握手',
            score=2.0,
            sort_order=2,
            is_approved=True,
        )
        ScoringPoint.objects.create(
            question_id=str(self.question.id),
            description='正确描述第二次握手',
            score=2.5,
            sort_order=3,
            is_approved=True,
        )
        total = sum(
            p.score for p in ScoringPoint.objects.filter(
                question_id=str(self.question.id),
                is_approved=True,
            )
        )
        self.assertEqual(total, 7.5)


class QuestionsFavoriteModelTest(TestCase):
    """试题收藏模型测试"""

    def setUp(self):
        self.question = Questions.objects.create(
            topic='测试题目',
            options='',
            answer='测试答案',
            type='essay',
            created_user='teacher_001',
        )

    def test_favorite_creation(self):
        """测试收藏创建"""
        favorite = QuestionsFavorite.objects.create(
            question_id=str(self.question.id),
            collector='teacher_001',
        )
        self.assertEqual(favorite.question_id, str(self.question.id))
        self.assertEqual(favorite.collector, 'teacher_001')
