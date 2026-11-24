# Shared AI controls (draft)

No live route is enabled by this package. Future routes must pass the authenticated server-side user object, never a client-supplied identity. The synchronous service must run in a worker thread, not block an async event loop.

Provisional limits: 3 requests per UTC minute, 20 per UTC day per user, 20,480 reserved output tokens per UTC day. Failed requests retain reservations. Atomic Table ETag updates preserve counters across runtime deletion. Fixed minute windows allow boundary bursts. The semaphore is per process; current deployment must remain one worker and one replica for a global limit of 3.

Conversation handles are user-partitioned and immutable. Each turn creates a new handle. Provider response retention may expire independently of Azure Storage. Results are stored in private blobs; future read APIs must enforce ownership. No arbitrary tools or model names are accepted by this service.

This is not a complete cost cap: input tokens, historical context, tool charges, failed requests and other inference paths need separate controls. Metrics cover successful returned inference calls only; persistence failures may leave partial records. Cloud tests and failure handling are required before live enablement. Fine-tuning remains disabled.
