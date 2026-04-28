<template>
  <div class="exam-online-main-box">
    <div class="common-module-header-box">
      <el-icon >
        <MonitorCheck />
      </el-icon>
      <span style="margin-left: 10px">在线考试</span>
    </div>
    <div class="exam-online-tips-box">
      <el-icon style="margin-left: 20px;color: #0077e5;font-size: 15px"><CircleAlert /></el-icon>
      <span style="margin-left: 8px;letter-spacing: 1px">
        温馨提示：中途离开都将被视为异常退出，若异常退出，本次考试将记为0分并且无法再次参加该考试，请谨慎操作!
      </span>
    </div>
    <div class="exam-online-operation-area">
      <div class="exam-online-questions-box">
        <h2>高中物理第一次测验</h2>
        <span>共6道题，祝大家好运</span>
        <div class="exam-online-paper-module-box" v-for="item in paperModuleQuestion">
          <div class="module-info-box">
            <span>{{ item.title }}（{{ item.description }}）</span>
          </div>
          <div class="paper-case-list-new" v-for="(question, index) in item['questions']">
            <span>{{ index + 1 }}. {{ question['question_detail']['topic'] }}（ {{ question['marks'] }}分 ）</span>
            <el-radio-group style="margin-top: 20px"
                            v-if="question['question_detail']['type'] === 'judge'"
                            v-model="answers[question['question_detail']['id']]">
              <el-radio value="T">对</el-radio>
              <el-radio value="F">错</el-radio>
            </el-radio-group>
            <el-radio-group v-else-if="question['question_detail']['type'] === 'select'" style="margin-top: 20px" v-model="answers[question['question_detail']['id']]">
              <el-radio :value="key" v-for="key in Object.keys(question['question_detail']['options'])">
                {{ key }}. {{ question['question_detail']['options'][key] }}
              </el-radio>
            </el-radio-group>
            <div v-else-if="question['question_detail']['type'] === 'essay'" style="margin-top: 20px">
              <el-input
                  type="textarea"
                  :rows="6"
                  v-model="answers[question['question_detail']['id']]"
                  placeholder="请输入你的答案"
                  :maxlength="question['question_detail']['max_chars'] || 1000"
                  show-word-limit
              />
            </div>
          </div>
        </div>
        <div class="end-line-style" v-if="paperModuleQuestion.length !== 0">
          <span>----- 我是底线 -----</span>
        </div>
      </div>
      <div class="exam-online-other-box">
        <span class="exam-online-count-down-wording">距离考试结束还剩</span>
        <span class="exam-online-count-down">{{ countDown }}</span>
        <el-divider/>
        <div class="exam-online-overview-box">
          <div
              :class="answers[item] !== null ? 'overview-item-done' : 'overview-item-hang'"
              v-for="(item, index) in Object.keys(answers)">
            {{ index + 1 }}
          </div>
        </div>
        <div class="exam-online-submit-button">
          <el-button type="primary" style="width: 100%" :icon="Check" @click="handleSubmit">提 交</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import moment from "moment";
import { Paper, Exam, ExamResult, AIGrading} from "../../api"
import { onMounted, ref, onBeforeUnmount, watch } from 'vue'
import { MonitorCheck, CircleAlert, Check } from "lucide-vue-next";
import { ElMessage, ElMessageBox } from "element-plus";
import router from "../../router";
import {onBeforeRouteLeave, useRoute} from 'vue-router'
import { useExamOnlineCallbackStore } from '../../stores/ExamOnlineCallbackStore.ts'
import {storeToRefs} from "pinia";

// 存储考试结束时间
const examDetail = ref({})

// 查询考试详情
const getExamDetail = () => {
  const id = localStorage.getItem('EXAM_ONLINE_EXAM')
  Exam.getExamDetailByIdApi(id).then(response => {
    if (response.code !== 200) {
      ElMessage.error(response.msg)
      return
    } else {
      examDetail.value = response.data
      // 考试详情加载完成后，立即获取试卷和启动倒计时
      getCompletePaperInfo()
      if (response.data && response.data.end_time) {
        startCountdown()
        restoreDraft()
        startAutoSaveDraft()
      }
    }
  })
}

// 存储答案
const answers = ref({})

// 试卷信息，渲染页面
const paperModuleQuestion: any = ref([])

// 获取完整试卷信息
const getCompletePaperInfo = () => {
  Paper.getCompletePaperApi(examDetail.value.paper_id).then((response: any) => {
    if (response.code !== 200) {
      ElMessage.error(response.message)
      return
    }
    const tempAnswers: any = {}
    // 处理试题选项
    response.data.forEach((item: any) => {
      item.questions.forEach((element: any) => {
        if (element.question_detail.options !== 'T&F') {
          element.question_detail.options = JSON.parse(element.question_detail.options)
        }
        tempAnswers[element['question_detail']['id']] = null
      })
    })
    paperModuleQuestion.value = response.data
    // 初始化答案信息
    answers.value = tempAnswers
  })
}

// 初始化计时器
let timer = null;
// 倒计时显示
const countDown = ref("")
// 草稿自动保存定时器
let draftTimer = null;
// 计算倒计时
const calculateTimeLeft = () => {
  // 获取当前时间
  const now = new Date();
  const targetTime = moment(examDetail.value.end_time, 'YYYY-MM-DD HH:mm:ss')
  // 计算差值
  let diff = targetTime - now
  // 判断是否已经结束
  if (diff < 0) {
    console.log('------👉 倒计时结束 👈------')
    clearInterval(timer)
    // 倒计时结束，自动提交并跳转到在线考试引导页
    handleSubmitData()
    return
  }
  const hours = Math.floor(diff / 1000 / 60 / 60);  // 小时
  diff -= hours * 1000 * 60 * 60
  const minutes = Math.floor(diff / 1000 / 60)  // 分钟
  diff -= minutes * 1000 * 60;
  const seconds = Math.floor(diff / 1000)  // 秒
  // 确保格式化输出：例如 01 : 05 : 09
  countDown.value = `${String(hours).padStart(2, '0')} : ${String(minutes).padStart(2, '0')} : ${String(seconds).padStart(2, '0')}`
}

// 启动倒计时
const startCountdown = () => {
  calculateTimeLeft()  // 初次计算
  timer = setInterval(calculateTimeLeft, 1000)  // 每秒更新一次
};

onMounted(() => {
  getExamDetail()
})

onBeforeUnmount(() => {
  localStorage.removeItem('EXAM_ONLINE_EXAM')
  clearInterval(timer)
  clearInterval(draftTimer)
  // 页面卸载前保存草稿
  saveDraft()
})

const route = useRoute()

const examEndCallback = useExamOnlineCallbackStore()
const { scoreInfo } = storeToRefs(examEndCallback)
const { changeDialogVisible } = examEndCallback

// 记录是否是点击提交按钮切换页面（用于限制在答题时误触）
const is_submit_btn = ref(false)

// 提交数据
const handleSubmitData = () => {
  const endTime = moment().format('YYYY-MM-DD HH:mm:ss')
  // 组装&提交数据
  const submitData = { exam_result_id: route.params.id, answers: { ...answers.value } }
  ExamResult.createExamResultDetailApi(submitData).then(res => {
    if (res.code !== 200) {
      ElMessage.error(res.msg)
      return
    }
    // 更新考试结果数据（考试结束时间）
    ExamResult.updateExamResultApi(
        route.params.id, { end_time: endTime, result_mark: res.data.result_total_mark, ending_status: true}
    ).then(response => {
      if (response.code !== 200) {
        ElMessage.error(response.msg)
        return
      }
      ElMessage.success('提交成功！')
      // 构建考试结果相关数据，作为回调数据
      scoreInfo.value = {
        score: res.data.result_total_mark,
        actual_total: res.data.sum_marks,
        pass_mark: res.data.pass_mark,
        percentage: res.data.percentage,
        start_time: response.data.start_time,
        end_time: response.data.end_time
      }
      is_submit_btn.value = true
      router.replace('/examOnline')
      changeDialogVisible()
    })
  })
}

// 处理交卷逻辑
const handleSubmit = () => {
  ElMessageBox.confirm(
      '您确定要交卷吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '我再看看',
        type: 'warning',
        center: true
      }
  ).then(() => {
    handleSubmitData()
  }).catch(() => {
    ElMessage.info('取消交卷')
  })
}

// 监听页面路由变化，实现异常退出提示
onBeforeRouteLeave((to, from, next) => {
  const handleExit = () => {
    const endTime = moment().format('YYYY-MM-DD HH:mm:ss')
    // 更新考试结果数据（考试结束时间）
    ExamResult.updateExamResultApi(
        route.params.id, { end_time: endTime, ending_status: false }
    ).then(response => {
      if (response.code !== 200) {
        ElMessage.error(response.msg)
        return
      }
      next(); // 允许离开
    })
  };

  const cancelExit = () => {
    next(false); // 阻止离开
  };

  if (!is_submit_btn.value) {
    ElMessageBox.confirm(
        '您确定要异常退出吗？若异常退出，考试将记为0分并且无法再次参加考试，请谨慎操作！',
        '警告',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
          center: true
        }
    ).then(handleExit).catch(cancelExit);
  } else {
    next(); // 允许离开
  }
})

// 获取所有主观题的 question_id 列表
const getEssayQuestionIds = (): string[] => {
  const essayIds: string[] = []
  paperModuleQuestion.value.forEach((module: any) => {
    module.questions.forEach((question: any) => {
      if (question.question_detail.type === 'essay') {
        essayIds.push(question.question_detail.id)
      }
    })
  })
  return essayIds
}

// 草稿自动保存功能（仅保存主观题）
const saveDraft = () => {
  const examResultId = route.params.id as string
  const essayIds = getEssayQuestionIds()
  essayIds.forEach(questionId => {
    const answerText = answers.value[questionId]
    if (answerText !== null && answerText !== undefined && answerText !== '') {
      AIGrading.saveDraftApi({
        exam_result_id: examResultId,
        question_id: questionId,
        answer: answerText
      }).catch(error => {
        console.error(`草稿保存异常: question_id=${questionId}`, error)
      })
    }
  })
}

// 恢复草稿（仅恢复主观题）
const restoreDraft = () => {
  const examResultId = route.params.id as string
  const essayIds = getEssayQuestionIds()
  essayIds.forEach(questionId => {
    AIGrading.getDraftApi(examResultId, questionId).then(response => {
      if (response.code === 200 && response.data && response.data.answer) {
        answers.value[questionId] = response.data.answer
      }
    }).catch(error => {
      console.error(`草稿恢复异常: question_id=${questionId}`, error)
    })
  })
}

// 启动自动保存草稿
const startAutoSaveDraft = () => {
  draftTimer = setInterval(() => {
    saveDraft()
  }, 30000)
}

</script>

<style scoped lang="scss">
$borderRadius: 4px;

.exam-online-tips-box {
  width: 100%;
  height: 30px;
  display: flex;
  align-items: center;
  background-color: #9fceff;
  border-radius: $borderRadius;
  color: #454545;
  font-size: 13px;
}

.exam-online-operation-area {
  width: 100%;
  height: calc(100vh - 200px);
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
}

.exam-online-questions-box {
  width: calc(100% - 320px);
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow-y: auto;
  padding-bottom: 10px;

  .end-line-style {
    width: 100%;
    display: flex;
    margin-top: 20px;
    justify-content: center;
    font-size: 13px;
    color: #a4a4a4
  }
}

.exam-online-paper-module-box {
  width: 100%;
  margin-top: 20px;
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

  .paper-case-list-new {
    width: 90%;
    min-height: 70px;
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 0 8px rgba(154, 154, 154, 0.5);
    border-radius: $borderRadius;
    color: #5e5e5e;
    padding: 20px 30px;
  }
}

.exam-online-other-box {
  width: 280px;
  height: 100%;
  display: flex;
  padding: 0 10px;
  flex-direction: column;
  align-items: center;
  background-color: rgba(239, 239, 239, 0.8);
  border-radius: $borderRadius;
  backdrop-filter: blur(10px);
  color: #5e5e5e;

  .exam-online-count-down-wording {
    font-size: 18px;
    margin-top: 20px
  }

  .exam-online-count-down {
    font-size: 20px;
    margin-top: 10px;
    letter-spacing: 1px
  }

  .exam-online-submit-button {
    width: 95%;
    height: 60px;
    display: flex;
    align-items: center;
  }

  .exam-online-overview-box {
    width: 100%;
    max-height: calc(100% - 200px);
    display: flex;
    flex-wrap: wrap;
    overflow-y: auto;

    .overview-item-hang {
      width: 22px;
      height: 22px;
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 50%;
      border: 2px solid #606060;
      margin: 5px 5px
    }

    .overview-item-done {
      width: 25px;
      height: 25px;
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 50%;
      background-color: #41b883;
      color: white;
      margin: 5px 5px
    }
  }
}
</style>
