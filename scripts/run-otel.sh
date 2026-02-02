#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
source "$PROJECT_DIR/.venv/bin/activate"

export OTEL_SERVICE_NAME=arc-damage-tracker
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_RESOURCE_ATTRIBUTES="service.name=arc-damage-tracker,deployment.environment=development"

opentelemetry-instrument gunicorn app:app --bind 0.0.0.0:8080
