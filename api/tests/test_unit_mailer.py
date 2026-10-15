"""Mail adapter tests use a fake SMTP client; no network or real server."""

import smtplib
import unittest
from unittest.mock import patch

from support import configured
from app.core.config import Settings
from app.core.errors import MailDeliveryError
from app.core.mailer import build_message, send_email


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send_message(self, message):
        self.sent.append(message)


class FailingSMTP(FakeSMTP):
    def send_message(self, message):
        raise smtplib.SMTPRecipientsRefused({"learner@example.test": (550, b"secret server detail")})


class MailerTests(unittest.TestCase):
    def setUp(self):
        FakeSMTP.instances = []

    def test_defaults_target_local_mailpit_without_changing_rag_defaults(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(_env_file=None)
        self.assertEqual((settings.smtp_host, settings.smtp_port), ("mailpit", 1025))
        self.assertEqual(settings.rag_profile, "fixture-offline")

    def test_sends_plain_text_to_configured_server(self):
        with configured(smtp_host="mail.test", smtp_port=2525, mail_from="InsightHub <noreply@example.test>"):
            with patch("app.core.mailer.smtplib.SMTP", FakeSMTP):
                message_id = send_email("learner@example.test", "Xác minh email", "Mã: 123456")
        client = FakeSMTP.instances[0]
        self.assertEqual((client.host, client.port), ("mail.test", 2525))
        sent = client.sent[0]
        self.assertEqual(sent["To"], "learner@example.test")
        self.assertEqual(sent["From"], "InsightHub <noreply@example.test>")
        self.assertEqual(sent["Subject"], "Xác minh email")
        self.assertEqual(sent.get_content_type(), "text/plain")
        self.assertIn("Mã: 123456", sent.get_content())
        self.assertEqual(sent["Message-ID"], message_id)

    def test_header_injection_is_rejected_before_connecting(self):
        with configured(), patch("app.core.mailer.smtplib.SMTP", FakeSMTP):
            for to, subject in [("a@example.test\nBcc: x@example.test", "S"), ("a@example.test", "S\r\nBcc: x"), ("", "S")]:
                with self.subTest(to=to, subject=subject), self.assertRaises(ValueError):
                    send_email(to, subject, "body")
        self.assertEqual(FakeSMTP.instances, [])

    def test_transport_failure_maps_to_fixed_error_without_details(self):
        with configured(), patch("app.core.mailer.smtplib.SMTP", FailingSMTP):
            with self.assertRaises(MailDeliveryError) as raised:
                send_email("learner@example.test", "S", "private body")
        text = str(raised.exception)
        self.assertNotIn("private body", text)
        self.assertNotIn("secret server detail", text)
        self.assertIsNone(raised.exception.__cause__)

    def test_connection_refused_maps_to_mail_error(self):
        def refuse(*args, **kwargs):
            raise ConnectionRefusedError()
        with configured(), patch("app.core.mailer.smtplib.SMTP", refuse):
            with self.assertRaises(MailDeliveryError):
                send_email("learner@example.test", "S", "body")

    def test_build_message_uses_settings_sender(self):
        with configured():
            message = build_message("learner@example.test", "S", "body")
        self.assertEqual(message["From"], "InsightHub <no-reply@insighthub.local>")


if __name__ == "__main__":
    unittest.main()
