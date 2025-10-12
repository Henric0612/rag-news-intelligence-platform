/**
 * Markdown渲染工具
 * 使用markdown-it和highlight.js提供完整的Markdown渲染支持
 */

import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'

/**
 * 配置markdown-it实例
 * - html: false - 不允许直接HTML标签（安全考虑）
 * - linkify: true - 自动识别并转换URL为链接
 * - typographer: true - 启用智能引号和其他排版替换
 * - breaks: true - 将单个换行符转换为<br>
 * - highlight: 代码高亮函数
 */
export const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight: (str, lang) => {
    // 如果指定了语言且highlight.js支持，则高亮
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code class="language-${lang}">${
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
        }</code></pre>`
      } catch (err) {
        console.error('代码高亮失败:', err)
      }
    }
    
    // 否则使用纯文本
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  }
})

/**
 * 渲染Markdown内容为安全的HTML
 * @param {string} content - Markdown格式的内容
 * @returns {string} 渲染后的HTML字符串
 */
export function renderMarkdown(content) {
  if (!content) return ''
  
  try {
    // ✅ 移除 <think></think> 标签及其内容（AI内部思考过程，不显示给用户）
    let cleanedContent = content.replace(/<think>[\s\S]*?<\/think>/gi, '')
    
    // 使用markdown-it渲染
    const rendered = md.render(cleanedContent)
    
    // 使用DOMPurify清理HTML，防止XSS攻击
    return DOMPurify.sanitize(rendered, {
      ALLOWED_TAGS: [
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'em', 'u', 's', 'del',
        'a', 'img',
        'ul', 'ol', 'li',
        'blockquote',
        'code', 'pre',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'br', 'hr',
        'span', 'div'
      ],
      ALLOWED_ATTR: [
        'href', 'src', 'alt', 'title',
        'class', 'id',
        'align', 'style'
      ],
      ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp|data):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i
    })
  } catch (error) {
    console.error('Markdown渲染失败:', error)
    // 失败时返回转义的原始内容
    return DOMPurify.sanitize(content.replace(/</g, '&lt;').replace(/>/g, '&gt;'))
  }
}

/**
 * 渲染内联Markdown（不包含块级元素）
 * @param {string} content - Markdown格式的内容
 * @returns {string} 渲染后的HTML字符串
 */
export function renderInlineMarkdown(content) {
  if (!content) return ''
  
  try {
    // 使用markdown-it的renderInline方法
    const rendered = md.renderInline(content)
    
    return DOMPurify.sanitize(rendered, {
      ALLOWED_TAGS: ['strong', 'em', 'u', 's', 'code', 'a', 'span'],
      ALLOWED_ATTR: ['href', 'class']
    })
  } catch (error) {
    console.error('内联Markdown渲染失败:', error)
    return DOMPurify.sanitize(content)
  }
}

/**
 * 检测内容是否包含Markdown语法
 * @param {string} content - 待检测的内容
 * @returns {boolean} 是否包含Markdown语法
 */
export function hasMarkdownSyntax(content) {
  if (!content) return false
  
  // 检测常见的Markdown语法标记
  const markdownPatterns = [
    /\*\*[^*]+\*\*/,           // 粗体 **text**
    /\*[^*]+\*/,               // 斜体 *text*
    /`[^`]+`/,                 // 行内代码 `code`
    /```[\s\S]*?```/,          // 代码块 ```code```
    /^#{1,6}\s/m,              // 标题 # heading
    /^\s*[-*+]\s/m,            // 无序列表 - item
    /^\s*\d+\.\s/m,            // 有序列表 1. item
    /^\s*>\s/m,                // 引用 > quote
    /\[([^\]]+)\]\(([^)]+)\)/, // 链接 [text](url)
    /!\[([^\]]*)\]\(([^)]+)\)/ // 图片 ![alt](url)
  ]
  
  return markdownPatterns.some(pattern => pattern.test(content))
}

/**
 * 提取Markdown中的纯文本（移除所有格式）
 * @param {string} content - Markdown格式的内容
 * @returns {string} 纯文本内容
 */
export function extractPlainText(content) {
  if (!content) return ''
  
  try {
    // 渲染为HTML
    const html = md.render(content)
    
    // 创建临时DOM元素来提取文本
    const temp = document.createElement('div')
    temp.innerHTML = html
    
    return temp.textContent || temp.innerText || ''
  } catch (error) {
    console.error('提取纯文本失败:', error)
    return content
  }
}

/**
 * 美化Markdown代码块
 * @param {string} content - Markdown格式的内容
 * @param {string} language - 默认语言
 * @returns {string} 美化后的Markdown
 */
export function beautifyCodeBlocks(content, language = 'text') {
  if (!content) return ''
  
  // 为未指定语言的代码块添加默认语言
  return content.replace(/```\n/g, `\`\`\`${language}\n`)
}

export default {
  md,
  renderMarkdown,
  renderInlineMarkdown,
  hasMarkdownSyntax,
  extractPlainText,
  beautifyCodeBlocks
}

