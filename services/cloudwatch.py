"""CloudWatch: structured logs (stdout) + optional custom metrics (``put_metric_data``).

**Elastic Beanstalk / EC2:** Gunicorn logs to stdout; the platform (or the CloudWatch agent)
typically ships log streams to a log group with no app code. Set ``ENABLE_CLOUDWATCH=true``
to also record **per-activity** metrics from ``log_activity`` (``ActivityAction`` with
dimension ``Action``) for dashboards and basic alarms in the AWS console.
"""
from __future__ import annotations

import json
import time
from typing import Any

from flask import current_app


def _structured_line(level: str, message: str, **extra: Any) -> str:
    payload = {
        "level": level,
        "message": message,
        "ts": time.time(),
        **extra,
    }
    return json.dumps(payload, default=str)


def emit_metric_or_log(message: str, extra: dict[str, Any] | None = None) -> None:
    """Emit a JSON line to the app logger (stdout on EB/EC2 → CloudWatch log group). No PutMetricData."""
    line = _structured_line("INFO", message, **(extra or {}))
    current_app.logger.info(line)


def emit_activity_metric(action: str) -> None:
    """Count each ``action`` from ``log_activity`` (dimension ``Action`` = action name)."""
    if not current_app.config.get("ENABLE_CLOUDWATCH"):
        return
    if not action:
        return
    try:
        import boto3

        region = current_app.config.get("AWS_REGION", "us-east-1")
        namespace = current_app.config.get("CLOUDWATCH_METRIC_NAMESPACE", "Whiteboard/App")
        cw = boto3.client("cloudwatch", region_name=region)
        safe_action = (action or "")[:255] or "unknown"
        cw.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    "MetricName": "ActivityAction",
                    "Dimensions": [{"Name": "Action", "Value": safe_action}],
                    "Value": 1.0,
                    "Unit": "Count",
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("CloudWatch ActivityAction metric skipped: %s", exc)
