<!--
  组件名称：CreateTaskDialog
  功能描述：创建任务的弹窗表单，支持 Shell 命令和 Python 脚本两种类型
-->
<template>
  <el-dialog
    v-model="visible"
    title="创建任务"
    width="560px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
      label-position="left"
    >
      <!-- 任务名称 -->
      <el-form-item label="任务名称" prop="name">
        <el-input
          v-model="form.name"
          placeholder="请输入任务名称"
          maxlength="255"
          show-word-limit
        />
      </el-form-item>

      <!-- 任务描述 -->
      <el-form-item label="任务描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          placeholder="可选，输入任务描述"
          :rows="2"
        />
      </el-form-item>

      <!-- 任务类型 -->
      <el-form-item label="任务类型" prop="task_type">
        <el-select v-model="form.task_type" style="width: 100%">
          <el-option label="Shell 命令" value="shell_command" />
          <el-option label="Python 脚本" value="python_script" />
        </el-select>
      </el-form-item>

      <!-- 任务内容 -->
      <el-form-item label="任务内容" prop="payload">
        <el-input
          v-model="form.payload"
          type="textarea"
          :placeholder="payloadPlaceholder"
          :rows="8"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false" :disabled="submitting">取消</el-button>
      <el-button
        type="primary"
        @click="handleSubmit"
        :loading="submitting"
      >
        提交执行
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createTask, type TaskType } from '@/api/tasks'

// ===== 响应式数据 =====

const visible = defineModel<boolean>('visible', { required: true })

const emit = defineEmits<{
  created: []
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = ref({
  name: '',
  description: '',
  task_type: 'shell_command' as TaskType,
  payload: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { max: 255, message: '任务名称不超过 255 个字符', trigger: 'blur' },
  ],
  task_type: [
    { required: true, message: '请选择任务类型', trigger: 'change' },
  ],
  payload: [
    { required: true, message: '请输入任务内容', trigger: 'blur' },
  ],
}

/** 根据任务类型动态切换 placeholder */
const payloadPlaceholder = computed(() => {
  return form.value.task_type === 'shell_command'
    ? '请输入 Shell 命令，例如：\necho "Hello World"\npython3 backup.py'
    : '请输入 Python 脚本，例如：\nimport time\nprint("开始执行...")\ntime.sleep(3)\nprint("完成")'
})

// ===== 方法 =====

/** 提交表单 */
async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createTask({
      name: form.value.name,
      description: form.value.description || undefined,
      task_type: form.value.task_type,
      payload: form.value.payload,
    })
    ElMessage.success('任务已提交执行')
    visible.value = false
    emit('created')
  } catch {
    // 错误由 axios 拦截器处理
  } finally {
    submitting.value = false
  }
}

/** 关闭弹窗时重置表单 */
function handleClose() {
  formRef.value?.resetFields()
  form.value.description = ''
  form.value.payload = ''
}
</script>
