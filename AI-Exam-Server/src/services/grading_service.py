
import logging
from typing import List, Dict, Tuple
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class LenientGradingService:
    """宽松模式：单LLM评分"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def grade(self, record_id):
        from src.apps.ExamResult.models import AnswerRecord, ScorePointDetail
        from src.apps.QuestionManagement.models import ScoringPoint
        
        record = AnswerRecord.objects.get(id=record_id)
        question_id = record.question_id
        
        from src.apps.QuestionManagement.models import Questions
        question = Questions.objects.get(id=question_id)
        
        points = ScoringPoint.objects.filter(
            question_id=question_id,
            is_approved=True
        ).order_by('sort_order')
        
        if not points:
            raise ValueError("该题目暂无已审核的评分细则")
        
        record.status = 'SCORING'
        record.save()
        
        try:
            result = self.llm_service.score_answer(
                record.answer_text,
                question,
                list(points)
            )
            
            # 构建 point_id 到评分结果的映射
            point_score_map = {}
            for point_result in result['point_scores']:
                point_score_map[str(point_result['point_id'])] = point_result
            
            total_score = 0.0
            for point in points:
                detail = point_score_map.get(str(point.id))
                if detail:
                    earned = float(detail['earned'])
                    total_score += earned
                    ScorePointDetail.objects.create(
                        answer_record_id=record_id,
                        scoring_point_id=str(point.id),
                        llm_1_hit=detail['hit'],
                        llm_1_score=earned,
                        llm_1_reason=detail['reason'],
                        final_hit=detail['hit'],
                        final_score=earned,
                        vote_count=1
                    )
            
            record.final_score = round(total_score, 1)
            record.status = 'SCORED'
            record.save()
            
            logger.info(f"宽松模式评分完成: record_id={record_id}, score={record.final_score}")
            return record
            
        except Exception as error:
            logger.error(f"宽松模式评分失败: record_id={record_id}, error={error}")
            record.status = 'PENDING'
            record.save()
            raise

class StrictGradingService:
    """严格模式：三LLM投票评分"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def grade(self, record_id):
        from src.apps.ExamResult.models import AnswerRecord, ScorePointDetail
        from src.apps.QuestionManagement.models import ScoringPoint, Questions
        
        record = AnswerRecord.objects.get(id=record_id)
        question = Questions.objects.get(id=record.question_id)
        
        points = ScoringPoint.objects.filter(
            question_id=record.question_id,
            is_approved=True
        ).order_by('sort_order')
        
        if not points:
            raise ValueError("该题目暂无已审核的评分细则")
        
        record.status = 'SCORING'
        record.save()
        
        try:
            # 三个LLM独立评分
            results = []
            for i in range(3):
                result = self.llm_service.score_answer(
                    record.answer_text,
                    question,
                    list(points)
                )
                results.append(result)
            
            # 逐点投票
            total_score = 0.0
            for point in points:
                votes = []
                for result in results:
                    detail = next(
                        (p for p in result['point_scores'] if str(p['point_id']) == str(point.id)),
                        None
                    )
                    if detail:
                        votes.append(detail)
                
                if len(votes) < 3:
                    logger.warning(f"得分点 {point.id} 的投票数不足3个，跳过")
                    continue
                
                final_hit, final_score, vote_count = self._vote(votes, point)
                total_score += final_score
                
                ScorePointDetail.objects.create(
                    answer_record_id=record_id,
                    scoring_point_id=str(point.id),
                    llm_1_hit=votes[0]['hit'],
                    llm_1_score=float(votes[0]['earned']),
                    llm_1_reason=votes[0]['reason'],
                    llm_2_hit=votes[1]['hit'],
                    llm_2_score=float(votes[1]['earned']),
                    llm_2_reason=votes[1]['reason'],
                    llm_3_hit=votes[2]['hit'],
                    llm_3_score=float(votes[2]['earned']),
                    llm_3_reason=votes[2]['reason'],
                    final_hit=final_hit,
                    final_score=final_score,
                    vote_count=vote_count
                )
            
            record.final_score = round(total_score, 1)
            record.status = 'SCORED'
            record.save()
            
            logger.info(f"严格模式评分完成: record_id={record_id}, score={record.final_score}")
            return record
            
        except Exception as error:
            logger.error(f"严格模式评分失败: record_id={record_id}, error={error}")
            record.status = 'PENDING'
            record.save()
            raise
    
    def _vote(self, votes, point):
        """投票逻辑：多数票决定，只有FULL和MISS两种状态"""
        hit_counts = {'FULL': 0, 'MISS': 0}
        
        for vote in votes:
            hit_type = vote['hit']
            if hit_type in hit_counts:
                hit_counts[hit_type] += 1
        
        # 取多数票（FULL和MISS只有两种，3票中必有一种>=2）
        if hit_counts['FULL'] >= 2:
            final_hit = 'FULL'
            final_score = point.score
            vote_count = hit_counts['FULL']
        else:
            final_hit = 'MISS'
            final_score = 0.0
            vote_count = hit_counts['MISS']
        
        return (final_hit, round(final_score, 1), vote_count)

class GradingOrchestrator:
    """评分主流程编排"""
    
    def __init__(self):
        self.lenient_service = LenientGradingService()
        self.strict_service = StrictGradingService()
    
    def score_answer(self, record_id):
        from src.apps.ExamResult.models import AnswerRecord
        record = AnswerRecord.objects.get(id=record_id)
        
        logger.info(f"开始评分: record_id={record_id}, mode={record.grading_mode}")
        
        if record.grading_mode == 'LENIENT':
            return self.lenient_service.grade(record_id)
        elif record.grading_mode == 'STRICT':
            return self.strict_service.grade(record_id)
        else:
            raise ValueError(f"不支持的评分模式: {record.grading_mode}")
