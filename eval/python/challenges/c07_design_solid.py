"""
CHALLENGE: Notification System — Design for Extension
CATEGORY: design_solid
DIFFICULTY: 2
POINTS: 20
WHY: Models dump everything into one class. When asked to make it extensible, they either
     over-engineer with abstract factories or just add if/elif branches. This challenge
     tests whether the model produces code that can be extended WITHOUT modifying existing code.
     The twist: after the initial generation, we test that adding a new channel requires
     zero modifications to existing classes.
"""

PROMPT = """
Design a notification system that can send messages through multiple channels.

Requirements:
1. Support these channels initially: Email, SMS, Webhook
2. Each channel has its own configuration and send logic
3. A NotificationService accepts a message and sends it through one or more channels
4. **Critical**: The system must be extensible — adding a new channel (e.g., Slack, Push)
   must NOT require modifying any existing class. Only new code should be added.
5. Use dependency injection — the NotificationService receives its channels, it does not create them
6. Each channel's send method returns a Result indicating success or failure with a reason
7. The NotificationService.notify() returns a dict mapping channel names to their Results

Write the following:

```python
from dataclasses import dataclass
from enum import Enum

class ResultStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"

@dataclass
class Result:
    status: ResultStatus
    channel: str
    message: str  # success message or failure reason

@dataclass
class Message:
    recipient: str
    subject: str
    body: str

# Abstract base / Protocol for channels
# Concrete channel implementations: EmailChannel, SMSChannel, WebhookChannel
# NotificationService that orchestrates sending
```

Each channel class must:
- Have a `name` property returning the channel name (e.g., "email", "sms", "webhook")
- Have a `send(message: Message) -> Result` method
- Accept its configuration via __init__ (not global config)

The NotificationService must:
- Accept a list of channels via __init__
- Have a `notify(message: Message) -> dict[str, Result]` method
- Send through ALL channels even if some fail
- Not contain any channel-specific logic (no if/elif on channel type)
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib
from unittest.mock import MagicMock


def load():
    mod = importlib.import_module("solutions.c07_design_solid")
    return mod


class TestBasicStructure:
    """4 points."""

    def test_message_dataclass(self):
        """(1 pt) Message has recipient, subject, body."""
        mod = load()
        msg = mod.Message(recipient="user@test.com", subject="Hello", body="World")
        assert msg.recipient == "user@test.com"

    def test_result_dataclass(self):
        """(1 pt) Result has status, channel, message."""
        mod = load()
        r = mod.Result(status=mod.ResultStatus.SUCCESS, channel="email", message="sent")
        assert r.status == mod.ResultStatus.SUCCESS

    def test_channels_have_name(self):
        """(1 pt) Each channel has a name property."""
        mod = load()
        email = mod.EmailChannel(host="smtp.test.com", port=587)
        sms = mod.SMSChannel(api_key="test-key")
        webhook = mod.WebhookChannel(url="https://hook.test.com")
        assert email.name == "email"
        assert sms.name == "sms"
        assert webhook.name == "webhook"

    def test_channels_have_send(self):
        """(1 pt) Each channel has a send method returning Result."""
        mod = load()
        email = mod.EmailChannel(host="smtp.test.com", port=587)
        msg = mod.Message(recipient="x@test.com", subject="Test", body="Body")
        result = email.send(msg)
        assert isinstance(result, mod.Result)


class TestNotificationService:
    """6 points."""

    def test_sends_to_all_channels(self):
        """(2 pts) notify() sends through ALL registered channels."""
        mod = load()
        email = mod.EmailChannel(host="smtp.test.com", port=587)
        sms = mod.SMSChannel(api_key="key")
        service = mod.NotificationService(channels=[email, sms])
        msg = mod.Message(recipient="user", subject="Hi", body="Hello")
        results = service.notify(msg)
        assert "email" in results
        assert "sms" in results

    def test_continues_on_failure(self):
        """(2 pts) If one channel fails, others still execute."""
        mod = load()

        class FailingChannel:
            @property
            def name(self):
                return "failing"

            def send(self, message):
                raise Exception("boom")

        class TrackingChannel:
            def __init__(self):
                self.called = False

            @property
            def name(self):
                return "tracking"

            def send(self, message):
                self.called = True
                return mod.Result(
                    status=mod.ResultStatus.SUCCESS,
                    channel="tracking",
                    message="sent",
                )

        tracker = TrackingChannel()
        service = mod.NotificationService(channels=[FailingChannel(), tracker])
        msg = mod.Message(recipient="user", subject="Hi", body="Hello")
        results = service.notify(msg)
        assert tracker.called is True
        assert results["failing"].status == mod.ResultStatus.FAILURE

    def test_no_channel_specific_logic(self):
        """(2 pts) NotificationService has no if/elif on channel type."""
        mod = load()
        import inspect

        source = inspect.getsource(mod.NotificationService)
        # Should not contain isinstance checks or channel-type conditionals
        assert "isinstance" not in source, "Service should not check channel types"
        assert "EmailChannel" not in source, "Service should not reference specific channels"
        assert "SMSChannel" not in source, "Service should not reference specific channels"
        assert "WebhookChannel" not in source, "Service should not reference specific channels"


class TestOpenClosedPrinciple:
    """6 points — the core of this challenge."""

    def test_new_channel_no_modification(self):
        """(3 pts) A brand new channel works with zero changes to existing code."""
        mod = load()

        # A completely new channel — written here, not in the module
        class SlackChannel:
            def __init__(self, webhook_url: str):
                self.webhook_url = webhook_url

            @property
            def name(self):
                return "slack"

            def send(self, message):
                return mod.Result(
                    status=mod.ResultStatus.SUCCESS,
                    channel="slack",
                    message=f"Posted to {self.webhook_url}",
                )

        service = mod.NotificationService(
            channels=[
                mod.EmailChannel(host="smtp.test.com", port=587),
                SlackChannel(webhook_url="https://hooks.slack.com/xxx"),
            ]
        )
        msg = mod.Message(recipient="user", subject="Hi", body="Hello")
        results = service.notify(msg)
        assert "slack" in results
        assert results["slack"].status == mod.ResultStatus.SUCCESS

    def test_channel_interface_is_minimal(self):
        """(3 pts) A channel only needs name + send. No registration, no base class required."""
        mod = load()

        # Absolute minimal channel — just a duck-typed object
        class MinimalChannel:
            @property
            def name(self):
                return "minimal"

            def send(self, message):
                return mod.Result(
                    status=mod.ResultStatus.SUCCESS,
                    channel="minimal",
                    message="ok",
                )

        service = mod.NotificationService(channels=[MinimalChannel()])
        msg = mod.Message(recipient="anyone", subject="Test", body="Body")
        results = service.notify(msg)
        assert results["minimal"].status == mod.ResultStatus.SUCCESS


class TestSingleResponsibility:
    """4 points."""

    def test_service_does_not_format_messages(self):
        """(2 pts) Service has no message formatting logic."""
        mod = load()
        import inspect

        source = inspect.getsource(mod.NotificationService)
        # Service should not contain format/template logic
        assert "format" not in source.lower() or "format" in "ResultStatus.FAILURE".lower()
        # More targeted: should not contain string templates or HTML
        assert "<html" not in source.lower()
        assert "template" not in source.lower()

    def test_channels_own_their_config(self):
        """(2 pts) Each channel takes its own config, not a shared config dict."""
        mod = load()
        import inspect

        # EmailChannel should accept host/port, not a generic config dict
        sig = inspect.signature(mod.EmailChannel.__init__)
        params = list(sig.parameters.keys())
        assert len(params) >= 2  # self + at least one config param
        assert "config" not in params  # Should not take a generic config dict
