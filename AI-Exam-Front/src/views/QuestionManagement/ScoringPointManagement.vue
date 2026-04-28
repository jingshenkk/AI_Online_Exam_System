<template>
  <div class="scoring-point-main-box">
    <div class="header-box">
      <div class="header-left">
        <el-button type="default" :icon="ArrowLeft" @click="handleGoBack">返回题库</el-button>
        <el-divider direction="vertical" />
        <span class="header-title">评分细则管理</span>
      </div>
      <div class="header-right" v-if="!isPublicQuestion">
        <el-button type="primary " :icon="Sparkles" @click="handleGenerateRubric" :loading="generateLoading">
          AI 生成评分细则
        </el-button>
        <el-button type="success" :icon="Plus" @click="handleOpenCreateDialog">手动添加</el-button>
        <el-button type="warning" :icon="CheckCheck" @click="handleBatchApprove" :disabled="selectedPoints.length === 0">
          批量审核通过 ({{ selectedPoints.length }})
        </el-button>
      </div>
    </div>

    <!-- 题目信息卡片 -->
    <el-card class="question-info-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span style="font-weight: bold;">题目信息</span>
        </div>
      </template>
      <div class="question-content">
        <div class="info-row">
          <span class="info-label">题目：</span>
          <span class="info-value">{{ questionInfo.topic }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">参考答案：</span>
          <span class="info-value" style="white-space: pre-wrap;">{{ questionInfo.answer }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">字数上限：</span>
          <span class="info-value">{{ questionInfo.max_chars }} 字</span>
        </div>
      </div>
    </el-card>

    <!-- AI 生成分值设置 -->
    <el-dialog
        v-model="generateDialogVisible"
        title="AI 生成评分细则"
        width="500"
        draggable
        :close-on-click-modal="false"
    >
      <el-form label-width="120px">
        <el-form-item label="该题总分">
          <el-input-number v-model="generateTotalScore" :min="1" :max="100" :step="1" />
        </el-form-item>
        <el-alert
            type="info"
            :closable="false"
            show-icon
            description="AI 将根据题目和参考答案自动拆解评分细则，生成的细则需要教师审核后才能生效。已有的未审核细则将被替换。"
            style="margin-top: 10px;"
        />
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmGenerateRubric" :loading="generateLoading">确认生成</el-button>
      </template>
    </el-dialog>

    <!-- 评分细则表格 -->
    <div class="scoring-point-table-box">
      <el-table
          :data="scoringPoints"
          border
          stripe
          style="width: 100%"
          @selection-change="handleSelectionChange"
          v-loading="tableLoading"
      >
        <el-table-column v-if="!isPublicQuestion" type="selection" width="50" :selectable="(row: any) => !row.is_approved" />
        <el-table-column label="序号" width="70" align="center">
          <template #default="scope">
            {{ scope.$index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="得分点描述" min-width="250">
          <template #default="scope">
            <span>{{ scope.row.description }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="分值" width="100" align="center">
          <template #default="scope">
            <el-tag type="primary" size="small">{{ scope.row.score }} 分</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="acceptable_expressions" label="可接受的同义表达" min-width="200">
          <template #default="scope">
            <div v-if="scope.row.acceptable_expressions && scope.row.acceptable_expressions.length > 0">
              <el-tag
                  v-for="(expr, index) in scope.row.acceptable_expressions"
                  :key="index"
                  size="small"
                  type="info"
                  style="margin: 2px 4px 2px 0;"
              >
                {{ expr }}
              </el-tag>
            </div>
            <span v-else style="color: #999;">暂无</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_approved" label="审核状态" width="120" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.is_approved ? 'success' : 'warning'" size="small">
              {{ scope.row.is_approved ? '已审核' : '待审核' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="!isPublicQuestion" label="操作" width="250" align="center" fixed="right">
          <template #default="scope">
            <el-button
                v-if="!scope.row.is_approved"
                link size="small" type="success" :icon="Check"
                @click="handleApprove(scope.row)"
            >
              审核通过
            </el-button>
            <el-divider v-if="!scope.row.is_approved" direction="vertical" />
            <el-button
                link size="small" type="warning" :icon="SquarePen"
                @click="handleOpenEditDialog(scope.row)"
            >
              编辑
            </el-button>
            <el-divider direction="vertical" />
            <el-button
                link size="small" type="danger" :icon="Trash2"
                @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div style="padding: 40px 0;">
            <el-empty :description="isPublicQuestion ? '暂无评分细则' : '暂无评分细则，请点击「AI 生成评分细则」或「手动添加」'">
              <el-button v-if="!isPublicQuestion" type="primary" :icon="Sparkles" @click="handleGenerateRubric">AI 生成</el-button>
            </el-empty>
          </div>
        </template>
      </el-table>
    </div>

    <!-- 分值汇总 -->
    <div class="score-summary" v-if="scoringPoints.length > 0">
      <span>得分点总数：<strong>{{ scoringPoints.length }}</strong></span>
      <el-divider direction="vertical" />
      <span>分值合计：<strong>{{ totalPointScore }} 分</strong></span>
      <el-divider direction="vertical" />
      <span>已审核：<strong>{{ approvedCount }}</strong> / {{ scoringPoints.length }}</span>
    </div>

    <!-- 新增/编辑评分细则对话框 -->
    <el-dialog
        v-model="editDialogVisible"
        :title="editMode === 'create' ? '新增评分细则' : '编辑评分细则'"
        width="600"
        draggable
        destroy-on-close
        :close-on-click-modal="false"
    >
      <el-form :model="editFormData" ref="editFormRef" label-width="130px">
        <el-form-item label="得分点描述" prop="description" required>
          <el-input
              v-model="editFormData.description"
              type="textarea"
              :rows="3"
              placeholder="请输入得分点描述"
          />
        </el-form-item>
        <el-form-item label="分值" prop="score" required>
          <el-input-number v-model="editFormData.score" :min="0.5" :max="100" :step="0.5" :precision="1" />
        </el-form-item>
        <el-form-item label="同义表达">
          <div style="width: 100%;">
            <div v-for="(_, index) in editFormData.acceptable_expressions" :key="index" style="display: flex; align-items: center; margin-bottom: 8px;">
              <el-input
                  v-model="editFormData.acceptable_expressions[index]"
                  placeholder="输入可接受的同义表达"
                  style="flex: 1;"
              />
              <el-button
                  link type="danger" :icon="Minus"
                  style="margin-left: 8px;"
                  @click="editFormData.acceptable_expressions.splice(index, 1)"
              />
            </div>
            <el-button link type="primary" :icon="Plus" @click="editFormData.acceptable_expressions.push('')">
              添加同义表达
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitEdit" :loading="submitLoading">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AIGrading, Questions } from '../../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Check, CheckCheck, Minus, Plus,
  Sparkles, SquarePen, Trash2
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

// 题目ID（从路由参数获取）
const questionId = ref(route.params.id as string)

// 题目信息
const questionInfo = ref<any>({
  topic: '',
  answer: '',
  type: 'essay',
  max_chars: 1000,
  grading_mode: 'LENIENT',
  trial_type: 'private'
})

// 评分细则列表
const scoringPoints = ref<any[]>([])
const tableLoading = ref(false)
const selectedPoints = ref<any[]>([])

// 计算属性
const totalPointScore = computed(() => {
  return scoringPoints.value.reduce((sum: number, point: any) => sum + (point.score || 0), 0).toFixed(1)
})
const approvedCount = computed(() => {
  return scoringPoints.value.filter((point: any) => point.is_approved).length
})
// 是否为只读模式（从公共题库页面进入时为只读）
const isPublicQuestion = computed(() => {
  return route.query.source === 'public'
})

// AI 生成相关
const generateDialogVisible = ref(false)
const generateLoading = ref(false)
const generateTotalScore = ref(10)

// 编辑相关
const editDialogVisible = ref(false)
const editMode = ref<'create' | 'edit'>('create')
const editFormRef = ref()
const submitLoading = ref(false)
const editFormData = ref({
  description: '',
  score: 1,
  acceptable_expressions: [] as string[],
  question_id: ''
})
const editingPointId = ref('')

// 获取题目信息
const fetchQuestionInfo = async () => {
  try {
    const response = await Questions.getQuestionDetailApi(questionId.value)
    if (response.code === 200) {
      questionInfo.value = response.data
    }
  } catch (error) {
    console.error('获取题目信息失败:', error)
  }
}

// 获取评分细则列表
const fetchScoringPoints = async () => {
  tableLoading.value = true
  try {
    const response = await AIGrading.getScoringPointsApi(questionId.value)
    if (response.code === 200) {
      scoringPoints.value = response.data || []
    }
  } catch (error) {
    console.error('获取评分细则失败:', error)
  } finally {
    tableLoading.value = false
  }
}

// 返回题库
const handleGoBack = () => {
  router.push('/personalWarehouse')
}

// 打开 AI 生成对话框
const handleGenerateRubric = () => {
  generateDialogVisible.value = true
}

// 确认 AI 生成
const confirmGenerateRubric = async () => {
  generateLoading.value = true
  try {
    const response = await AIGrading.generateRubricApi(questionId.value, generateTotalScore.value)
    if (response.code === 201 || response.code === 200) {
      ElMessage.success('评分细则生成成功，请审核后启用')
      generateDialogVisible.value = false
      await fetchScoringPoints()
    } else {
      ElMessage.error(response.msg || '生成失败')
    }
  } catch (error) {
    ElMessage.error('AI 生成评分细则失败，请重试')
    console.error('AI 生成失败:', error)
  } finally {
    generateLoading.value = false
  }
}

// 表格多选
const handleSelectionChange = (selection: any[]) => {
  selectedPoints.value = selection
}

// 审核通过单个
const handleApprove = async (row: any) => {
  try {
    const response = await AIGrading.approveScoringPointApi(row.id)
    if (response.code === 200) {
      ElMessage.success('审核通过')
      await fetchScoringPoints()
    } else {
      ElMessage.error(response.msg || '审核失败')
    }
  } catch (error) {
    ElMessage.error('审核操作失败')
  }
}

// 批量审核通过
const handleBatchApprove = async () => {
  const ids = selectedPoints.value.map((point: any) => point.id)
  if (ids.length === 0) return

  try {
    await ElMessageBox.confirm(
        `确定要批量审核通过 ${ids.length} 条评分细则吗？`,
        '批量审核',
        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    const response = await AIGrading.batchApproveScoringPointsApi(ids)
    if (response.code === 200) {
      ElMessage.success(response.msg || '批量审核成功')
      await fetchScoringPoints()
    } else {
      ElMessage.error(response.msg || '批量审核失败')
    }
  } catch {
    // 用户取消
  }
}

// 打开新增对话框
const handleOpenCreateDialog = () => {
  editMode.value = 'create'
  editFormData.value = {
    description: '',
    score: 1,
    acceptable_expressions: [],
    question_id: questionId.value
  }
  editDialogVisible.value = true
}

// 打开编辑对话框
const handleOpenEditDialog = (row: any) => {
  editMode.value = 'edit'
  editingPointId.value = row.id
  editFormData.value = {
    description: row.description,
    score: row.score,
    acceptable_expressions: row.acceptable_expressions ? [...row.acceptable_expressions] : [],
    question_id: questionId.value
  }
  editDialogVisible.value = true
}

// 提交编辑
const handleSubmitEdit = async () => {
  if (!editFormData.value.description) {
    ElMessage.warning('请输入得分点描述')
    return
  }
  if (!editFormData.value.score || editFormData.value.score <= 0) {
    ElMessage.warning('请输入有效的分值')
    return
  }

  // 过滤空的同义表达
  const filteredExpressions = editFormData.value.acceptable_expressions.filter((expr: string) => expr.trim() !== '')

  submitLoading.value = true
  try {
    const payload = {
      ...editFormData.value,
      acceptable_expressions: filteredExpressions
    }

    let response
    if (editMode.value === 'create') {
      response = await AIGrading.createScoringPointApi(payload)
    } else {
      response = await AIGrading.updateScoringPointApi(editingPointId.value, payload)
    }

    if (response.code === 200 || response.code === 201) {
      ElMessage.success(editMode.value === 'create' ? '创建成功' : '修改成功')
      editDialogVisible.value = false
      await fetchScoringPoints()
    } else {
      ElMessage.error(response.msg || '操作失败')
    }
  } catch (error) {
    ElMessage.error('操作失败，请重试')
  } finally {
    submitLoading.value = false
  }
}

// 删除评分细则
const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(
        `确定要删除该评分细则「${row.description}」吗？`,
        '删除确认',
        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    const response = await AIGrading.deleteScoringPointApi(row.id)
    if (response.code === 200) {
      ElMessage.success('删除成功')
      await fetchScoringPoints()
    } else {
      ElMessage.error(response.msg || '删除失败')
    }
  } catch {
    // 用户取消
  }
}

onMounted(async () => {
  await fetchQuestionInfo()
  await fetchScoringPoints()
})
</script>

<style scoped lang="scss">
.scoring-point-main-box {
  display: flex;
  flex-direction: column;
  padding: 20px;
  height: 100%;
}

.header-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  .header-left {
    display: flex;
    align-items: center;

    .header-title {
      font-size: 18px;
      font-weight: bold;
      color: #303133;
    }
  }

  .header-right {
    display: flex;
    gap: 8px;
  }
}

.question-info-card {
  margin-bottom: 16px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .question-content {
    .info-row {
      display: flex;
      margin-bottom: 8px;

      .info-label {
        font-weight: bold;
        min-width: 80px;
        color: #606266;
      }

      .info-value {
        flex: 1;
        color: #303133;
      }
    }
  }
}

.scoring-point-table-box {
  flex: 1;
  overflow: auto;
}

.score-summary {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-top: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
  color: #606266;

  strong {
    color: #409eff;
  }
}
</style>
