"""
邮件服务
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from typing import Optional


class EmailService:
    """邮件服务类"""
    
    def __init__(self):
        self.smtp_server = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = current_app.config.get('SMTP_PORT', 587)
        self.smtp_username = current_app.config.get('SMTP_USERNAME')
        self.smtp_password = current_app.config.get('SMTP_PASSWORD')
        self.from_email = current_app.config.get('FROM_EMAIL', 'noreply@xu-news-rag.com')
        self.from_name = current_app.config.get('FROM_NAME', 'XU News AI RAG')
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML内容
            text_content: 纯文本内容
            
        Returns:
            是否发送成功
        """
        try:
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # 添加文本内容
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"发送邮件失败: {str(e)}")
            return False
    
    def send_password_reset_email(self, to_email: str, username: str, reset_token: str, reset_url: str) -> bool:
        """
        发送密码重置邮件
        
        Args:
            to_email: 收件人邮箱
            username: 用户名
            reset_token: 重置令牌
            reset_url: 重置链接
            
        Returns:
            是否发送成功
        """
        subject = "XU News AI RAG - 密码重置"
        
        # HTML内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>密码重置</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>XU News AI RAG</h1>
                <p>智能新闻问答系统</p>
            </div>
            <div class="content">
                <h2>密码重置请求</h2>
                <p>您好 {username}，</p>
                <p>我们收到了您的密码重置请求。请点击下面的按钮来重置您的密码：</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">重置密码</a>
                </p>
                <p>如果按钮无法点击，请复制以下链接到浏览器中打开：</p>
                <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px;">
                    {reset_url}
                </p>
                <p><strong>注意：</strong></p>
                <ul>
                    <li>此链接将在24小时后过期</li>
                    <li>如果您没有请求密码重置，请忽略此邮件</li>
                    <li>为了您的账户安全，请不要将重置链接分享给他人</li>
                </ul>
            </div>
            <div class="footer">
                <p>此邮件由系统自动发送，请勿回复</p>
                <p>&copy; 2025 XU News AI RAG. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        # 纯文本内容
        text_content = f"""
        XU News AI RAG - 密码重置
        
        您好 {username}，
        
        我们收到了您的密码重置请求。请访问以下链接来重置您的密码：
        
        {reset_url}
        
        注意：
        - 此链接将在24小时后过期
        - 如果您没有请求密码重置，请忽略此邮件
        - 为了您的账户安全，请不要将重置链接分享给他人
        
        此邮件由系统自动发送，请勿回复
        
        © 2025 XU News AI RAG. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_email_verification(self, to_email: str, username: str, verification_token: str, verification_url: str) -> bool:
        """
        发送邮箱验证邮件
        
        Args:
            to_email: 收件人邮箱
            username: 用户名
            verification_token: 验证令牌
            verification_url: 验证链接
            
        Returns:
            是否发送成功
        """
        subject = "XU News AI RAG - 邮箱验证"
        
        # HTML内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>邮箱验证</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>XU News AI RAG</h1>
                <p>智能新闻问答系统</p>
            </div>
            <div class="content">
                <h2>欢迎注册！</h2>
                <p>您好 {username}，</p>
                <p>感谢您注册XU News AI RAG系统。请点击下面的按钮来验证您的邮箱地址：</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">验证邮箱</a>
                </p>
                <p>如果按钮无法点击，请复制以下链接到浏览器中打开：</p>
                <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px;">
                    {verification_url}
                </p>
                <p><strong>注意：</strong></p>
                <ul>
                    <li>此链接将在24小时后过期</li>
                    <li>验证后您将可以正常使用系统功能</li>
                    <li>如果您没有注册此账户，请忽略此邮件</li>
                </ul>
            </div>
            <div class="footer">
                <p>此邮件由系统自动发送，请勿回复</p>
                <p>&copy; 2025 XU News AI RAG. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        # 纯文本内容
        text_content = f"""
        XU News AI RAG - 邮箱验证
        
        您好 {username}，
        
        感谢您注册XU News AI RAG系统。请访问以下链接来验证您的邮箱地址：
        
        {verification_url}
        
        注意：
        - 此链接将在24小时后过期
        - 验证后您将可以正常使用系统功能
        - 如果您没有注册此账户，请忽略此邮件
        
        此邮件由系统自动发送，请勿回复
        
        © 2025 XU News AI RAG. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
