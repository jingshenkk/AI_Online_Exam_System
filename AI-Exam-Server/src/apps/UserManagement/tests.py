from django.test import TestCase, Client
from .models import Student, Teacher


class StudentModelTest(TestCase):
    """学生模型测试"""

    def setUp(self):
        self.student = Student.objects.create(
            username='test_student',
            password='123456',
            name='张三',
            role='student',
            gender='male',
            student_id='2024001',
            grade='2024',
            is_active=True,
            is_deleted=False,
        )

    def test_student_creation(self):
        """测试学生模型创建"""
        self.assertEqual(self.student.username, 'test_student')
        self.assertEqual(self.student.name, '张三')
        self.assertEqual(self.student.student_id, '2024001')
        self.assertEqual(self.student.role, 'student')

    def test_student_str(self):
        """测试学生模型字符串表示"""
        self.assertEqual(str(self.student), 'Student: test_student')

    def test_student_is_authenticated(self):
        """测试学生认证属性"""
        self.assertTrue(self.student.is_authenticated)

    def test_student_default_values(self):
        """测试学生模型默认值"""
        self.assertTrue(self.student.is_active)
        self.assertFalse(self.student.is_deleted)

    def test_student_id_unique(self):
        """测试学号唯一性约束"""
        with self.assertRaises(Exception):
            Student.objects.create(
                username='another_student',
                password='123456',
                name='李四',
                student_id='2024001',  # 重复学号
            )

    def test_username_unique(self):
        """测试用户名唯一性约束"""
        with self.assertRaises(Exception):
            Student.objects.create(
                username='test_student',  # 重复用户名
                password='123456',
                name='王五',
                student_id='2024002',
            )


class TeacherModelTest(TestCase):
    """教师模型测试"""

    def setUp(self):
        self.teacher = Teacher.objects.create(
            username='test_teacher',
            password='123456',
            name='李老师',
            role='teacher',
            gender='female',
            teacher_id='T001',
            is_active=True,
            is_deleted=False,
        )

    def test_teacher_creation(self):
        """测试教师模型创建"""
        self.assertEqual(self.teacher.username, 'test_teacher')
        self.assertEqual(self.teacher.name, '李老师')
        self.assertEqual(self.teacher.teacher_id, 'T001')

    def test_teacher_str(self):
        """测试教师模型字符串表示"""
        self.assertEqual(str(self.teacher), 'Teacher: test_teacher')

    def test_teacher_is_authenticated(self):
        """测试教师认证属性"""
        self.assertTrue(self.teacher.is_authenticated)


class StudentLoginTest(TestCase):
    """学生登录接口测试"""

    def setUp(self):
        self.client = Client()
        self.login_url = '/api/studentLogin'
        Student.objects.create(
            username='login_student',
            password='pass123',
            name='测试学生',
            role='student',
            student_id='2024010',
            is_active=True,
            is_deleted=False,
        )

    def test_login_success(self):
        """测试正常登录"""
        response = self.client.post(
            self.login_url,
            {'username': 'login_student', 'password': 'pass123'},
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['msg'], '登录成功')
        self.assertIn('access', data['data'])
        self.assertIn('refresh', data['data'])

    def test_login_wrong_password(self):
        """测试密码错误"""
        response = self.client.post(
            self.login_url,
            {'username': 'login_student', 'password': 'wrong_pass'},
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['code'], 401)

    def test_login_user_not_exist(self):
        """测试用户不存在"""
        response = self.client.post(
            self.login_url,
            {'username': 'nonexistent', 'password': '123456'},
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['code'], 400)

    def test_login_deleted_user(self):
        """测试已删除用户登录"""
        Student.objects.create(
            username='deleted_student',
            password='123456',
            name='已删除',
            student_id='2024099',
            is_deleted=True,
        )
        response = self.client.post(
            self.login_url,
            {'username': 'deleted_student', 'password': '123456'},
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['code'], 400)

    def test_login_inactive_user(self):
        """测试未激活用户登录"""
        Student.objects.create(
            username='inactive_student',
            password='123456',
            name='未激活',
            student_id='2024098',
            is_active=False,
        )
        response = self.client.post(
            self.login_url,
            {'username': 'inactive_student', 'password': '123456'},
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['code'], 400)


class TeacherLoginTest(TestCase):
    """教师登录接口测试"""

    def setUp(self):
        self.client = Client()
        self.login_url = '/api/teacherLogin'
        Teacher.objects.create(
            username='login_teacher',
            password='teach123',
            name='测试教师',
            role='teacher',
            teacher_id='T010',
            is_active=True,
            is_deleted=False,
        )

    def test_login_success(self):
        """测试教师正常登录"""
        response = self.client.post(
            self.login_url,
            {'username': 'login_teacher', 'password': 'teach123'},
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['msg'], '登录成功')

    def test_login_wrong_password(self):
        """测试教师密码错误"""
        response = self.client.post(
            self.login_url,
            {'username': 'login_teacher', 'password': 'wrong'},
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['code'], 401)
