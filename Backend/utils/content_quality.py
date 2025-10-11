"""
内容质量评估工具
"""
import re
import jieba
from typing import Dict, Any, List
from langdetect import detect, DetectorFactory

# 设置语言检测为确定性模式
DetectorFactory.seed = 0


class ContentQualityAssessor:
    """内容质量评估器"""
    
    def __init__(self):
        # 中文停用词
        self.chinese_stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'
        }
        
        # 英文停用词
        self.english_stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
    
    def assess_content_quality(self, content: str, title: str = '') -> Dict[str, Any]:
        """
        评估内容质量
        
        Args:
            content: 文本内容
            title: 标题（可选）
            
        Returns:
            Dict: 质量评估结果
        """
        if not content or not content.strip():
            return {
                'quality_score': 0,
                'quality_level': 'poor',
                'metrics': {
                    'text_length': 0,
                    'effective_words': 0,
                    'sentence_count': 0,
                    'paragraph_count': 0,
                    'information_density': 0,
                    'semantic_completeness': 0,
                    'content_value': 0
                },
                'issues': ['内容为空']
            }
        
        # 基础统计
        text_length = len(content)
        sentence_count = self._count_sentences(content)
        paragraph_count = self._count_paragraphs(content)
        
        # 语言检测
        language = self._detect_language(content)
        
        # 分词和有效词统计
        effective_words = self._count_effective_words(content, language)
        
        # 质量指标计算
        length_score = self._calculate_length_score(text_length)
        information_density = self._calculate_information_density(content, effective_words, language)
        semantic_completeness = self._calculate_semantic_completeness(content, sentence_count, paragraph_count)
        content_value = self._calculate_content_value(content, title, language)
        
        # 综合质量评分 (0-100)
        quality_score = (
            length_score * 0.1 +
            information_density * 0.3 +
            semantic_completeness * 0.3 +
            content_value * 0.3
        )
        
        # 质量等级
        quality_level = self._get_quality_level(quality_score)
        
        # 问题检测
        issues = self._detect_issues(content, text_length, effective_words, sentence_count)
        
        return {
            'quality_score': round(quality_score, 1),
            'quality_level': quality_level,
            'language': language,
            'metrics': {
                'text_length': text_length,
                'effective_words': effective_words,
                'sentence_count': sentence_count,
                'paragraph_count': paragraph_count,
                'information_density': round(information_density, 1),
                'semantic_completeness': round(semantic_completeness, 1),
                'content_value': round(content_value, 1)
            },
            'issues': issues
        }
    
    def _detect_language(self, content: str) -> str:
        """检测语言"""
        try:
            # 取前1000个字符进行检测
            sample = content[:1000] if len(content) > 1000 else content
            lang = detect(sample)
            return lang if lang in ['zh-cn', 'en'] else 'zh-cn'  # 默认中文
        except:
            return 'zh-cn'
    
    def _count_sentences(self, content: str) -> int:
        """统计句子数量"""
        # 中文句子分割
        chinese_sentences = len(re.findall(r'[。！？；]', content))
        # 英文句子分割
        english_sentences = len(re.findall(r'[.!?]', content))
        return max(chinese_sentences, english_sentences, 1)
    
    def _count_paragraphs(self, content: str) -> int:
        """统计段落数量"""
        paragraphs = content.split('\n\n')
        return len([p for p in paragraphs if p.strip()])
    
    def _count_effective_words(self, content: str, language: str) -> int:
        """统计有效词数量"""
        if language == 'zh-cn':
            # 中文分词
            words = list(jieba.cut(content))
            # 过滤停用词和单字符
            effective_words = [w for w in words if len(w) > 1 and w not in self.chinese_stopwords and w.strip()]
        else:
            # 英文分词
            words = re.findall(r'\b\w+\b', content.lower())
            effective_words = [w for w in words if w not in self.english_stopwords and len(w) > 2]
        
        return len(effective_words)
    
    def _calculate_length_score(self, text_length: int) -> float:
        """计算长度评分 (0-100)"""
        if text_length < 50:
            return 20
        elif text_length < 200:
            return 40
        elif text_length < 500:
            return 70
        elif text_length < 1000:
            return 90
        else:
            return 100
    
    def _calculate_information_density(self, content: str, effective_words: int, language: str) -> float:
        """计算信息密度 (0-100)"""
        if not content:
            return 0
        
        total_chars = len(content)
        if total_chars == 0:
            return 0
        
        # 有效词占比
        word_density = (effective_words / total_chars) * 1000 if total_chars > 0 else 0
        
        # 句子完整性
        sentences = self._count_sentences(content)
        avg_sentence_length = total_chars / sentences if sentences > 0 else 0
        
        # 信息密度评分
        if word_density > 50 and avg_sentence_length > 20:
            return 90
        elif word_density > 30 and avg_sentence_length > 15:
            return 70
        elif word_density > 20 and avg_sentence_length > 10:
            return 50
        else:
            return 30
    
    def _calculate_semantic_completeness(self, content: str, sentence_count: int, paragraph_count: int) -> float:
        """计算语义完整性 (0-100)"""
        if not content:
            return 0
        
        score = 0
        
        # 段落结构评分
        if paragraph_count > 1:
            score += 30
        elif paragraph_count == 1:
            score += 20
        
        # 标点符号分布
        punctuation_count = len(re.findall(r'[。！？，、；：]', content))
        if punctuation_count > sentence_count * 0.5:
            score += 30
        elif punctuation_count > sentence_count * 0.3:
            score += 20
        else:
            score += 10
        
        # 句子长度分布
        sentences = re.split(r'[。！？.!?]', content)
        avg_sentence_length = sum(len(s.strip()) for s in sentences if s.strip()) / len(sentences) if sentences else 0
        
        if 10 <= avg_sentence_length <= 50:
            score += 40
        elif 5 <= avg_sentence_length <= 80:
            score += 30
        else:
            score += 20
        
        return min(score, 100)
    
    def _calculate_content_value(self, content: str, title: str, language: str) -> float:
        """计算内容价值 (0-100)"""
        if not content:
            return 0
        
        score = 0
        
        # 关键词质量
        if language == 'zh-cn':
            words = list(jieba.cut(content))
            # 过滤停用词
            keywords = [w for w in words if len(w) > 1 and w not in self.chinese_stopwords]
        else:
            words = re.findall(r'\b\w+\b', content.lower())
            keywords = [w for w in words if w not in self.english_stopwords and len(w) > 2]
        
        # 关键词多样性
        unique_keywords = len(set(keywords))
        keyword_diversity = (unique_keywords / len(keywords)) * 100 if keywords else 0
        
        if keyword_diversity > 0.7:
            score += 40
        elif keyword_diversity > 0.5:
            score += 30
        else:
            score += 20
        
        # 重复度检查
        content_lower = content.lower()
        words_list = content_lower.split()
        if words_list:
            word_freq = {}
            for word in words_list:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            max_freq = max(word_freq.values())
            repetition_ratio = max_freq / len(words_list)
            
            if repetition_ratio < 0.1:
                score += 30
            elif repetition_ratio < 0.2:
                score += 20
            else:
                score += 10
        
        # 标题相关性
        if title:
            title_words = set(title.lower().split())
            content_words = set(content.lower().split())
            overlap = len(title_words.intersection(content_words))
            if overlap > 0:
                score += 30
        
        return min(score, 100)
    
    def _get_quality_level(self, quality_score: float) -> str:
        """获取质量等级"""
        if quality_score >= 80:
            return 'excellent'
        elif quality_score >= 60:
            return 'good'
        elif quality_score >= 40:
            return 'fair'
        else:
            return 'poor'
    
    def _detect_issues(self, content: str, text_length: int, effective_words: int, sentence_count: int) -> List[str]:
        """检测内容问题"""
        issues = []
        
        if text_length < 50:
            issues.append('内容过短')
        
        if effective_words < 10:
            issues.append('有效词数过少')
        
        if sentence_count < 2:
            issues.append('句子数量过少')
        
        # 检查重复内容
        words = content.split()
        if len(words) > 10:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.3:
                issues.append('内容重复度过高')
        
        # 检查特殊字符过多
        special_chars = len(re.findall(r'[^\w\s\u4e00-\u9fff]', content))
        if special_chars > text_length * 0.2:
            issues.append('特殊字符过多')
        
        return issues


def assess_content_quality(content: str, title: str = '') -> Dict[str, Any]:
    """
    便捷函数：评估内容质量
    
    Args:
        content: 文本内容
        title: 标题（可选）
        
    Returns:
        Dict: 质量评估结果
    """
    assessor = ContentQualityAssessor()
    return assessor.assess_content_quality(content, title)
