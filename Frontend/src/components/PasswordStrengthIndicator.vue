<template>
  <div class="password-strength-indicator">
    <div class="strength-bar">
      <div 
        class="strength-fill" 
        :class="strengthClass"
        :style="{ width: strengthPercentage + '%' }"
      ></div>
    </div>
    <div class="strength-text" :class="strengthClass">
      {{ strengthText }}
    </div>
    <div v-if="showRequirements" class="requirements">
      <div class="requirement" :class="{ valid: requirements.length }">
        <el-icon><Check v-if="requirements.length" /><Close v-else /></el-icon>
        至少8位字符
      </div>
      <div class="requirement" :class="{ valid: requirements.lowercase }">
        <el-icon><Check v-if="requirements.lowercase" /><Close v-else /></el-icon>
        包含小写字母
      </div>
      <div class="requirement" :class="{ valid: requirements.uppercase }">
        <el-icon><Check v-if="requirements.uppercase" /><Close v-else /></el-icon>
        包含大写字母
      </div>
      <div class="requirement" :class="{ valid: requirements.number }">
        <el-icon><Check v-if="requirements.number" /><Close v-else /></el-icon>
        包含数字
      </div>
      <div class="requirement" :class="{ valid: requirements.special }">
        <el-icon><Check v-if="requirements.special" /><Close v-else /></el-icon>
        包含特殊字符
      </div>
      <div class="requirement" :class="{ valid: requirements.noRepeat }">
        <el-icon><Check v-if="requirements.noRepeat" /><Close v-else /></el-icon>
        无连续重复字符
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Check, Close } from '@element-plus/icons-vue'

const props = defineProps({
  password: {
    type: String,
    default: ''
  },
  showRequirements: {
    type: Boolean,
    default: true
  }
})

// 计算密码强度
const strengthScore = computed(() => {
  if (!props.password) return 0
  
  let score = 0
  
  // 长度分数 (0-30分)
  if (props.password.length >= 8) score += 10
  if (props.password.length >= 12) score += 10
  if (props.password.length >= 16) score += 10
  
  // 字符类型分数 (0-40分)
  if (/[a-z]/.test(props.password)) score += 10
  if (/[A-Z]/.test(props.password)) score += 10
  if (/\d/.test(props.password)) score += 10
  if (/[!@#$%^&*(),.?":{}|<>]/.test(props.password)) score += 10
  
  // 复杂度分数 (0-30分)
  if (new Set(props.password).size >= props.password.length * 0.8) score += 15
  if (!/(.)\1{2,}/.test(props.password)) score += 15
  
  return Math.min(score, 100)
})

// 强度百分比
const strengthPercentage = computed(() => {
  return strengthScore.value
})

// 强度等级
const strengthLevel = computed(() => {
  const score = strengthScore.value
  if (score < 20) return 'very-weak'
  if (score < 40) return 'weak'
  if (score < 60) return 'fair'
  if (score < 80) return 'good'
  return 'strong'
})

// 强度样式类
const strengthClass = computed(() => {
  return `strength-${strengthLevel.value}`
})

// 强度文本
const strengthText = computed(() => {
  const level = strengthLevel.value
  const texts = {
    'very-weak': '非常弱',
    'weak': '弱',
    'fair': '一般',
    'good': '良好',
    'strong': '强'
  }
  return texts[level] || '未知'
})

// 密码要求检查
const requirements = computed(() => {
  const pwd = props.password
  return {
    length: pwd.length >= 8,
    lowercase: /[a-z]/.test(pwd),
    uppercase: /[A-Z]/.test(pwd),
    number: /\d/.test(pwd),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(pwd),
    noRepeat: !/(.)\1{2,}/.test(pwd)
  }
})
</script>

<style scoped>
.password-strength-indicator {
  margin-top: 8px;
}

.strength-bar {
  width: 100%;
  height: 4px;
  background-color: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 8px;
}

.strength-fill {
  height: 100%;
  transition: all 0.3s ease;
  border-radius: 2px;
}

.strength-very-weak {
  background-color: #ff4757;
}

.strength-weak {
  background-color: #ff6b7a;
}

.strength-fair {
  background-color: #ffa502;
}

.strength-good {
  background-color: #2ed573;
}

.strength-strong {
  background-color: #1e90ff;
}

.strength-text {
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 8px;
}

.strength-text.strength-very-weak,
.strength-text.strength-weak {
  color: #ff4757;
}

.strength-text.strength-fair {
  color: #ffa502;
}

.strength-text.strength-good,
.strength-text.strength-strong {
  color: #2ed573;
}

.requirements {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  font-size: 11px;
}

.requirement {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  transition: color 0.2s ease;
}

.requirement.valid {
  color: #2ed573;
}

.requirement .el-icon {
  font-size: 12px;
}

@media (max-width: 480px) {
  .requirements {
    grid-template-columns: 1fr;
  }
}
</style>
