"""
郵件通知系統
支援 Outlook/Exchange 和 SMTP 郵件發送
"""
import smtplib
import ssl
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime
import config.settings as settings


def send_notification(subject, message, priority="normal"):
    """
    發送郵件通知
    
    Args:
        subject: 郵件主題
        message: 郵件內容
        priority: 優先級 ("low", "normal", "high")
    """
    try:
        # 檢查是否啟用郵件通知
        if not getattr(settings, 'ENABLE_EMAIL_NOTIFICATIONS', False):
            print(f"[email] 郵件通知已關閉: {subject}")
            return False
        
        # 獲取郵件設定
        smtp_server = getattr(settings, 'EMAIL_SMTP_SERVER', '')
        smtp_port = getattr(settings, 'EMAIL_SMTP_PORT', 587)
        username = getattr(settings, 'EMAIL_USERNAME', '')
        password = getattr(settings, 'EMAIL_PASSWORD', '')
        sender_email = getattr(settings, 'EMAIL_SENDER', username)
        recipient_email = getattr(settings, 'EMAIL_RECIPIENT', '')
        use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        
        # 檢查必要設定
        if not all([smtp_server, username, password, recipient_email]):
            print("[email] 郵件設定不完整，無法發送通知")
            return False
        
        # 創建郵件
        msg = MimeMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"[Excel監控] {subject}"
        
        # 設定優先級
        if priority == "high":
            msg['X-Priority'] = '1'
            msg['X-MSMail-Priority'] = 'High'
        elif priority == "low":
            msg['X-Priority'] = '5'
            msg['X-MSMail-Priority'] = 'Low'
        
        # 郵件內容
        body = f"""
{message}

---
發送時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
系統: Excel 檔案監控系統
主機: {getattr(settings, 'COMPUTER_NAME', 'Unknown')}
        """
        
        msg.attach(MimeText(body, 'plain', 'utf-8'))
        
        # 發送郵件
        if use_tls:
            # 使用 TLS (適用於大多數現代郵件服務)
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.send_message(msg)
        else:
            # 不使用加密 (適用於內部郵件服務器)
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.login(username, password)
                server.send_message(msg)
        
        print(f"[email] 通知已發送: {subject}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("[email] 郵件認證失敗，請檢查用戶名和密碼")
        return False
    except smtplib.SMTPConnectError:
        print(f"[email] 無法連接到郵件服務器: {smtp_server}:{smtp_port}")
        return False
    except smtplib.SMTPException as e:
        print(f"[email] SMTP 錯誤: {e}")
        return False
    except Exception as e:
        print(f"[email] 發送郵件失敗: {e}")
        return False


def send_startup_notification():
    """發送程式啟動通知"""
    try:
        import socket
        hostname = socket.gethostname()
        
        subject = "程式啟動通知"
        message = f"""
Excel 檔案監控系統已成功啟動

啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
主機名稱: {hostname}
監控資料夾: {getattr(settings, 'WATCH_FOLDERS', [])}

系統已開始監控 Excel 檔案變更。
        """
        
        return send_notification(subject, message, priority="normal")
    except Exception as e:
        print(f"[email] 發送啟動通知失敗: {e}")
        return False


def send_shutdown_notification():
    """發送程式關閉通知"""
    try:
        import socket
        hostname = socket.gethostname()
        
        uptime_seconds = time.time() - getattr(settings, 'program_start_time', time.time())
        uptime_hours = uptime_seconds / 3600
        processed_files = getattr(settings, 'total_processed_files', 0)
        
        subject = "程式關閉通知"
        message = f"""
Excel 檔案監控系統已關閉

關閉時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
主機名稱: {hostname}
運行時間: {uptime_hours:.1f} 小時
處理檔案: {processed_files} 個

系統已停止監控 Excel 檔案變更。
        """
        
        return send_notification(subject, message, priority="normal")
    except Exception as e:
        print(f"[email] 發送關閉通知失敗: {e}")
        return False


def test_email_settings():
    """測試郵件設定"""
    try:
        subject = "郵件設定測試"
        message = f"""
這是一封測試郵件，用於驗證郵件設定是否正確。

如果您收到這封郵件，表示郵件通知功能已正常運作。

測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        success = send_notification(subject, message, priority="low")
        
        if success:
            print("✅ 郵件設定測試成功")
        else:
            print("❌ 郵件設定測試失敗")
        
        return success
        
    except Exception as e:
        print(f"❌ 郵件設定測試失敗: {e}")
        return False


# Outlook/Exchange 常用設定參考
OUTLOOK_SETTINGS_REFERENCE = {
    "Office 365": {
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "use_tls": True,
        "description": "Office 365 / Outlook.com"
    },
    "Exchange Online": {
        "smtp_server": "smtp.office365.com", 
        "smtp_port": 587,
        "use_tls": True,
        "description": "Exchange Online (企業版)"
    },
    "Gmail": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "description": "Gmail (需要應用程式密碼)"
    },
    "Yahoo": {
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "use_tls": True,
        "description": "Yahoo Mail"
    }
}