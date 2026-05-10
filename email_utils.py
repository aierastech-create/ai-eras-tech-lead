import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from dotenv import load_dotenv

load_dotenv()

def send_otp(recipient_email, otp):
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        logging.error("Email credentials not found in .env")
        return False

    subject = "Your Verification Code - Scraper App"
    body = f"""
    <html>
    <body>
        <h2>Email Verification</h2>
        <p>Hello,</p>
        <p>Thank you for signing up. Your verification code is:</p>
        <h1 style="color: #4CAF50; font-size: 32px;">{otp}</h1>
        <p>Please enter this code in the application to verify your email.</p>
        <p>If you did not request this code, please ignore this email.</p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        # Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        logging.info(f"OTP sent successfully to {recipient_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False
