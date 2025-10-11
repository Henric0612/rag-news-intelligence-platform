"""
Markdown转换工具
提供HTML到Markdown的转换功能
"""
import html2text
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def html_to_markdown(html_content: str, base_url: str = None) -> str:
    """
    将HTML转换为Markdown格式
    
    Args:
        html_content: HTML内容
        base_url: 基础URL，用于相对链接转换
        
    Returns:
        str: Markdown格式的内容
    """
    try:
        # 先用BeautifulSoup清理HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'iframe', 'noscript', 'svg', 'canvas']):
            tag.decompose()
        
        # 配置html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.body_width = 0  # 不自动换行
        h.unicode_snob = True  # 使用Unicode字符
        h.ignore_tables = False
        h.skip_internal_links = False
        h.inline_links = True  # 使用内联链接而不是引用式
        h.mark_code = True  # 标记代码块
        
        if base_url:
            h.baseurl = base_url
        
        # 转换为Markdown
        markdown = h.handle(str(soup))
        
        # 清理多余空行（超过2个连续换行的压缩为2个）
        import re
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        return markdown.strip()
    except Exception as e:
        logger.error(f"HTML转Markdown失败: {str(e)}")
        return ""


def content_to_markdown(content: str, source_url: str = None) -> str:
    """
    将纯文本或HTML内容转换为Markdown
    
    Args:
        content: 内容文本
        source_url: 来源URL
        
    Returns:
        str: Markdown格式的内容
    """
    if not content:
        return ""
    
    try:
        # 如果内容看起来像HTML，先解析
        if '<' in content and '>' in content:
            soup = BeautifulSoup(content, 'html.parser')
            # 清理脚本和样式
            for tag in soup(['script', 'style', 'iframe', 'noscript']):
                tag.decompose()
            html_content = str(soup)
            return html_to_markdown(html_content, source_url)
        else:
            # 纯文本智能格式化为Markdown
            return _format_plain_text_to_markdown(content)
    except Exception as e:
        logger.error(f"内容转Markdown失败: {str(e)}")
        return content  # 转换失败时返回原内容


def _format_plain_text_to_markdown(text: str) -> str:
    """
    将纯文本智能格式化为Markdown
    识别段落、标题、列表等结构
    """
    import re
    
    lines = text.split('\n')
    formatted_lines = []
    in_code_block = False
    prev_line_empty = True
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 空行保持
        if not stripped:
            if not prev_line_empty:  # 避免连续多个空行
                formatted_lines.append('')
                prev_line_empty = True
            continue
        
        prev_line_empty = False
        
        # 检测代码块标记（如果有）
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            formatted_lines.append(line)
            continue
        
        # 在代码块内，保持原样
        if in_code_block:
            formatted_lines.append(line)
            continue
        
        # 检测可能的标题（短行，后面跟空行或内容行）
        # 标题特征：1. 长度<50字符 2. 不以标点结尾 3. 后面是空行或新段落
        is_potential_title = (
            len(stripped) < 50 and
            not stripped.endswith(('。', '，', ',', '.', '、', '；', ';')) and
            (i == 0 or (i > 0 and not lines[i-1].strip()))  # 前面是空行或是第一行
        )
        
        if is_potential_title:
            # 根据位置判断标题级别
            if i == 0:
                formatted_lines.append(f'# {stripped}')  # 第一行作为一级标题
            else:
                formatted_lines.append(f'## {stripped}')  # 其他作为二级标题
            continue
        
        # 检测列表（以数字+点/圆点/短横线开头）
        if re.match(r'^[\d\-\*\•]\s', stripped):
            if not stripped.startswith('-'):
                formatted_lines.append(f'- {stripped}')
            else:
                formatted_lines.append(stripped)
            continue
        
        # 检测可能的代码行（包含大量技术符号）
        tech_symbols = ['()', '{}', '[]', '=>', '->', '<', '>', 'const', 'function', 'export', 'import']
        if any(symbol in stripped for symbol in tech_symbols) and len(stripped) > 20:
            # 如果前一行不是代码，开始代码块
            if not formatted_lines or not formatted_lines[-1].startswith('    '):
                formatted_lines.append('')
            formatted_lines.append(f'    {stripped}')  # 4空格缩进表示代码
            continue
        
        # 普通段落
        formatted_lines.append(stripped)
    
    # 合并结果
    result = '\n'.join(formatted_lines)
    
    # 清理多余空行（超过2个连续换行压缩为2个）
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()

