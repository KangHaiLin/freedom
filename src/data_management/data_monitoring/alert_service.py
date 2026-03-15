"""
告警服务
支持多种告警渠道，负责告警消息的格式化和发送
"""
from typing import List, Dict, Optional, Any
import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import logging
from datetime import datetime

from .base_monitor import MonitorResult, AlertLevel
from common.config import settings
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class AlertService:
    """告警服务"""

    def __init__(self, config: Dict = None):
        self.config = config or settings.ALERT_CONFIG
        self.enabled = self.config.get('enabled', True)
        self.default_channels = self.config.get('default_channels', ['log'])
        self.channel_configs = self.config.get('channels', {})
        self.alert_template = self.config.get('template', """
【{level}告警】{monitor_name}
时间：{timestamp}
状态：{status}
消息：{message}
指标：{metrics}
详细信息：{details}
        """)

    def send_alert(
        self,
        result: MonitorResult,
        channels: Optional[List[str]] = None,
        receiver: Optional[List[str]] = None
    ) -> bool:
        """
        发送告警
        Args:
            result: 监控结果
            channels: 告警渠道，为空则使用默认渠道
            receiver: 接收人列表，为空则使用默认接收人
        Returns:
            是否发送成功
        """
        if not self.enabled or not result.need_alert():
            return False

        channels = channels or self.default_channels
        success = True

        for channel in channels:
            try:
                if channel == 'log':
                    self._send_log_alert(result)
                elif channel == 'email':
                    self._send_email_alert(result, receiver)
                elif channel == 'wecom':
                    self._send_wecom_alert(result, receiver)
                elif channel == 'dingtalk':
                    self._send_dingtalk_alert(result, receiver)
                elif channel == 'webhook':
                    self._send_webhook_alert(result)
                else:
                    logger.warning(f"不支持的告警渠道：{channel}")
                    success = False
            except Exception as e:
                logger.error(f"发送{channel}告警失败：{e}")
                success = False

        return success

    def _format_alert_message(self, result: MonitorResult) -> str:
        """格式化告警消息"""
        status_str = "正常" if result.success else "异常"
        level_str = {
            AlertLevel.INFO: "信息",
            AlertLevel.WARNING: "警告",
            AlertLevel.ERROR: "错误",
            AlertLevel.CRITICAL: "严重"
        }.get(result.level, "未知")

        return self.alert_template.format(
            level=level_str,
            monitor_name=result.monitor_name,
            timestamp=DateTimeUtils.to_str(result.timestamp),
            status=status_str,
            message=result.message,
            metrics=json.dumps(result.metrics, ensure_ascii=False, indent=2),
            details=json.dumps(result.details, ensure_ascii=False, indent=2)
        )

    def _send_log_alert(self, result: MonitorResult):
        """发送日志告警"""
        message = self._format_alert_message(result)
        logger.warning(f"告警通知：\n{message}")

    def _send_email_alert(self, result: MonitorResult, receiver: Optional[List[str]] = None):
        """发送邮件告警"""
        email_config = self.channel_configs.get('email', {})
        if not email_config:
            logger.warning("邮件告警未配置")
            raise ValueError("邮件告警未配置")

        smtp_server = email_config.get('smtp_server')
        smtp_port = email_config.get('smtp_port', 465)
        smtp_user = email_config.get('smtp_user')
        smtp_password = email_config.get('smtp_password')
        sender = email_config.get('sender', smtp_user)
        receivers = receiver or email_config.get('receivers', [])

        if not all([smtp_server, smtp_user, smtp_password, receivers]):
            logger.warning("邮件告警配置不完整")
            raise ValueError("邮件告警配置不完整")

        # 构建邮件
        message = self._format_alert_message(result)
        msg = MIMEText(message, 'plain', 'utf-8')
        msg['From'] = Header(f"量化交易系统监控 <{sender}>", 'utf-8')
        msg['To'] = Header(','.join(receivers), 'utf-8')
        subject = f"【{result.level.name.upper()}】{result.monitor_name}告警"
        msg['Subject'] = Header(subject, 'utf-8')

        # 发送邮件
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()

            server.login(smtp_user, smtp_password)
            server.sendmail(sender, receivers, msg.as_string())
            server.quit()
            logger.info(f"邮件告警发送成功，接收人：{receivers}")
        except Exception as e:
            logger.error(f"发送邮件告警失败：{e}")
            raise

    def _send_wecom_alert(self, result: MonitorResult, receiver: Optional[List[str]] = None):
        """发送企业微信告警"""
        wecom_config = self.channel_configs.get('wecom', {})
        if not wecom_config:
            logger.warning("企业微信告警未配置")
            raise ValueError("企业微信告警未配置")

        webhook_url = wecom_config.get('webhook_url')
        mentioned_list = receiver or wecom_config.get('mentioned_list', [])

        if not webhook_url:
            logger.warning("企业微信webhook未配置")
            raise ValueError("企业微信webhook未配置")

        message = self._format_alert_message(result)
        data = {
            "msgtype": "text",
            "text": {
                "content": message,
                "mentioned_list": mentioned_list
            }
        }

        try:
            response = requests.post(webhook_url, json=data, timeout=10)
            response.raise_for_status()
            logger.info("企业微信告警发送成功")
        except Exception as e:
            logger.error(f"发送企业微信告警失败：{e}")
            raise

    def _send_dingtalk_alert(self, result: MonitorResult, receiver: Optional[List[str]] = None):
        """发送钉钉告警"""
        dingtalk_config = self.channel_configs.get('dingtalk', {})
        if not dingtalk_config:
            logger.warning("钉钉告警未配置")
            raise ValueError("钉钉告警未配置")

        webhook_url = dingtalk_config.get('webhook_url')
        secret = dingtalk_config.get('secret')
        at_mobiles = receiver or dingtalk_config.get('at_mobiles', [])
        is_at_all = dingtalk_config.get('is_at_all', False)

        if not webhook_url:
            logger.warning("钉钉webhook未配置")
            raise ValueError("钉钉webhook未配置")

        message = self._format_alert_message(result)
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            },
            "at": {
                "atMobiles": at_mobiles,
                "isAtAll": is_at_all
            }
        }

        # 如果有secret，进行签名
        if secret:
            import time
            import hmac
            import hashlib
            import base64
            import urllib.parse

            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode('utf-8')
            string_to_sign = f"{timestamp}\n{secret}"
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

        try:
            response = requests.post(webhook_url, json=data, timeout=10)
            response.raise_for_status()
            logger.info("钉钉告警发送成功")
        except Exception as e:
            logger.error(f"发送钉钉告警失败：{e}")
            raise

    def _send_webhook_alert(self, result: MonitorResult):
        """发送自定义webhook告警"""
        webhook_config = self.channel_configs.get('webhook', {})
        if not webhook_config:
            logger.warning("Webhook告警未配置")
            raise ValueError("Webhook告警未配置")

        webhook_url = webhook_config.get('url')
        headers = webhook_config.get('headers', {})

        if not webhook_url:
            logger.warning("Webhook URL未配置")
            raise ValueError("Webhook URL未配置")

        data = {
            "alert": result.to_dict(),
            "timestamp": DateTimeUtils.now_str()
        }

        try:
            response = requests.post(webhook_url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info("Webhook告警发送成功")
        except Exception as e:
            logger.error(f"发送Webhook告警失败：{e}")
            raise

    def send_test_alert(self, channels: Optional[List[str]] = None) -> bool:
        """发送测试告警"""
        test_result = MonitorResult(
            monitor_name="测试监控",
            success=False,
            message="这是一条测试告警消息",
            level=AlertLevel.ERROR,
            metrics={"test_key": "test_value"},
            details={"test_detail": "测试详细信息"}
        )
        return self.send_alert(test_result, channels)


# 全局告警服务实例
alert_service = AlertService()
