"""
文本处理工具类
"""
import re
import hashlib
from typing import Tuple, List


def clean_text(text):
    """清洗文本"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除特殊字符但保留中文、英文、数字和基本标点
    text = re.sub(r'[^\w\s\u4e00-\u9fff,。!?;:，。！？；：]', '', text)
    
    return text.strip()


def generate_content_hash(content):
    """生成内容哈希"""
    if not content:
        return None
    
    # 使用MD5生成内容哈希
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def validate_email_format(email: str) -> Tuple[bool, str]:
    """
    验证邮箱格式
    
    Args:
        email: 邮箱字符串
        
    Returns:
        (是否通过验证, 错误信息)
    """
    if not email:
        return False, "邮箱不能为空"
    
    # 基本格式验证
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "邮箱格式不正确"
    
    # 长度验证
    if len(email) > 254:  # RFC 5321
        return False, "邮箱长度不能超过254个字符"
    
    # 本地部分和域名部分验证
    try:
        local, domain = email.rsplit('@', 1)
        
        # 本地部分长度验证
        if len(local) > 64:
            return False, "邮箱用户名部分过长"
        
        # 域名部分验证
        if len(domain) < 3:
            return False, "邮箱域名过短"
        
        # 检查是否有连续的点
        if '..' in email:
            return False, "邮箱格式不正确"
        
        # 检查开头和结尾
        if local.startswith('.') or local.endswith('.'):
            return False, "邮箱格式不正确"
        
    except ValueError:
        return False, "邮箱格式不正确"
    
    return True, "邮箱格式正确"


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    验证密码强度
    
    Args:
        password: 密码字符串
        
    Returns:
        (是否通过验证, 错误信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8位"
    
    if len(password) > 128:
        return False, "密码长度不能超过128位"
    
    # 检查是否包含小写字母
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含小写字母"
    
    # 检查是否包含大写字母
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含大写字母"
    
    # 检查是否包含数字
    if not re.search(r'\d', password):
        return False, "密码必须包含数字"
    
    # 检查是否包含特殊字符
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含特殊字符"
    
    # 检查是否包含常见弱密码模式
    weak_patterns = [
        r'123456',
        r'password',
        r'qwerty',
        r'admin',
        r'letmein',
        r'welcome',
        r'monkey',
        r'dragon',
        r'master',
        r'hello'
    ]
    
    password_lower = password.lower()
    for pattern in weak_patterns:
        if re.search(pattern, password_lower):
            return False, "密码不能包含常见弱密码模式"
    
    # 检查是否包含重复字符（连续3个或以上相同字符）
    if re.search(r'(.)\1{2,}', password):
        return False, "密码不能包含连续3个或以上相同字符"
    
    return True, "密码强度符合要求"


def calculate_password_strength(password: str) -> int:
    """
    计算密码强度分数 (0-100)
    
    Args:
        password: 密码字符串
        
    Returns:
        密码强度分数
    """
    score = 0
    
    # 长度分数 (0-30分)
    if len(password) >= 8:
        score += 10
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10
    
    # 字符类型分数 (0-40分)
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'\d', password):
        score += 10
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 10
    
    # 复杂度分数 (0-30分)
    if len(set(password)) >= len(password) * 0.8:  # 字符重复度低
        score += 15
    if not re.search(r'(.)\1{2,}', password):  # 无连续重复字符
        score += 15
    
    return min(score, 100)


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """从文本中提取关键词（轻量实现）
    - 仅使用正则与简单频次统计，避免额外依赖
    - 适配中英文：按中文字符窗口与英文单词分词的混合策略
    - 过滤编程关键字和技术术语
    """
    if not text:
        return []

    # 统一清洗
    normalized = clean_text(text)

    # 英文/数字 token 提取
    english_tokens = re.findall(r"[A-Za-z][A-Za-z\-']+|\d+", normalized)

    # 中文分片（连续中文当作词片段）
    chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", normalized)

    tokens = [t.lower() for t in english_tokens] + chinese_tokens

    # 停用词（中英混合，精简版）+ 编程关键字
    stopwords = set([
        # 英文常用停用词
        'the','is','are','and','or','of','to','in','on','for','with','a','an','by','as','at','from','that','this','it','be','was','were','will','would','can','could','should','has','have','had','not','no','but','if','about','into','than','then','so','such','its','their','them','they','we','you','i','my','your','his','her','our','me','him','us','do','does','did','doing','done',
        # 中文常用停用词
        '的','了','和','与','及','等','中','对','在','为','于','是','有','也','并','或','及其','以及','通过','根据','同时','进行','相关','包括','这个','那个','一个','什么','怎么','如何','可以','需要','使用','实现','提供','支持','功能','方法','系统','应用','服务','数据','信息','内容','文件','代码','项目','开发','技术','工具','平台','框架','模块','组件','接口','配置','管理','操作','处理','设置','显示','获取','创建','更新','删除','查询','添加','修改','保存','加载','执行','运行','启动','关闭','打开','编辑','选择','点击','输入','输出',
        # 编程关键字（JavaScript/TypeScript/Python/Java等）
        'const','let','var','function','class','interface','type','enum','import','export','from','default','return','if','else','elif','for','while','do','switch','case','break','continue','try','catch','finally','throw','async','await','yield','new','this','super','extends','implements','public','private','protected','static','void','int','string','boolean','bool','float','double','long','short','char','byte','true','false','null','undefined','none','self','def','lambda','pass','raise','assert','with','global','nonlocal','del','exec','print','len','range','list','dict','set','tuple','str','repr','isinstance','hasattr','getattr','setattr','property','classmethod','staticmethod',
        # 常见技术术语
        'api','url','http','https','html','css','js','ts','jsx','tsx','vue','react','angular','node','npm','yarn','webpack','vite','babel','eslint','prettier','git','github','gitlab','docker','kubernetes','redis','mysql','mongodb','postgresql','nginx','apache','linux','windows','mac','ios','android','app','web','mobile','frontend','backend','fullstack','database','server','client','request','response','json','xml','rest','graphql','websocket','oauth','jwt','token','session','cookie','cache','log','debug','test','unit','integration','e2e','ci','cd','deploy','build','dev','prod','staging','localhost','port','host','domain','ssl','tls','cors','csrf','xss','sql','nosql','orm','mvc','mvvm','spa','ssr','ssg','pwa','seo','ui','ux','design','layout','component','element','div','span','button','input','form','table','list','item','container','wrapper','header','footer','nav','menu','sidebar','modal','dialog','popup','tooltip','dropdown','select','checkbox','radio','slider','progress','loading','spinner','icon','image','video','audio','file','upload','download','search','filter','sort','pagination','scroll','drag','drop','click','hover','focus','blur','change','submit','reset','validate','error','warning','success','info','message','notification','alert','confirm','prompt'
    ])

    # 过滤停用词、过短token、纯数字、编程关键字
    filtered = []
    for t in tokens:
        # 跳过长度<=1的token
        if len(t) <= 1:
            continue
        # 跳过停用词
        if t in stopwords:
            continue
        # 跳过纯数字
        if t.isdigit():
            continue
        # 跳过常见的版本号模式（如v1, v2, v38等）
        if re.match(r'^v\d+$', t):
            continue
        # 跳过单个字母
        if len(t) == 1:
            continue
        filtered.append(t)
    
    if not filtered:
        return []

    # 频次统计
    freq: dict[str, int] = {}
    for token in filtered:
        freq[token] = freq.get(token, 0) + 1

    # 按频次与长度综合排序（频次优先，长度次之）
    # 优先选择中文词汇（通常更有意义）
    def sort_key(item):
        word, count = item
        is_chinese = bool(re.search(r'[\u4e00-\u9fff]', word))
        return (count, is_chinese, len(word))
    
    ranked = sorted(freq.items(), key=sort_key, reverse=True)

    return [w for w, _ in ranked[:top_k]]
