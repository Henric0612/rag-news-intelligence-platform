#!/usr/bin/env python3
"""
RAG News Intelligence Platform - 后端测试运行脚本

支持运行不同类型和Sprint的测试，生成覆盖率报告。

用法:
    python run_tests.py              # 运行所有测试
    python run_tests.py --unit       # 只运行单元测试
    python run_tests.py --sprint 2   # 运行Sprint 2的所有测试
    python run_tests.py --coverage   # 运行所有测试并生成覆盖率报告
    python run_tests.py --quick      # 快速测试（跳过性能测试）
"""
import subprocess
import sys
import os
import argparse
from pathlib import Path


def run_command(command, description, continue_on_error=False):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - 通过")
        return True
    else:
        print(f"❌ {description} - 失败")
        if not continue_on_error:
            return False
        return True


def check_environment():
    """检查运行环境"""
    if not os.path.exists('app.py'):
        print("❌ 错误: 请在 Backend 目录下运行此脚本")
        sys.exit(1)
    
    if not os.path.exists('tests'):
        print("❌ 错误: tests 目录不存在")
        sys.exit(1)
    
    print("✅ 环境检查通过")


def run_all_tests(with_coverage=False):
    """运行所有测试"""
    print("\n🧪 运行完整测试套件")
    print("="*60)
    
    if with_coverage:
        cmd = "python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing"
        return run_command(cmd, "所有测试（含覆盖率）")
    else:
        cmd = "python -m pytest tests/ -v --tb=short"
        return run_command(cmd, "所有测试")


def run_unit_tests():
    """运行单元测试"""
    print("\n🔬 运行单元测试")
    cmd = "python -m pytest tests/unit/ -v --tb=short"
    return run_command(cmd, "单元测试 (37个用例)")


def run_integration_tests():
    """运行集成测试"""
    print("\n🔗 运行集成测试")
    cmd = "python -m pytest tests/integration/ -v --tb=short"
    return run_command(cmd, "集成测试 (18个用例)")


def run_api_tests():
    """运行API测试"""
    print("\n🌐 运行API测试")
    cmd = "python -m pytest tests/api/ -v --tb=short"
    return run_command(cmd, "API测试 (18个用例)")


def run_e2e_tests():
    """运行E2E测试"""
    print("\n🎯 运行E2E测试")
    cmd = "python -m pytest tests/e2e/ -v --tb=short"
    return run_command(cmd, "E2E测试 (7个用例)")


def run_performance_tests():
    """运行性能测试"""
    print("\n⚡ 运行性能测试")
    cmd = "python -m pytest tests/performance/ -v --tb=short"
    return run_command(cmd, "性能测试 (6个用例)")


def run_sprint_tests(sprint_num):
    """运行指定Sprint的测试"""
    print(f"\n🏃 运行 Sprint {sprint_num} 测试")
    
    sprint_tests = {
        0: ["tests/unit/test_environment.py"],
        1: [
            "tests/unit/test_auth_service.py",
            "tests/unit/test_models.py",
            "tests/integration/test_auth_integration.py",
            "tests/api/test_auth_api.py",
            "tests/api/test_health_api.py"
        ],
        2: [
            "tests/unit/test_crawler_service.py",
            "tests/unit/test_vector_service.py",
            "tests/unit/test_search_service.py",
            "tests/unit/test_llm_service.py",
            "tests/unit/test_knowledge_service.py",
            "tests/integration/test_rag_integration.py",
            "tests/integration/test_model_integration.py",
            "tests/api/test_knowledge_api.py",
            "tests/api/test_crawler_api.py",
            "tests/api/test_search_api.py",
            "tests/api/test_rag_api.py",
            "tests/api/test_model_status_api.py",
            "tests/e2e/test_search_e2e.py",
            "tests/e2e/test_rag_qa_e2e.py"
        ],
        3: [
            "tests/unit/test_email_service.py",
            "tests/unit/test_web_search_service.py",
            "tests/unit/test_analytics_service.py",
            "tests/integration/test_email_integration.py",
            "tests/integration/test_web_search_integration.py",
            "tests/api/test_analytics_api.py",
            "tests/e2e/test_frontend_e2e.py",
            "tests/e2e/test_knowledge_e2e.py",
            "tests/e2e/test_crawler_e2e.py",
            "tests/e2e/test_analytics_e2e.py"
        ],
        4: ["tests/performance/"]
    }
    
    if sprint_num not in sprint_tests:
        print(f"❌ Sprint {sprint_num} 不存在")
        return False
    
    test_files = " ".join(sprint_tests[sprint_num])
    cmd = f"python -m pytest {test_files} -v --tb=short"
    return run_command(cmd, f"Sprint {sprint_num} 测试")


def run_quick_tests():
    """快速测试（跳过性能测试和E2E测试）"""
    print("\n⚡ 运行快速测试（单元 + 集成 + API）")
    cmd = "python -m pytest tests/unit/ tests/integration/ tests/api/ -v --tb=short"
    return run_command(cmd, "快速测试")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RAG News Intelligence Platform 后端测试运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_tests.py                 # 运行所有测试
  python run_tests.py --unit          # 只运行单元测试
  python run_tests.py --integration   # 只运行集成测试
  python run_tests.py --api           # 只运行API测试
  python run_tests.py --e2e           # 只运行E2E测试
  python run_tests.py --performance   # 只运行性能测试
  python run_tests.py --sprint 2      # 运行Sprint 2的所有测试
  python run_tests.py --coverage      # 运行所有测试并生成覆盖率报告
  python run_tests.py --quick         # 快速测试（跳过性能和E2E）
        """
    )
    
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--api', action='store_true', help='运行API测试')
    parser.add_argument('--e2e', action='store_true', help='运行E2E测试')
    parser.add_argument('--performance', action='store_true', help='运行性能测试')
    parser.add_argument('--sprint', type=int, choices=[0, 1, 2, 3, 4], help='运行指定Sprint的测试')
    parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--quick', action='store_true', help='快速测试（跳过性能和E2E）')
    
    args = parser.parse_args()
    
    # 显示标题
    print("\n" + "="*60)
    print("🧪 RAG News Intelligence Platform - 后端测试套件")
    print("="*60)
    
    # 检查环境
    check_environment()
    
    # 根据参数运行不同的测试
    success = True
    
    if args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    elif args.api:
        success = run_api_tests()
    elif args.e2e:
        success = run_e2e_tests()
    elif args.performance:
        success = run_performance_tests()
    elif args.sprint is not None:
        success = run_sprint_tests(args.sprint)
    elif args.quick:
        success = run_quick_tests()
    else:
        # 默认运行所有测试
        success = run_all_tests(with_coverage=args.coverage)
    
    # 显示结果
    print("\n" + "="*60)
    if success:
        print("✅ 测试完成！")
        if args.coverage:
            print("📊 覆盖率报告: htmlcov/index.html")
    else:
        print("❌ 测试失败！")
        sys.exit(1)
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
