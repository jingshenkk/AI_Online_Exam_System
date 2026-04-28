<template>
  <div class="common-result-view-main-main">
    <div id="paperTitle" class="common-result-view-paper-title">
      <span style="font-size: 25px;font-weight: bolder;">{{ props.paperInfo['title'] }}</span>
      <span style="font-size: 18px;color: #5e5e5e;margin-top: 15px">{{ props.paperInfo['description'] }}</span>
    </div>
    <div v-if="paperModuleQuestion.length === 0" class="common-result-view-module-empty">
      <el-image style="width: 300px;opacity: 0.8" src="/src/images/noData.png" fit="cover"/>
    </div>
    <div v-else class="common-result-view-module-box" v-for="(item) in paperModuleQuestion ">
      <div class="module-info-box">
        <span>{{ item['title'] }}（{{ item['description'] }}）</span>
      </div>
      <div v-if="item['questions'].length === 0">
        <el-image style="width: 250px;opacity: 0.8" src="/src/images/noData.png" fit="cover"/>
      </div>
      <div v-else class="common-result-view-case-list" :style="getIsTrue(question['question_id'])" v-for="(question, index) in item['questions']">
        <div style="width: 100%;display: flex;justify-content: space-between;align-items: center;">
          <span>{{ index + 1 }}. {{ question['question_detail']['topic'] }}（ {{ question['marks'] }}分 ）</span>

        </div>
        <el-radio-group
            v-if="question['question_detail']['type'] === 'judge'"
            :model-value="getStudentAnswer(question['question_id'])"
            style="margin-top: 20px"
        >
          <el-radio value="T">对</el-radio>
          <el-radio value="F">错</el-radio>
        </el-radio-group>
        <el-radio-group v-else-if="question['question_detail']['type'] === 'select'" style="margin-top: 20px" :model-value="getStudentAnswer(question['question_id'])">
          <el-radio v-for="key in Object.keys(question['question_detail']['options'])" :value="key">
            {{ key }}. {{ question['question_detail']['options'][key] }}
          </el-radio>
        </el-radio-group>
        <div v-else-if="question['question_detail']['type'] === 'essay'" style="margin-top: 20px">
          <div style="font-size: 15px; margin-bottom: 10px;">
            <span style="font-weight: bold;">学生答案：</span>
          </div>
          <div style="background-color: #f5f7fa; padding: 15px; border-radius: 4px; white-space: pre-wrap; min-height: 60px;">
            {{ getStudentAnswer(question['question_id']) || '未作答' }}
          </div>
          <div style="margin-top: 10px; font-size: 15px; display: flex; align-items: center; gap: 12px;">
            <span>
              <span style="font-weight: bold;">得分：</span>
              <span style="color: #409eff;">{{ getQuestionScore(question['question_id']) }} / {{ question['marks'] }} 分</span>
            </span>
            <el-tag v-if="getGradingMode(question['question_id'])" size="small"
                    :type="getGradingMode(question['question_id']) === 'STRICT' ? 'danger' : 'success'">
              {{ getGradingMode(question['question_id']) === 'STRICT' ? '严格模式' : '宽松模式' }}
            </el-tag>
            <el-tag v-if="getGradingStatus(question['question_id']) === 'REVIEWED'" size="small" type="warning">
              已人工复核
            </el-tag>
            <el-button v-if="props.isTeacher && getAnswerRecordId(question['question_id'])"
                       type="warning" size="small"
                       @click="handleAdjustScore(question['question_id'], question['marks'])">
              调整分数
            </el-button>
          </div>
          <!-- 逐点评分明细 -->
          <div v-if="getPointDetails(question['question_id']).length > 0" style="margin-top: 16px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <span style="font-weight: bold; font-size: 15px;">评分明细：</span>
              <el-button link type="primary" size="small"
                         @click="togglePointDetails(question['question_id'])">
                {{ expandedQuestions[question['question_id']] ? '收起' : '展开' }}
              </el-button>
            </div>
            <div v-show="expandedQuestions[question['question_id']]">
              <div v-for="(detail, dIdx) in getPointDetails(question['question_id'])" :key="detail.id"
                   style="background: #fafafa; border: 1px solid #ebeef5; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: bold; color: #303133;">得分点 {{ dIdx + 1 }}：{{ detail.description }}</span>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <el-tag :type="detail.final_hit === 'FULL' ? 'success' : 'danger'" size="small">
                      {{ detail.final_hit === 'FULL' ? '命中' : '未命中' }}
                    </el-tag>
                    <span style="font-weight: bold; color: #409eff;">{{ detail.final_score }} / {{ detail.point_score }} 分</span>
                  </div>
                </div>
                <div v-if="detail.llm_1_reason" style="margin-top: 8px; color: #606266; font-size: 13px;">
                  <span style="font-weight: bold;">评分理由：</span>{{ detail.llm_1_reason }}
                </div>
                <!-- 严格模式：显示投票详情 -->
                <div v-if="detail.llm_2_hit" style="margin-top: 8px; font-size: 12px; color: #909399;">
                  <span>投票详情：</span>
                  <el-tag size="small" :type="detail.llm_1_hit === 'FULL' ? 'success' : 'danger'" style="margin: 0 4px;">
                    LLM-1: {{ detail.llm_1_hit }}
                  </el-tag>
                  <el-tag size="small" :type="detail.llm_2_hit === 'FULL' ? 'success' : 'danger'" style="margin: 0 4px;">
                    LLM-2: {{ detail.llm_2_hit }}
                  </el-tag>
                  <el-tag size="small" :type="detail.llm_3_hit === 'FULL' ? 'success' : 'danger'" style="margin: 0 4px;">
                    LLM-3: {{ detail.llm_3_hit }}
                  </el-tag>
                  <span style="margin-left: 8px;">（{{ detail.vote_count }} 票通过）</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <el-divider/>
        <div style="width: auto;display: flex;align-items: center" v-if="question['question_detail']['type'] !== 'essay'">
          <span style="font-size: 15px">参考答案：</span>
          <span style="font-size: 15px;display: flex;align-items: center"  v-if="question['question_detail']['type'] === 'judge'">
            <Check v-if="getReferenceAnswer(question['question_id']) == 'T'" style="height: 17px"/>
            <X v-else style="height: 17px"/>
          </span>
          <span style="font-size: 15px" v-else>{{ getReferenceAnswer(question['question_id']) }}</span>
        </div>
      </div>
    </div>
    <div class="common-result-view-end-line-style" v-if="paperModuleQuestion.length !== 0">
      <span>----- 我是底线 -----</span>
    </div>
  </div>

</template>

<script setup lang="ts">
import { ref, watch} from "vue";
import { Paper, AIGrading } from "../api";
import { ElMessage, ElMessageBox } from "element-plus";
import { Check, X } from "lucide-vue-next";
const props = defineProps({
  paperInfo: { type: Object, required: true, default: () => ({}) },
  examResultAnswers: { type: Array, required: true },
  isCollect: { type: Boolean, required: false, default: false },
  isTeacher: { type: Boolean, required: false, default: false },
})

const emits = defineEmits(['updateData'])

const paperModuleQuestion = ref([])

const getExamResultInfo = () => {
  // 获取试题模块信息
  Paper.getCompletePaperApi(props.paperInfo.id).then((response: any) => {
    if (response.code !== 200) {
      ElMessage.error(response.message)
      return
    }
    // 处理试题选项
    response.data.forEach((item: any) => {
      item.questions.forEach((element: any) => {
        if (element.question_detail.options !== 'T&F') {
          element.question_detail.options = JSON.parse(element.question_detail.options)
        }
      })
    })
    paperModuleQuestion.value = response.data
  })
}

// 获取答案
const getStudentAnswer = (q_id: string) => {
  return props.examResultAnswers?.find(item => item['question_id'] === q_id).solution
}

// 获取试题作答是否正确
const getIsTrue = (q_id: string) => {
  const answerItem = props.examResultAnswers?.find(item => item['question_id'] === q_id)
  // 主观题不显示错误阴影
  if (!answerItem || answerItem.question_type === 'essay') {
    return ''
  }
  return !answerItem.is_true ? 'box-shadow: 0 0 8px #F56C6C;' : ''
}

// 获取主观题得分
const getQuestionScore = (q_id: string) => {
  const answerItem = props.examResultAnswers?.find(item => item['question_id'] === q_id)
  return answerItem?.score || 0
}

// 获取评分模式
const getGradingMode = (q_id: string) => {
  const answerItem = props.examResultAnswers?.find(item => item['question_id'] === q_id)
  return answerItem?.grading_mode || ''
}

// 获取逐点评分明细
const getPointDetails = (q_id: string) => {
  const answerItem = props.examResultAnswers?.find(item => item['question_id'] === q_id)
  return answerItem?.point_details || []
}

// 控制评分明细展开/收起
const expandedQuestions = ref<Record<string, boolean>>({})
const togglePointDetails = (q_id: string) => {
  expandedQuestions.value[q_id] = !expandedQuestions.value[q_id]
}

// 获取答题记录ID
const getAnswerRecordId = (q_id: string) => {
  const answerItem = props.examResultAnswers?.find(item => item['question_id'] === q_id)
  return answerItem?.answer_record_id || ''
}

// 获取评分状态
const getGradingStatus = (q_id: string) => {
  const answerItem = props.examResultAnswers?.find(item => item['question_id'] === q_id)
  return answerItem?.grading_status || ''
}

// 教师调整分数
const handleAdjustScore = (q_id: string, maxScore: number) => {
  const currentScore = getQuestionScore(q_id)
  const answerRecordId = getAnswerRecordId(q_id)
  ElMessageBox.prompt(
    `当前得分：${currentScore} / ${maxScore} 分，请输入调整后的分数：`,
    '调整分数',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputValue: String(currentScore),
      inputPattern: /^\d+(\.\d+)?$/,
      inputErrorMessage: '请输入有效的数字',
      inputValidator: (value: string) => {
        const numValue = parseFloat(value)
        if (isNaN(numValue) || numValue < 0) return '分数不能为负数'
        if (numValue > maxScore) return `分数不能超过满分 ${maxScore} 分`
        return true
      }
    }
  ).then(({ value }) => {
    const adjustedScore = parseFloat(value)
    AIGrading.adjustScoreApi(answerRecordId, adjustedScore).then((response: any) => {
      if (response.code !== 200) {
        ElMessage.error(response.message)
        return
      }
      ElMessage.success('分数调整成功')
      emits('updateData')
    })
  }).catch(() => {
    // 用户取消操作
  })
}

// 获取参考答案
const getReferenceAnswer = (q_id: string) => {
  return props.examResultAnswers?.find(item => item['question_id'] === q_id).reference_answer
}

watch(() => props.paperInfo, (newValue) => {
  if (newValue && Object.keys(newValue).length > 0) {
    getExamResultInfo()
  }
}, { immediate: true })


</script>

<style scoped lang="scss">
.common-result-view-main-main {
  width: 100%;
  height: calc(100vh - 180px);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.common-result-view-paper-title {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 20px;
}

.common-result-view-module-empty {
  width:98%;
  display: flex;
  justify-content: center;
  margin-top: 50px
}

.common-result-view-case-list {
  width: 90%;
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  box-shadow: 0 0 8px rgba(154, 154, 154, 0.5);
  border-radius: 10px;
  padding: 20px 30px;
  color: #5e5e5e;
}

.common-result-view-module-box {
  width: 98%;
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;

  .module-info-box {
    width: 100%;
    height: 30px;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 5px;
    background: #606060;
    color: #fff;
    font-size: 13px;
  }
}
.common-result-view-end-line-style {
  width: 100%;
  display: flex;
  margin-top: 20px;
  justify-content: center;
  font-size: 13px;
  color: #a4a4a4
}
</style>