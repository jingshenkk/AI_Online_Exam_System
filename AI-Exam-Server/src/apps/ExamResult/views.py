# -*- coding: utf-8 -*-
# @File    : views.py
# @Describe: ExamResult应用视图层

import os

from openpyxl import Workbook
from openpyxl.styles import Font
from django.db.models import Sum
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import ExamResult, ExamResultDetail, AnswerRecord, AnswerDraft, ScorePointDetail
from src.apps.ExamManagement.models import Exam
from src.apps.ExamManagement.serializers import ExamSerializer
from src.apps.QuestionManagement.models import Questions, ScoringPoint
from src.apps.PaperManagement.models import Paper, PaperQuestions
from src.apps.PaperManagement.serializers import PaperQuestionsSerializer
from .serializers import ExamResultSerializer
from .serializers import ExamResultDetailSerializer, AnswerRecordSerializer, AnswerDraftSerializer
from src.utils.response_utils import ResponseCode, api_response


class ExamResultBaseView(APIView):
    # JWT校验
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """post 批量创建考试结果信息
        Args:
            request (Object): { "exam_id": 考试ID, "student_ids": 学生IDs }
        """
        student_ids = request.data['student_ids']
        exam_result_list = []
        if len(student_ids) == 0:
            return api_response(ResponseCode.SUCCESS, '考试关联的学生为空！')
        else:
            for s_id in student_ids:
                exam_result_list.append({
                    'exam_id': request.data['exam_id'],
                    'student_id': s_id
                })
            serializer = ExamResultSerializer(data=exam_result_list, many=True)
            if serializer.is_valid():
                # 如果新数据校验通过，对老数据进行删除操作
                old_data = ExamResult.objects.filter(exam_id=request.data['exam_id'])
                old_data_length = len(old_data)
                deleted_count, _ = old_data.delete()
                if deleted_count != old_data_length:
                    return api_response(ResponseCode.BAD_REQUEST, '创建失败！数据处理失败！', serializer.errors)
                # 老数据删除后，新数据存储
                serializer.save()
                data = Response(serializer.data)
                return api_response(ResponseCode.SUCCESS, '创建成功', data.data)
            else:
                return api_response(ResponseCode.BAD_REQUEST, '创建失败', serializer.errors)

    def delete(self, _, **kwargs):
        """delete 删除考试结果信息（物理删除）
        Args:
            _ (-): 缺省参数
            id (Object): 考试ID
        """
        try:
            exam_instance = ExamResult.objects.get(id=kwargs['id'])
        except ExamResult.DoesNotExist:
            return api_response(ResponseCode.NOT_FOUND, '考试结果不存在，删除失败！')
        if exam_instance.start_time is not None:
            return api_response(ResponseCode.BAD_REQUEST, '该学生已经参加考试，无法删除！')
        else:
            exam_instance.delete()
            # 返回成功响应
            return api_response(ResponseCode.SUCCESS, '删除成功！')

    def put(self, request, **kwargs):
        """put 编辑考试结果信息
        Args:
            id (str): 考试结果ID
            request (Object): 请求参数
        """
        try:
            # 获取需要编辑的考试结果实例
            exam_result_instance = ExamResult.objects.get(id=kwargs['id'])
        except ExamResult.DoesNotExist:
            return api_response(ResponseCode.NOT_FOUND, '编辑失败！考试结果不存在，无法进行编辑！')
        serializer = ExamResultSerializer(exam_result_instance, request.data, partial=True)
        # 检查更新后的数据是否符合规则校验
        if serializer.is_valid():
            # 保存验证过的数据以更新现有的 ExamResult 实例
            serializer.save()
            # 返回成功响应，包含序列化后的数据和 HTTP 200 OK 状态
            data = Response(serializer.data)
            return api_response(ResponseCode.SUCCESS, '编辑成功', data.data)
        else:
            # 返回错误响应，包含验证错误和 HTTP 400 Bad Request 状态
            return api_response(ResponseCode.BAD_REQUEST, '编辑失败！存在校验失败的字段', serializer.error_messages)

    def get(self, request, **kwargs):
        """get 查询考试结果列表信息（根据考试结果ID获取考试结果详情）
        Args:
            request (Object): 请求参数
            kwargs[id] (str): 考试结果ID
        """
        if len(kwargs.items()) != 0:
            try:
                # 获取指定考试结果实例
                exam_result_instance = ExamResult.objects.get(id=kwargs['id'])
            except ExamResult.DoesNotExist:
                # 考试结果不存在，返回错误响应和 HTTP 404 Not Found 状态
                return api_response(ResponseCode.NOT_FOUND, '考试结果不存在！')
            # 序列化试题详情数据
            serializer = ExamResultSerializer(exam_result_instance)
            # 返回序列化后的试题详情数据
            data = Response(serializer.data)
            return api_response(ResponseCode.SUCCESS, '查询考试结果成功', data.data)
        else:
            # 定义查询参数和它们对应的模型字段
            query_params_mapping = {
                'exam_id': 'exam_id',
                'result_mark': 'result_mark'
                # 添加其他查询参数和字段的映射
            }
            # 构建查询条件的字典
            filters = {}
            for param, field in query_params_mapping.items():
                value = request.query_params.get(param, None)
                if value is not None and value != '':
                    filters[field] = value
            # 执行查询
            queryset = ExamResult.objects.filter(**filters).order_by('-result_mark')
            # 序列化试题数据
            serializer = ExamResultSerializer(queryset, many=True)
            serializer_data = serializer.data
            # 获取查询参数
            filter_stu_id = request.query_params.get('student_id', None)
            filter_stu_name = request.query_params.get('name', None)
            # 二次筛选
            if filter_stu_id is not None or filter_stu_name is not None:
                filter_stu_id = filter_stu_id.strip() if filter_stu_id else None
                filter_stu_name = filter_stu_name.strip() if filter_stu_name else None

                def filter_item(item):
                    if filter_stu_id and filter_stu_id not in item['student_info']['student_id']:
                        return False
                    if filter_stu_name and filter_stu_name not in item['student_info']['name']:
                        return False
                    return True

                serializer_data = [item for item in serializer_data if filter_item(item)]
            # 返回序列化后的数据
            data = Response(serializer_data)
            resp = { 'total': len(data.data), 'data': data.data }
            return api_response(ResponseCode.SUCCESS, '查询成功', resp)


class ExamResultStudentView(APIView):
    # JWT校验
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """get 查询考试结果（学生端）
        Args:
            request (Object): 请求参数
        """
        student_id = request.query_params.get("student_id", None)
        queryset = ExamResult.objects.filter(student_id=student_id).order_by('-updated_at')
        # 序列化数据
        serializer_data = ExamResultSerializer(queryset, many=True).data
        title_filter = request.query_params.get("title", None)  # 获取标题筛选参数
        filter_datas = []
        # 根据 exam_info.title 进行筛选
        if title_filter:
            for item in serializer_data:
                if title_filter in item['exam_info']['title']:
                    filter_datas.append(item)
        else:
            filter_datas = serializer_data

        # 实例化分页器并配置参数
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('pageSize', 50))
        paginator.page_query_param = 'currentPage'
        # 进行分页处理
        paginated_queryset = paginator.paginate_queryset(filter_datas, request)
        resp = { 'total': len(filter_datas), 'data': paginated_queryset }
        return api_response(ResponseCode.SUCCESS, '查询成功', resp)


class ExamOnlineGetResultView(APIView):
    
    def get(self, request):
        """get 在线考试页面使用 - 获取考生考试信息
        Args:
            request (Object): 
                examId: 考试ID
                studentId: 学生ID
        """
        exam_id = request.query_params.get('examId')
        student_id = request.query_params.get('studentId')
        queryset = ExamResult.objects.filter(exam_id=exam_id).filter(student_id=student_id)
        if len(queryset) <= 0:
            return api_response(ResponseCode.BAD_REQUEST, '没有查询到对应的考试信息，请刷新后重试！')
        # 序列化考试数据
        serializer = ExamResultSerializer(queryset.first())
        return api_response(ResponseCode.SUCCESS, '查询成功', serializer.data)
        

class ExamResultDetailBaseView(APIView):
    # JWT校验
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """post 创建考试结果详情信息
        Args:
            request (Object): 请求参数
        """
        meta_data = request.data
        # 获取考试ID、试卷ID
        exam_id = ExamResult.objects.filter(id=meta_data['exam_result_id']).first().exam_id
        exam_info = Exam.objects.filter(id=exam_id).first()
        # 及格分数
        pass_mark = exam_info.pass_mark
        # 试卷总分
        sum_marks = PaperQuestions.objects.filter(
                    paper_id=exam_info.paper_id).aggregate(actual_total=Sum('marks'))
        paper_questions = PaperQuestions.objects.filter(paper_id=exam_info.paper_id)
        serializer_paper_questions = PaperQuestionsSerializer(paper_questions, many=True).data
        # 获取试卷的评分模式
        paper_grading_mode = Paper.objects.filter(id=exam_info.paper_id).values_list('grading_mode', flat=True).first() or 'LENIENT'
        answers = meta_data['answers']
        result_detail_list = []
        result_total_mark = 0
        for key in answers.keys():
            result_record = { 'exam_result_id': meta_data['exam_result_id'], 'question_id': key, 'solution': answers[key], 'mark': 0 }
            # 若学生没有答题，直接0分
            if answers[key] is not None:
                filter_res = list(filter(lambda x: x['question_id'] == key, serializer_paper_questions))
                question_instance = Questions.objects.filter(id=key).first()
                
                if question_instance and question_instance.type == 'essay':
                    # 主观题：调用AI评分
                    try:
                        from src.apps.ExamResult.models import AnswerRecord
                        from src.services.grading_service import GradingOrchestrator
                        
                        answer_record = AnswerRecord.objects.create(
                            question_id=key,
                            student_id=ExamResult.objects.filter(id=meta_data['exam_result_id']).first().student_id,
                            exam_result_id=meta_data['exam_result_id'],
                            answer_text=answers[key],
                            grading_mode=paper_grading_mode,
                            status='PENDING'
                        )
                        
                        orchestrator = GradingOrchestrator()
                        graded_record = orchestrator.score_answer(str(answer_record.id))
                        
                        if graded_record.final_score is not None:
                            result_record['mark'] = graded_record.final_score
                    except Exception as grading_error:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"主观题评分失败: question_id={key}, error={grading_error}")
                        result_record['mark'] = 0
                else:
                    # 客观题：保持原有逻辑
                    if filter_res and filter_res[0]['question_detail']['answer'] == answers[key]:
                        result_record['mark'] = filter_res[0]['marks']
            result_total_mark += result_record['mark']
            result_detail_list.append(result_record)
        serializer = ExamResultDetailSerializer(data=result_detail_list, many=True)
        if serializer.is_valid():
            serializer.save()
            data = Response(serializer.data)
            return api_response(ResponseCode.SUCCESS, '创建成功', {
                "data": data.data, 
                "result_total_mark": result_total_mark, 
                "sum_marks": sum_marks['actual_total'],
                "percentage": (result_total_mark / sum_marks['actual_total']) * 100,
                "pass_mark": pass_mark
            })
        else:
            return api_response(ResponseCode.BAD_REQUEST, '创建失败', serializer.errors)

    def get(self, request, **kwargs):
        """get 根据考试结果ID获取详情信息
        Args:
            _ (——): 缺省参数
            id：试卷ID
        """
        student_id = request.query_params.get('student_id', None)
        # 获取考试结果ID为入参的详情实例
        exam_result_detal_instance = ExamResultDetail.objects.filter(exam_result_id=kwargs['id'])
        if len(exam_result_detal_instance) == 0:
            return api_response(ResponseCode.NOT_FOUND, '没有找到该考试结果的 详情信息！')
        else:
            serializer = ExamResultDetailSerializer(exam_result_detal_instance, many=True)
            for item in serializer.data:
                question = Questions.objects.filter(id=item['question_id']).first()
                answer = question.answer if question else ''
                question_type = question.type if question else 'select'
                item['question_type'] = question_type
                item['score'] = item['mark']
                if question_type == 'essay':
                    # 主观题：不做简单的字符串对比判断对错
                    item['is_true'] = True
                    item['reference_answer'] = answer
                    # 查询该主观题的答题记录和逐点评分明细
                    answer_record = AnswerRecord.objects.filter(
                        question_id=item['question_id'],
                        exam_result_id=kwargs['id']
                    ).first()
                    if answer_record:
                        item['answer_record_id'] = str(answer_record.id)
                        item['grading_mode'] = answer_record.grading_mode
                        item['grading_status'] = answer_record.status
                        point_details = ScorePointDetail.objects.filter(answer_record_id=answer_record.id)
                        details_list = []
                        for detail in point_details:
                            point_info = ScoringPoint.objects.filter(id=detail.scoring_point_id).first()
                            detail_data = {
                                'id': str(detail.id),
                                'scoring_point_id': str(detail.scoring_point_id),
                                'description': point_info.description if point_info else '',
                                'point_score': point_info.score if point_info else 0,
                                'final_hit': detail.final_hit,
                                'final_score': detail.final_score,
                                'vote_count': detail.vote_count,
                                'llm_1_hit': detail.llm_1_hit,
                                'llm_1_score': detail.llm_1_score,
                                'llm_1_reason': detail.llm_1_reason,
                            }
                            if answer_record.grading_mode == 'STRICT':
                                detail_data['llm_2_hit'] = detail.llm_2_hit
                                detail_data['llm_2_score'] = detail.llm_2_score
                                detail_data['llm_2_reason'] = detail.llm_2_reason
                                detail_data['llm_3_hit'] = detail.llm_3_hit
                                detail_data['llm_3_score'] = detail.llm_3_score
                                detail_data['llm_3_reason'] = detail.llm_3_reason
                            details_list.append(detail_data)
                        item['point_details'] = details_list
                else:
                    # 客观题：保持原有逻辑
                    item['is_true'] = True if answer == item['solution'] else False
                    item['reference_answer'] = answer
            data = Response(serializer.data)
            return api_response(ResponseCode.SUCCESS, '获取考试结果详情成功', data.data)


class GenerateExamResultExcel(APIView):
    
    def post(self, request):
        try:
            exam_id = request.data['exam_id']
            exam_instance = Exam.objects.filter(id=exam_id).first()
            exam_serializer = ExamSerializer(exam_instance)
            exam_result_instance = ExamResult.objects.filter(exam_id=exam_id).order_by('-result_mark')
            exam_result_datas = ExamResultSerializer(exam_result_instance, many=True).data
            
            # 创建一个新的工作簿
            wb = Workbook()
            ws = wb.active

            # 定义总览标题和对应的数据
            headers = [['考试名称', '试卷名称', '总分'], ['考试开始时间', '考试结束时间', '考试人数']]
            datas = [[
                exam_serializer.data['title'],
                exam_serializer.data['paper_info']['title'],
                exam_serializer.data['paper_info']['total_marks']
            ],[
                exam_serializer.data['start_time'],
                exam_serializer.data['end_time'],
                len(exam_result_datas)
            ]]
            # 总览数据填充
            for index in range(len(headers)):
                # 写入标题并设置加粗
                for col, (header, data) in enumerate(zip(headers[index], datas[index]), start=1):
                    if col == 1:
                        cell = ws.cell(row=index + 1, column=col, value=header)
                        cell.font = Font(bold=True)
                        cell = ws.cell(row=index + 1, column=col + 1, value=data)
                    else:
                        cell = ws.cell(row=index + 1, column=2 * col - 1, value=header)
                        cell.font = Font(bold=True)
                        cell = ws.cell(row=index + 1, column=2 * col, value=data)
            
            # 定义主体表头数据并填充
            students_result_header = ['学号', '学生姓名', '得分', '考试状态', '考试开始时间', '考试结束时间']
            for index, item in enumerate(students_result_header):
                cell = ws.cell(row=4, column=index+1, value=item)
                cell.font = Font(bold=True)
            
            # 主体数据填充
            for index, item in enumerate(exam_result_datas):
                cell = ws.cell(row=index+5, column=1, value=item['student_info']['student_id'])
                cell = ws.cell(row=index+5, column=2, value=item['student_info']['name'])
                cell = ws.cell(row=index+5, column=3, value=item['result_mark'])
                cell = ws.cell(row=index+5, column=4, value='正常' if item['ending_status'] else '异常退出' )
                cell = ws.cell(row=index+5, column=5, value=item['start_time'])
                cell = ws.cell(row=index+5, column=6, value=item['end_time'])

            # 设置所有行的高度为 30
            for row in range(1, len(exam_result_datas) + 6):
                ws.row_dimensions[row].height = 30
                
            # 设置列 A 到 F 的宽度
            column_width = 35  # 设置的宽度值
            for col in range(ord('A'), ord('F') + 1):  # A到F的ASCII码范围
                ws.column_dimensions[chr(col)].width = column_width

            # ========== 新增：主观题评分详情 Sheet ==========
            # 查询该考试中所有主观题
            paper_id = exam_serializer.data['paper_info']['id']
            paper_questions = PaperQuestions.objects.filter(paper_id=paper_id)
            essay_question_ids = []
            for pq in paper_questions:
                question = Questions.objects.filter(id=pq.question_id, type='essay').first()
                if question:
                    essay_question_ids.append(str(question.id))

            if essay_question_ids:
                ws2 = wb.create_sheet(title='主观题评分详情')
                # 表头
                essay_headers = ['学号', '学生姓名', '题目', '学生答案', '得分', '满分', '评分模式', '评分状态', '得分点明细']
                for col_idx, header in enumerate(essay_headers, start=1):
                    cell = ws2.cell(row=1, column=col_idx, value=header)
                    cell.font = Font(bold=True)

                row_idx = 2
                for result_data in exam_result_datas:
                    exam_result_id = result_data['id']
                    student_id_str = result_data['student_info']['student_id']
                    student_name = result_data['student_info']['name']

                    for q_id in essay_question_ids:
                        question = Questions.objects.filter(id=q_id).first()
                        if not question:
                            continue

                        # 查询答题记录
                        answer_record = AnswerRecord.objects.filter(
                            question_id=q_id,
                            exam_result_id=exam_result_id
                        ).first()

                        # 查询学生答案
                        detail = ExamResultDetail.objects.filter(
                            exam_result_id=exam_result_id,
                            question_id=q_id
                        ).first()

                        student_answer = detail.solution if detail else '未作答'
                        score = detail.mark if detail else 0

                        # 获取满分
                        pq = PaperQuestions.objects.filter(paper_id=paper_id, question_id=q_id).first()
                        max_score = pq.marks if pq else 0

                        grading_mode = answer_record.grading_mode if answer_record else ''
                        grading_status = answer_record.status if answer_record else ''

                        # 构建得分点明细文本
                        point_detail_text = ''
                        if answer_record:
                            point_details = ScorePointDetail.objects.filter(answer_record_id=answer_record.id)
                            detail_parts = []
                            for pd in point_details:
                                sp = ScoringPoint.objects.filter(id=pd.scoring_point_id).first()
                                desc = sp.description if sp else '未知'
                                hit_text = '命中' if pd.final_hit == 'FULL' else '未命中'
                                detail_parts.append(f'{desc}: {hit_text}({pd.final_score}分)')
                            point_detail_text = '; '.join(detail_parts)

                        ws2.cell(row=row_idx, column=1, value=student_id_str)
                        ws2.cell(row=row_idx, column=2, value=student_name)
                        ws2.cell(row=row_idx, column=3, value=question.topic)
                        ws2.cell(row=row_idx, column=4, value=student_answer)
                        ws2.cell(row=row_idx, column=5, value=score)
                        ws2.cell(row=row_idx, column=6, value=max_score)
                        ws2.cell(row=row_idx, column=7, value=grading_mode)
                        ws2.cell(row=row_idx, column=8, value=grading_status)
                        ws2.cell(row=row_idx, column=9, value=point_detail_text)
                        row_idx += 1

                # 设置列宽
                column_widths = [15, 15, 40, 50, 10, 10, 12, 12, 60]
                for col_idx, width in enumerate(column_widths, start=1):
                    ws2.column_dimensions[chr(64 + col_idx)].width = width
                # 设置行高
                for row in range(1, row_idx):
                    ws2.row_dimensions[row].height = 30

            # 指定目录路径
            directory = settings.EXAM_RESULT_ROOT
            os.makedirs(directory, exist_ok=True)  # 确保目录存在
            file_name = '{}.xlsx'.format(exam_id)
            # 保存文件
            wb.save(os.path.join(directory, file_name))
            return api_response(ResponseCode.SUCCESS, '生成成功', file_name)
        except Exception as e:
            return api_response(ResponseCode.BAD_REQUEST, '生成失败!', e)

class AnswerRecordView(APIView):
    """答题记录管理"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """提交答案并触发评分（同步）"""
        required_fields = ['question_id', 'student_id', 'answer_text', 'grading_mode']
        for field in required_fields:
            if not request.data.get(field):
                return api_response(ResponseCode.BAD_REQUEST, f'缺少必要参数：{field}')
        
        grading_mode = request.data.get('grading_mode')
        if grading_mode not in ['LENIENT', 'STRICT']:
            return api_response(ResponseCode.BAD_REQUEST, 'grading_mode 必须是 LENIENT 或 STRICT')
        
        # 验证题目存在且为主观题
        question = Questions.objects.filter(id=request.data['question_id']).first()
        if not question:
            return api_response(ResponseCode.NOT_FOUND, '题目不存在')
        if question.type != 'essay':
            return api_response(ResponseCode.BAD_REQUEST, '仅主观题支持AI评分')
        
        # 检查是否有已审核的评分细则
        approved_points = ScoringPoint.objects.filter(question_id=request.data['question_id'], is_approved=True)
        if not approved_points.exists():
            return api_response(ResponseCode.BAD_REQUEST, '该题目暂无已审核的评分细则，请先完成评分细则审核')
        
        # 创建答题记录
        serializer = AnswerRecordSerializer(data=request.data)
        if serializer.is_valid():
            record = serializer.save(status='PENDING')
            
            # 同步触发评分
            from src.services.grading_service import GradingOrchestrator
            orchestrator = GradingOrchestrator()
            try:
                record = orchestrator.score_answer(str(record.id))
                result_serializer = AnswerRecordSerializer(record)
                return api_response(ResponseCode.CREATED, '评分完成', result_serializer.data)
            except Exception as e:
                return api_response(ResponseCode.INTERNAL_SERVER_ERROR, f'评分失败: {str(e)}')
        return api_response(ResponseCode.BAD_REQUEST, '创建失败', serializer.errors)
    
    def get(self, request, **kwargs):
        """查询答题记录"""
        if len(kwargs.items()) != 0:
            # 查询单条记录详情
            try:
                record = AnswerRecord.objects.get(id=kwargs['id'])
            except AnswerRecord.DoesNotExist:
                return api_response(ResponseCode.NOT_FOUND, '答题记录不存在')
            serializer = AnswerRecordSerializer(record)
            return api_response(ResponseCode.SUCCESS, '查询成功', serializer.data)
        else:
            # 查询列表
            filters = {}
            for param in ['question_id', 'student_id', 'exam_result_id', 'status', 'grading_mode']:
                value = request.query_params.get(param)
                if value:
                    filters[param] = value
            queryset = AnswerRecord.objects.filter(**filters).order_by('-created_at')
            serializer = AnswerRecordSerializer(queryset, many=True)
            resp = {'total': len(queryset), 'data': serializer.data}
            return api_response(ResponseCode.SUCCESS, '查询成功', resp)

class AnswerDraftView(APIView):
    """答案草稿管理"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """保存/更新草稿"""
        exam_result_id = request.data.get('exam_result_id')
        question_id = request.data.get('question_id')
        answer = request.data.get('answer', '')
        
        if not exam_result_id or not question_id:
            return api_response(ResponseCode.BAD_REQUEST, '缺少必要参数：exam_result_id、question_id')
        
        # 使用 update_or_create 实现 upsert
        draft, created = AnswerDraft.objects.update_or_create(
            exam_result_id=exam_result_id,
            question_id=question_id,
            defaults={'answer': answer}
        )
        serializer = AnswerDraftSerializer(draft)
        return api_response(ResponseCode.SUCCESS, '保存成功', serializer.data)
    
    def get(self, request):
        """获取草稿"""
        exam_result_id = request.query_params.get('exam_result_id')
        question_id = request.query_params.get('question_id')
        
        if not exam_result_id or not question_id:
            return api_response(ResponseCode.BAD_REQUEST, '缺少必要参数：exam_result_id、question_id')
        
        draft = AnswerDraft.objects.filter(
            exam_result_id=exam_result_id,
            question_id=question_id
        ).first()
        
        if draft:
            serializer = AnswerDraftSerializer(draft)
            return api_response(ResponseCode.SUCCESS, '查询成功', serializer.data)
        else:
            return api_response(ResponseCode.SUCCESS, '暂无草稿', {'answer': ''})
        

class AdjustScoreView(APIView):
    """教师人工复核-调整主观题分数"""
    permission_classes = [IsAuthenticated]

    def put(self, request, **kwargs):
        """调整答题记录的分数
        Args:
            request: 请求参数，包含 adjusted_score（调整后的总分）
            kwargs: answer_record_id
        """
        answer_record_id = kwargs.get('id')
        adjusted_score = request.data.get('adjusted_score')

        if adjusted_score is None:
            return api_response(ResponseCode.BAD_REQUEST, '缺少必要参数：adjusted_score')

        try:
            adjusted_score = float(adjusted_score)
        except (ValueError, TypeError):
            return api_response(ResponseCode.BAD_REQUEST, 'adjusted_score 必须是数字')

        try:
            answer_record = AnswerRecord.objects.get(id=answer_record_id)
        except AnswerRecord.DoesNotExist:
            return api_response(ResponseCode.NOT_FOUND, '答题记录不存在')

        old_score = answer_record.final_score or 0

        # 更新答题记录的总分和状态
        answer_record.final_score = adjusted_score
        answer_record.status = 'REVIEWED'
        answer_record.save()

        # 同步更新 ExamResultDetail 中该题的分数
        exam_result_detail = ExamResultDetail.objects.filter(
            exam_result_id=answer_record.exam_result_id,
            question_id=answer_record.question_id
        ).first()
        if exam_result_detail:
            exam_result_detail.mark = adjusted_score
            exam_result_detail.save()

        # 重新计算 ExamResult 的总分
        exam_result = ExamResult.objects.filter(id=answer_record.exam_result_id).first()
        if exam_result:
            total_mark = ExamResultDetail.objects.filter(
                exam_result_id=answer_record.exam_result_id
            ).aggregate(total=Sum('mark'))['total'] or 0
            exam_result.result_mark = total_mark
            exam_result.save()

        return api_response(ResponseCode.SUCCESS, '分数调整成功', {
            'answer_record_id': str(answer_record.id),
            'old_score': old_score,
            'new_score': adjusted_score,
            'exam_result_total': exam_result.result_mark if exam_result else 0
        })


if __name__ == '__main__':
    pass