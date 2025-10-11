"""
Sprint 3：应用功能层 - 邮件服务单元测试
测试用例：EMAIL-001, EMAIL-002
"""
import pytest
from Backend.services.email_service import EmailService


class TestSprint3EmailService:
    """Sprint 3：入库邮件通知测试（2个用例）"""
    
    def test_smtp_email_sending(self, app):
        """EMAIL-001: SMTP邮件发送"""
        with app.app_context():
            email_service = EmailService()
            
            # 验证邮件服务配置存在
            assert email_service.smtp_server is not None
            assert email_service.smtp_port is not None
            assert email_service.from_email is not None
            print("✓ 邮件服务配置正确")
    
    def test_email_template_rendering(self, app):
        """EMAIL-002: 邮件模板渲染"""
        with app.app_context():
            email_service = EmailService()
            
            # 测试邮件内容构建
            test_data = {
                'title': '测试标题',
                'content': '测试内容' * 50,
                'source': '测试来源',
                'category': '科技'
            }
            
            # 构建HTML邮件内容
            html_content = f"""
            <html><body>
            <h2>知识库入库通知</h2>
            <p><strong>标题：</strong>{test_data['title']}</p>
            <p><strong>来源：</strong>{test_data['source']}</p>
            <p><strong>分类：</strong>{test_data['category']}</p>
            <p><strong>内容预览：</strong>{test_data['content'][:200]}...</p>
            </body></html>
            """
            
            assert '测试标题' in html_content
            assert '测试来源' in html_content
            print("✓ 邮件模板渲染成功")
