"""
关键词提取服务
使用 KeyBERT 结合 Sentence-Transformers 进行高质量关键词提取
"""
import logging
import re
from typing import List, Dict, Any, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class KeywordService:
    """关键词提取服务类"""
    
    def __init__(self):
        """初始化关键词提取服务"""
        self._keybert_model = None
        self._embedding_model = None
        
    def _get_keybert_model(self):
        """懒加载 KeyBERT 模型（单例模式）"""
        if self._keybert_model is None:
            try:
                from keybert import KeyBERT
                from sentence_transformers import SentenceTransformer
                
                logger.info("正在加载 KeyBERT 模型...")
                
                # 使用现有的嵌入模型
                self._embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                self._keybert_model = KeyBERT(model=self._embedding_model)
                
                logger.info("✅ KeyBERT 模型加载成功")
            except Exception as e:
                logger.error(f"❌ KeyBERT 模型加载失败: {str(e)}")
                raise
        
        return self._keybert_model
    
    def extract_keywords_keybert(
        self, 
        texts: List[str], 
        top_k: int = 10,
        diversity: float = 0.5,
        use_mmr: bool = True
    ) -> List[Dict[str, Any]]:
        """
        使用 KeyBERT 从文本列表中提取关键词
        
        Args:
            texts: 文本列表
            top_k: 返回前K个关键词
            diversity: 多样性参数（0-1），越大越多样化
            use_mmr: 是否使用 MMR 算法增加多样性
            
        Returns:
            关键词列表，格式: [{'keyword': str, 'score': float, 'count': int}, ...]
        """
        try:
            if not texts:
                logger.warning("输入文本为空")
                return []
            
            # 获取 KeyBERT 模型
            kw_model = self._get_keybert_model()
            
            # 合并所有文本
            combined_text = " ".join(texts)
            
            # 清洗文本
            cleaned_text = self._clean_text_for_extraction(combined_text)
            
            if not cleaned_text or len(cleaned_text) < 10:
                logger.warning("清洗后的文本过短，无法提取关键词")
                return []
            
            logger.info(f"开始提取关键词，文本长度: {len(cleaned_text)} 字符")
            
            # 使用 KeyBERT 提取关键词
            # keyphrase_ngram_range: (1, 2) 表示提取1-2个词的短语（优化：避免过长句子）
            # stop_words: 'english' 过滤英文停用词
            # use_mmr: 使用 Maximal Marginal Relevance 增加多样性
            # diversity: 多样性参数
            keywords = kw_model.extract_keywords(
                cleaned_text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                use_mmr=use_mmr,
                diversity=diversity,
                top_n=top_k * 3  # 提取更多候选词，后续过滤
            )
            
            # 过滤和处理关键词
            filtered_keywords = self._filter_and_rank_keywords(keywords, top_k)
            
            logger.info(f"✅ 成功提取 {len(filtered_keywords)} 个关键词")
            
            return filtered_keywords
            
        except Exception as e:
            logger.error(f"❌ KeyBERT 关键词提取失败: {str(e)}")
            # 降级到简单方法
            return self._fallback_keyword_extraction(texts, top_k)
    
    def _clean_text_for_extraction(self, text: str) -> str:
        """清洗文本用于关键词提取"""
        if not text:
            return ""
        
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除 URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # 移除邮箱
        text = re.sub(r'\S+@\S+', '', text)
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _filter_and_rank_keywords(
        self, 
        keywords: List[Tuple[str, float]], 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        过滤和排序关键词
        
        Args:
            keywords: KeyBERT 返回的关键词列表 [(keyword, score), ...]
            top_k: 返回前K个
            
        Returns:
            过滤后的关键词列表
        """
        # 纯编程关键字黑名单（精简版 - 只过滤明显的代码术语）
        programming_terms = {
            # HTML/CSS
            'div', 'span', 'px', 'padding', 'margin', 'border', 'width', 'height',
            'display', 'position', 'flex', 'grid', 'rgba', 'rem', 'em',
            # JavaScript/编程语法
            'var', 'const', 'let', 'function', 'return', 'import', 'export',
            'async', 'await', 'promise', 'callback', 'typeof', 'instanceof',
            'true', 'false', 'null', 'undefined', 'none', 'nil',
            # 变量命名常见词
            'obj', 'arr', 'str', 'num', 'bool', 'idx', 'tmp', 'temp', 'val',
            'params', 'args', 'props', 'attrs', 'opts', 'cfg',
            # 测试相关
            'test', 'mock', 'expect', 'assert', 'describe', 'it',
            # 常见代码片段
            'console', 'log', 'debug', 'print', 'echo', 'printf',
            'getElementById', 'querySelector', 'addEventListener',
            # 文件路径/系统
            'src', 'dist', 'build', 'node_modules', 'package',
            # 数据库/API常见
            'id', 'uuid', 'timestamp', 'created', 'updated', 'deleted',
            'get', 'set', 'post', 'put', 'delete', 'patch',
            'api', 'rest', 'graphql', 'endpoint', 'webhook',
            'demo', 'example', 'sample', 'tutorial', 'guide',
            # 框架特定
            'vue', 'react', 'angular', 'component', 'directive', 'hook',
            'router', 'store', 'vuex', 'redux', 'state', 'action', 'mutation',
            # 其他代码术语
            'index', 'key', 'value', 'item', 'element', 'node', 'child', 'parent',
            'prev', 'next', 'first', 'last', 'length', 'size', 'count',
            'isvisible', 'isenabled', 'isactive', 'hasclass', 'setstate',
            'getdata', 'setdata', 'onclick', 'onchange', 'oninput',
            'formvalue', 'inputvalue', 'selectvalue', 'checkvalue',
            'tocamelcase', 'topascalcase', 'tosnakecase', 'tokebabcase',
            'parseint', 'parsefloat', 'tostring', 'tojson', 'frobjson',
            'results', 'result', 'response', 'request', 'payload', 'body'
        }
        
        # 无意义词汇
        meaningless_words = {
            'the', 'and', 'or', 'but', 'for', 'with', 'from', 'this', 'that',
            '的', '了', '和', '是', '在', '有', '个', '为', '与', '及', '等',
            '可以', '需要', '使用', '进行', '通过', '实现', '提供', '支持'
        }
        
        # 新闻常用句式（过滤掉这些描述性短语）
        news_phrases = {
            '公开资料显示', '资料显示', '报道称', '据报道', '消息称', '据悉',
            '据了解', '据介绍', '据统计', '据分析', '有关人士', '知情人士',
            '央视新闻', '新闻报道', '媒体报道', '官方消息', '权威消息',
            '据央视', '据新华社', '据人民日报', '新闻联播', '晚间新闻',
            '新华社', '曾报道', '早前',  # 新闻机构和时间词
            '今日消息', '最新消息', '刚刚消息', '突发消息', '独家消息',
            '的文章', '之前的文章', '上述文章', '前文', '本文',
            '年月日', '今天', '昨天', '明天', '近日', '日前', '目前',
            '实施出口管制', '并对', '关键软件', '软件实施',  # 这些是句子片段
            '长期盘踞', '一人为', '其中一人', '三人', '首要分子',  # 句子片段
            '缅甸北部', '被捕', '武装', '护诈', '犯罪集团',  # 新闻事件细节
            '下同', '如下', '上述', '以上', '以下',  # 文章结构词
            '通告称', '声明称', '表示', '负责人表示', '官方表示',  # 引述语
            '长期以来', '一直以来', '近年来', '近期', '当前',  # 时间描述
            '共同推进', '深入开展', '积极推动', '全面落实',  # 政府工作术语
            '消除', '提出', '倡议', '合作', '贸易壁垒',  # 通用动词/名词
            '此外', '另外', '同时', '并且', '以及', '或者',  # 连接词
            '交流', '意见建议', '反映', '当地居民', '有关部门'  # 通用短语
        }
        
        filtered = []
        seen_keywords = set()
        
        for keyword, score in keywords:
            # 转换为小写用于比较
            keyword_lower = keyword.lower().strip()
            
            # 跳过空关键词
            if not keyword_lower:
                continue
            
            # 强制限制：跳过过长的关键词（超过10个字符的可能是句子）
            # 中文：2-6个字，避免单字和长句
            if len(keyword_lower) > 10:  # 更严格的长度限制
                continue
            
            # 优先选择：必须包含中文（避免纯英文编程术语）
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', keyword_lower))
            if not has_chinese:
                # 允许少量高质量英文术语（如"AI"、"5G"等），但要非常短
                if len(keyword_lower) > 4:
                    continue
            
            # 跳过过短的关键词（少于2个字符）
            if len(keyword_lower) < 2:
                continue
            
            # 跳过纯数字
            if keyword_lower.isdigit():
                continue
            
            # 跳过编程术语（仅当关键词全为英文时才应用此过滤）
            if keyword_lower.isascii() and keyword_lower in programming_terms:
                continue
            
            # 跳过无意义词汇
            if keyword_lower in meaningless_words:
                continue
            
            # 跳过新闻常用句式（使用包含匹配）
            if any(phrase in keyword_lower for phrase in news_phrases):
                continue
            
            # 跳过包含日期的短语（如"2025年10月3日"）
            if re.search(r'\d{4}年\d{1,2}月\d{1,2}日', keyword):
                continue
            
            # 跳过纯数字或包含大量数字的短语
            digit_ratio = sum(c.isdigit() for c in keyword) / len(keyword) if len(keyword) > 0 else 0
            if digit_ratio > 0.2:  # 更严格：如果超过20%是数字，跳过
                continue
            
            # 跳过包含特殊字符的关键词（但允许中文、英文、数字、空格、连字符）
            if not re.match(r'^[\u4e00-\u9fff\w\s\-]+$', keyword):
                continue
            
            # 跳过重复关键词
            if keyword_lower in seen_keywords:
                continue
            
            # 跳过相似关键词（简单的包含关系检查）
            is_duplicate = False
            for existing in seen_keywords:
                if keyword_lower in existing or existing in keyword_lower:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # 添加到结果
            seen_keywords.add(keyword_lower)
            # 给中文关键词额外加分，使其优先排序
            adjusted_score = float(score) * 1.5 if has_chinese else float(score)
            filtered.append({
                'keyword': keyword,
                'score': adjusted_score,
                'count': 1  # KeyBERT 不统计频次，设为1
            })
            
            # 达到目标数量则停止
            if len(filtered) >= top_k:
                break
        
        logger.info(f"过滤后保留 {len(filtered)} 个关键词（原始: {len(keywords)} 个）")
        
        return filtered
    
    def _fallback_keyword_extraction(
        self, 
        texts: List[str], 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        降级方案：使用简单的频次统计
        当 KeyBERT 不可用时使用
        """
        logger.warning("使用降级方案进行关键词提取")
        
        try:
            from Backend.utils.text_utils import extract_keywords
            
            all_keywords = []
            for text in texts:
                keywords = extract_keywords(text, top_k=20)
                all_keywords.extend(keywords)
            
            # 统计频次
            keyword_freq = Counter(all_keywords)
            top_keywords = keyword_freq.most_common(top_k)
            
            return [
                {
                    'keyword': keyword,
                    'score': count / len(all_keywords) if all_keywords else 0,
                    'count': count
                }
                for keyword, count in top_keywords
            ]
        except Exception as e:
            logger.error(f"降级方案也失败: {str(e)}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 尝试加载模型
            self._get_keybert_model()
            return {
                'status': 'healthy',
                'service': 'keyword_extraction',
                'model': 'KeyBERT + all-MiniLM-L6-v2'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'keyword_extraction',
                'error': str(e)
            }


# 全局关键词服务实例
_keyword_service = None


def get_keyword_service() -> KeywordService:
    """获取关键词服务实例（单例模式）"""
    global _keyword_service
    if _keyword_service is None:
        _keyword_service = KeywordService()
    return _keyword_service

