import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
# Current date for email subject and filenames
today_date = datetime.today().strftime('%Y-%m-%d')
def send_email(to_addresses, subject, body, attachments=None, username="user"):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    email_address = "omarkamalabuassaf1@gmail.com"
    email_password = os.getenv('EMAIL_PASSWORD')
    # Create the email
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = ", ".join(to_addresses)
    msg['Subject'] = subject
    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))
    # Attach files using the naming template
    today_date = datetime.today().strftime('%Y-%m-%d')
    try:
        if attachments:
            for idx, file_path in enumerate(attachments, start=1):
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as attachment:
                        # Generate a file name template dynamically
                        filename = f"tenders_{today_date}_file{idx}_{username}.xlsx"
                        # Add the file as a MIMEBase object
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        # Add header with the generated file name
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={filename}'
                        )
                        msg.attach(part)
                        print(f"Attached file: {file_path} as {filename}")
                else:
                    print(f"Attachment not found: {file_path}")
        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.sendmail(email_address, to_addresses, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
# V2
# def send_email(to_addresses, subject, body, username):
#     """
#     Sends an email with an attachment.
#     Args:
#         to_addresses (list): List of recipient email addresses.
#         subject (str): Email subject.
#         body (str): Email body text.
#         username (str): Username for personalized attachment file naming.
#     """
#     # Email server configuration
#     smtp_server = 'smtp.gmail.com'
#     smtp_port = 587
#     email_address = "omarkamalabuassaf1@gmail.com"
#     email_password = os.getenv('EMAIL_PASSWORD')
#     # Create the email
#     msg = MIMEMultipart()
#     msg['From'] = email_address
#     msg['To'] = ", ".join(to_addresses)
#     msg['Subject'] = subject
#     # Attach the email body
#     msg.attach(MIMEText(body, 'plain'))
#     # File attachment
#     filename = f'tenders_{today_date}_filtered_{username}.xlsx'
#     try:
#         if os.path.exists(filename):
#             with open(filename, 'rb') as attachment:
#                 part = MIMEBase('application', 'octet-stream')
#                 part.set_payload(attachment.read())
#                 encoders.encode_base64(part)
#                 part.add_header(
#                     'Content-Disposition',
#                     f'attachment; filename={os.path.basename(filename)}'
#                 )
#                 msg.attach(part)
#         else:
#             print(f"Attachment not found: {filename}")
#             return
#         # Send the email
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             server.starttls()
#             server.login(email_address, email_password)
#             server.sendmail(email_address, to_addresses, msg.as_string())
#         print("Email sent successfully!")
#     except Exception as e:
#         print(f"Failed to send email: {str(e)}")
