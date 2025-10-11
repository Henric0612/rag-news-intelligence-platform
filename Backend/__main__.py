"""
以模块模式启动 Backend 应用：python -m Backend
"""

import os
import atexit
import signal
import sys
import warnings
import logging

# ===== 警告屏蔽配置 =====
# 屏蔽第三方库的无关警告
warnings.filterwarnings('ignore', category=UserWarning, module='jieba')
warnings.filterwarnings('ignore', message='pkg_resources is deprecated')
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='transformers')

# 设置日志级别，减少第三方库的警告输出
logging.getLogger('jieba').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)

# ===== HuggingFace 离线模式配置（官方推荐） =====
# 必须在导入任何 transformers/langchain 库之前设置
# 参考: https://huggingface.co/docs/transformers/installation#offline-mode
os.environ['TRANSFORMERS_OFFLINE'] = '1'              # Transformers 离线模式
os.environ['HF_HUB_OFFLINE'] = '1'                    # HuggingFace Hub 离线模式
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'          # 禁用遥测数据收集
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'      # 禁用进度条（减少日志输出）
os.environ['HF_DATASETS_OFFLINE'] = '1'               # Datasets 离线模式（如果使用）
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'   # 禁用符号链接警告（Windows兼容）
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'  # 禁用 transformers advisory 警告


def main() -> None:
    # 与 app.py 的启动参数保持一致
    import time

    start_time = time.time()
    
    # 检测是否为reloader主进程
    is_reloader_main = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'

    # 设置环境变量
    os.environ['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'development')

    # 导入应用工厂与配置（包内导入）
    from .config import Config
    from .app import create_app, signal_handler

    # 统一数据库路径环境变量，确保多进程一致
    os.environ['DATABASE_URL'] = Config.SQLALCHEMY_DATABASE_URI

    try:
        app = create_app()
        
        # 只在主进程显示启动信息（避免重复）
        if is_reloader_main:
            startup_time = time.time() - start_time
            print("🌐 服务器启动:")
            print(f"   • 地址: http://127.0.0.1:5000")
            print(f"   • 模式: 开发模式 (自动重载已启用)")
            print(f"   • 按 Ctrl+C 停止\n")

        # 注册信号处理和退出清理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        def cleanup_on_exit():
            if not is_reloader_main:  # 只在reloader子进程显示
                print("\n👋 应用正在退出...")

        atexit.register(cleanup_on_exit)

        # 运行服务（与 app.py 保持一致的参数）
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True,
            threaded=True,
            use_debugger=True,
            reloader_interval=2,
            extra_files=None,
            exclude_patterns=['*.pyc', '__pycache__', '*.log', '*.db', 'data/*', 'venv/*']
        )
    except Exception as e:
        print(f"\n❌ 应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()


