# Product Overview

INEV SDK is a Python SDK for **automatic event capture** enabling Intentionality Leakage Analysis (ILA). It allows developers to track user behavior, detect trajectory gaps, and identify error leaks with minimal code changes.

## Core Capabilities

1. **Zero-Code Auto-Instrumentation** - Middleware that automatically captures all HTTP requests/responses as domain events without code changes to route handlers
2. **Async-First Event Batching** - Non-blocking event queuing with configurable batch sizes and flush intervals for high-volume scenarios
3. **Hybrid Event Capture** - Combines client-side extraction with server-side enrichment for semantic domain context
4. **Structured Error Tracking** - Automatic extraction of error codes, types, categories, and details from exceptions and responses
5. **Multiple Integration Patterns** - Context managers, decorators, and direct client API for different use cases

## Target Use Cases

- **API Observability** - Track all HTTP interactions in FastAPI/Starlette applications
- **State Machine Monitoring** - Capture state transitions with from/to states for trajectory analysis
- **Error Analysis** - Classify and track errors with structured context for debugging
- **Serverless Environments** - Synchronous mode for AWS Lambda and similar environments

## Value Proposition

- **Minimal Integration Effort** - Single middleware addition captures everything
- **Never Slows Requests** - Background batching and async design
- **Smart Extraction** - Automatic entity/record ID extraction from URLs, state inference from HTTP context
- **Framework Native** - Designed for FastAPI/Starlette with Django/Flask support planned

---
_Focus on patterns and purpose, not exhaustive feature lists_
