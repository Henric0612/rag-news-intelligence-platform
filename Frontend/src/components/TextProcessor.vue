<template>
  <div class="text-processor">
    <div v-if="processedContent" v-html="processedContent"></div>
    <div v-else class="empty-content">暂无内容</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import DOMPurify from 'dompurify'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  // 是否启用智能分段
  enableSmartParagraph: {
    type: Boolean,
    default: true
  },
  // 是否启用文本美化
  enableTextBeautify: {
    type: Boolean,
    default: true
  }
})

// 智能分段规则
const paragraphRules = [
  // 句号、问号、感叹号后分段
  { pattern: /([。！？])\s*/g, replacement: '$1\n\n' },
  // 中文句号后分段
  { pattern: /([。])\s*/g, replacement: '$1\n\n' },
  // 英文句号后分段（排除小数点）
  { pattern: /([.!?])\s+(?![0-9])/g, replacement: '$1\n\n' },
  // 分号后分段
  { pattern: /([;；])\s*/g, replacement: '$1\n\n' },
  // 冒号后分段（特定情况）
  { pattern: /([:：])\s*(?=[A-Z\u4e00-\u9fa5])/g, replacement: '$1\n\n' },
  // 多个连续换行合并为两个
  { pattern: /\n{3,}/g, replacement: '\n\n' }
]

// 文本美化规则
const beautifyRules = [
  // 移除多余空格
  { pattern: /\s+/g, replacement: ' ' },
  // 中文标点符号标准化
  { pattern: /，/g, replacement: '，' },
  { pattern: /。/g, replacement: '。' },
  { pattern: /！/g, replacement: '！' },
  { pattern: /？/g, replacement: '？' },
  // 数字和单位之间添加空格
  { pattern: /(\d+)([年月日时分秒])/g, replacement: '$1 $2' },
  // 英文和中文之间添加空格
  { pattern: /([a-zA-Z])([\u4e00-\u9fa5])/g, replacement: '$1 $2' },
  { pattern: /([\u4e00-\u9fa5])([a-zA-Z])/g, replacement: '$1 $2' }
]

// 处理文本内容
const processedContent = computed(() => {
  if (!props.content) return ''
  
  let processed = props.content.trim()
  
  // 应用文本美化规则
  if (props.enableTextBeautify) {
    beautifyRules.forEach(rule => {
      processed = processed.replace(rule.pattern, rule.replacement)
    })
  }
  
  // 应用智能分段规则
  if (props.enableSmartParagraph) {
    paragraphRules.forEach(rule => {
      processed = processed.replace(rule.pattern, rule.replacement)
    })
    
    // 按段落分割并处理
    const paragraphs = processed.split('\n\n').filter(p => p.trim())
    
    // 生成HTML段落
    const htmlParagraphs = paragraphs.map(paragraph => {
      const trimmed = paragraph.trim()
      if (!trimmed) return ''
      
      // 检测是否为标题（短文本且以特定字符结尾）
      if (trimmed.length < 50 && /[：:]$/.test(trimmed)) {
        return `<h4 class="content-subtitle">${trimmed}</h4>`
      }
      
      // 检测是否为列表项
      if (/^[•·▪▫‣⁃]\s/.test(trimmed) || /^\d+[\.\)]\s/.test(trimmed)) {
        return `<div class="content-list-item">${trimmed}</div>`
      }
      
      // 普通段落
      return `<p class="content-paragraph">${trimmed}</p>`
    }).filter(p => p)
    
    processed = htmlParagraphs.join('')
  } else {
    // 简单换行处理
    processed = processed.replace(/\n/g, '<br>')
    processed = `<p class="content-paragraph">${processed}</p>`
  }
  
  // 安全清理HTML
  return DOMPurify.sanitize(processed, {
    ALLOWED_TAGS: ['p', 'h4', 'div', 'br', 'strong', 'em', 'span'],
    ALLOWED_ATTR: ['class']
  })
})
</script>

<style scoped>
.text-processor {
  line-height: 1.8;
  color: var(--text-primary);
  font-size: 14px;
}

.text-processor :deep(.content-paragraph) {
  margin-bottom: 1.2em;
  text-indent: 2em;
  line-height: 1.8;
  color: var(--text-primary);
  word-wrap: break-word;
  word-break: break-all;
}

.text-processor :deep(.content-subtitle) {
  margin: 1.5em 0 0.8em 0;
  font-size: 1.1em;
  font-weight: 600;
  color: var(--text-primary);
  border-left: 3px solid var(--primary-color);
  padding-left: 12px;
  text-indent: 0;
}

.text-processor :deep(.content-list-item) {
  margin-bottom: 0.8em;
  padding-left: 1.5em;
  position: relative;
  line-height: 1.6;
  color: var(--text-secondary);
}

.text-processor :deep(.content-list-item::before) {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--primary-color);
  font-weight: bold;
}

.empty-content {
  color: var(--text-placeholder);
  font-style: italic;
  text-align: center;
  padding: 2em;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .text-processor :deep(.content-paragraph) {
    text-indent: 1em;
    font-size: 13px;
  }
  
  .text-processor :deep(.content-subtitle) {
    font-size: 1em;
    padding-left: 8px;
  }
}

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .text-processor :deep(.content-paragraph) {
    color: var(--text-primary-dark);
  }
  
  .text-processor :deep(.content-subtitle) {
    color: var(--text-primary-dark);
    border-left-color: var(--primary-color-dark);
  }
  
  .text-processor :deep(.content-list-item) {
    color: var(--text-secondary-dark);
  }
  
  .text-processor :deep(.content-list-item::before) {
    color: var(--primary-color-dark);
  }
}
</style>
