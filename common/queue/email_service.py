import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings


class EmailConfigurationError(RuntimeError):
    pass


class EmailService:
    @staticmethod
    def validate_configuration():
        required = {
            "SMTP_HOST": settings.SMTP_HOST,
            "SMTP_USER": settings.SMTP_USER,
            "SMTP_PASS": settings.SMTP_PASS,
            "SMTP_FROM": settings.SMTP_FROM,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise EmailConfigurationError(f"Missing required SMTP settings: {', '.join(missing)}")

    @staticmethod
    def send_welcome_email(*, to: str, display_name: str, user_id: str):
        EmailService.validate_configuration()
        safe_name = display_name or to
        login_url = "http://localhost:8000/api/docs/"

        text_body = (
            f"Здравствуйте, {safe_name}!\n\n"
            "Вы успешно зарегистрировались в Lab Project API.\n"
            f"ID вашего аккаунта: {user_id}\n"
            f"Войти и проверить API можно здесь: {login_url}\n"
        )
        html_body = f"""
        <html>
          <body>
            <h2>Здравствуйте, {safe_name}!</h2>
            <p>Вы успешно зарегистрировались в <strong>Lab Project API</strong>.</p>
            <p>ID вашего аккаунта: <code>{user_id}</code></p>
            <p><a href="{login_url}">Перейти к API-документации</a></p>
          </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Добро пожаловать в Lab Project API"
        message["From"] = settings.SMTP_FROM
        message["To"] = to
        message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        if settings.SMTP_SECURE:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
                smtp.send_message(message)


email_service = EmailService()
