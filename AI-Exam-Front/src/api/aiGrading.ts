import axios from '../utils/request'
import {Result} from "./response.interface.ts";

export class AIGrading {
  // 获取题目的评分细则列表
  async getScoringPointsApi(questionId: string): Promise<Result> {
    const { data } = await axios.get(`/scoringPoints/${questionId}`)
    return data
  }

  // 创建评分细则
  async createScoringPointApi(pointInfo: object): Promise<Result> {
    const { data } = await axios.post('/scoringPoints', { ...pointInfo })
    return data
  }

  // 修改评分细则
  async updateScoringPointApi(pointId: string, pointInfo: object): Promise<Result> {
    const { data } = await axios.put(`/scoringPoint/${pointId}`, { ...pointInfo })
    return data
  }

  // 删除评分细则
  async deleteScoringPointApi(pointId: string): Promise<Result> {
    const { data } = await axios.delete(`/scoringPoint/${pointId}`)
    return data
  }

  // 审核通过评分细则
  async approveScoringPointApi(pointId: string): Promise<Result> {
    const { data } = await axios.put(`/scoringPoint/${pointId}/approve`)
    return data
  }

  // 批量审核通过
  async batchApproveScoringPointsApi(ids: string[]): Promise<Result> {
    const { data } = await axios.put('/scoringPointBatchApprove', { ids })
    return data
  }

  // AI生成评分细则
  async generateRubricApi(questionId: string, totalScore: number): Promise<Result> {
    const { data } = await axios.post(`/rubricGenerate/${questionId}`, { total_score: totalScore })
    return data
  }

  // 提交答案并触发评分
  async submitAnswerApi(answerData: {
    question_id: string,
    student_id: string,
    exam_result_id?: string,
    answer_text: string,
    grading_mode: string
  }): Promise<Result> {
    const { data } = await axios.post('/answerRecord', { ...answerData })
    return data
  }

  // 查询评分结果详情
  async getAnswerRecordApi(recordId: string): Promise<Result> {
    const { data } = await axios.get(`/answerRecord/${recordId}`)
    return data
  }

  // 查询答题记录列表
  async getAnswerRecordsApi(querySet: object): Promise<Result> {
    const { data } = await axios.get('/answerRecord', { params: { ...querySet } })
    return data
  }

  // 保存/更新草稿
  async saveDraftApi(draftData: {
    exam_result_id: string,
    question_id: string,
    answer: string
  }): Promise<Result> {
    const { data } = await axios.post('/answerDraft', { ...draftData })
    return data
  }

  // 获取草稿
  async getDraftApi(examResultId: string, questionId: string): Promise<Result> {
    const { data } = await axios.get('/answerDraft', {
      params: { exam_result_id: examResultId, question_id: questionId }
    })
    return data
  }

  // 教师调整主观题分数
  async adjustScoreApi(answerRecordId: string, adjustedScore: number): Promise<Result> {
    const { data } = await axios.put(`/adjustScore/${answerRecordId}`, { adjusted_score: adjustedScore })
    return data
  }
}

export default new AIGrading()
