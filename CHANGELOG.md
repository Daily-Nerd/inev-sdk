# Changelog

All notable changes to the INEV SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-22

### Added
- Initial release of INEV Python SDK
- `INEVClient` for async/sync event emission
- Auto-instrumentation middleware for FastAPI
- Framework integration stubs for Django and Flask
- Decorator pattern with `@emit_domain_event`
- Context manager pattern with `InstrumentationContext`
- Automatic event batching (size-based and time-based)
- Smart action naming from HTTP requests
- User identification from multiple sources
- Non-blocking event capture with async queues
- Comprehensive test suite
- Full documentation and examples

### Features
- Zero-code instrumentation for FastAPI applications
- Automatic semantic action extraction from HTTP endpoints
- Configurable path exclusions
- Batch size and flush interval configuration
- Graceful shutdown with pending event flush
- Support for Python 3.10+

[0.1.0]: https://github.com/Daily-Nerd/inev-sdk/releases/tag/v0.1.0
