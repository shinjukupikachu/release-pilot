from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from release_pilot import config

_RELEASES = [
    {
        "version": "v1.0.0",
        "from_ref": "v0.9.0",
        "days_ago": 540,
        "suggested_bump": "major",
        "readiness_score": 95,
        "recommendation": "READY",
        "internal_announcement": (
            "## NyankoOS v1.0.0 — General Availability\n\nAfter 18 months of "
            "development and beta testing with 12 pilot customers, NyankoOS 1.0 is "
            "shipping. This is our first production-ready release.\n\n**Core "
            "capabilities shipping today:**\n- Pick-and-place task execution for "
            "standard 6-DOF arms\n- Vision-based object detection (YOLOv5)\n- REST "
            "API for task management\n- Web operator dashboard\n- SQLite-backed task "
            "history"
        ),
        "customer_notes": (
            "## NyankoOS v1.0.0 — Generally Available\n\nWe're excited to announce "
            "the general availability of NyankoOS 1.0, the first production release of "
            "Nyanko's robot operating system.\n\n### What's Included\n\n**Core Robot "
            "Control**\n- Execute pick-and-place tasks on standard 6-DOF industrial "
            "robot arms\n- Real-time trajectory planning with collision avoidance\n- "
            "Graceful E-stop and recovery handling\n\n**Vision System**\n- Object "
            "detection and pose estimation using onboard cameras\n- Supports "
            "structured-light and stereo depth sensors\n- Confidence-based pick "
            "decision gating\n\n**Operator Dashboard**\n- Web-based UI for task "
            "monitoring and configuration\n- Real-time robot status, joint positions, "
            "and camera feeds\n- Task history and basic cycle time metrics\n\n**REST "
            "API**\n- Full task lifecycle management via REST\n- Webhook support for "
            "task completion events\n- Python SDK included"
        ),
        "marketing_notes": (
            "## NyankoOS 1.0: The Industrial Robot OS Built for Production\n\nToday, "
            "Nyanko launches NyankoOS 1.0 — the first robot operating system designed "
            "from the ground up for production warehouse automation.\n\nUnlike "
            "research-grade platforms, NyankoOS 1.0 ships with everything needed to "
            "run a live picking cell: vision, planning, control, and a production-ready "
            "API. No PhD required."
        ),
        "traceability": [
            {
                "short_hash": "1a2b3c4",
                "description": "feat: initial pick-and-place task execution engine",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 1,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/1",
            },
            {
                "short_hash": "2b3c4d5",
                "description": "feat: YOLOv5 object detection integration",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 2,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/2",
            },
            {
                "short_hash": "3c4d5e6",
                "description": "feat: REST API for task management",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 3,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/3",
            },
            {
                "short_hash": "4d5e6f7",
                "description": "feat: web operator dashboard",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 4,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/4",
            },
        ],
    },
    {
        "version": "v1.1.0",
        "from_ref": "v1.0.0",
        "days_ago": 480,
        "suggested_bump": "minor",
        "readiness_score": 88,
        "recommendation": "READY",
        "internal_announcement": ("## NyankoOS v1.1.0\n\nFirst minor release since GA. Focuses on conveyor tracking, multi-SKU support, and the Python SDK.\n\n**Key wins:** conveyor tracking at up to 1.5 m/s, barcode fallback for low-confidence picks, SDK published to PyPI."),
        "customer_notes": (
            "## NyankoOS v1.1.0 — What's New\n\n### New Features\n\n**Conveyor Tracking** "
            "— Robots can now pick items from moving conveyors at speeds up to 1.5 m/s. "
            "Configure belt speed via the dashboard or API.\n\n**Multi-SKU Support** — A "
            "single cell can now handle up to 20 distinct SKU types simultaneously with "
            "per-SKU grasp profiles.\n\n**Barcode Fallback** — When vision confidence "
            "falls below your configured threshold, NyankoOS automatically falls back to "
            "barcode scanning to confirm item identity before picking.\n\n**Python SDK on "
            "PyPI** — Install with `pip install nyankoos-sdk`. Full API coverage with "
            "async support.\n\n### Bug Fixes\n\n- Fixed gripper jaw calibration drift "
            "after 10,000 cycles\n- Fixed waypoint editor crash on import of files with "
            "more than 500 waypoints\n- Fixed dashboard session timeout with no notification"
        ),
        "marketing_notes": ("## NyankoOS v1.1 Adds Conveyor Tracking and Multi-SKU Support\n\nNyankoOS 1.1 brings two of the most-requested capabilities from our launch customers: the ability to pick from moving conveyors and to handle diverse product mixes in a single cell."),
        "traceability": [
            {
                "short_hash": "5e6f7a8",
                "description": "feat(conveyor): tracking at up to 1.5 m/s belt speed",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 8,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/8",
            },
            {
                "short_hash": "6f7a8b9",
                "description": "feat(vision): barcode fallback for low-confidence picks",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 9,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/9",
            },
            {
                "short_hash": "7a8b9c0",
                "description": "fix(gripper): jaw calibration drift after 10k cycles",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 10,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/10",
            },
        ],
    },
    {
        "version": "v1.1.10",
        "from_ref": "v1.1.0",
        "days_ago": 430,
        "suggested_bump": "patch",
        "readiness_score": 92,
        "recommendation": "READY",
        "internal_announcement": (
            "## NyankoOS v1.1.10 — Patch Release\n\nSecurity and stability patches. All customers on v1.1.x should upgrade.\n\n- SLAM map corruption on hard power cycle (critical)\n- Memory leak in point cloud pipeline (critical)\n- E-stop not propagating to conveyor PLC (critical)"
        ),
        "customer_notes": (
            "## NyankoOS v1.1.10 — Patch Release\n\nThis patch release addresses "
            "three critical stability and safety issues. **All customers on v1.1.x "
            "are strongly encouraged to upgrade.**\n\n### Critical Fixes\n\n- **SLAM "
            "Map Corruption** — Fixed a corruption bug that occurred when the "
            "controller experienced a hard power cycle during active mapping. Maps "
            "are now written atomically.\n\n- **Memory Leak in Vision Pipeline** — "
            "Fixed a memory leak in the point cloud pre-processing pipeline that "
            "caused controller memory to exhaust after ~72 hours of continuous "
            "operation.\n\n- **E-Stop Propagation** — Fixed an issue where a robot "
            "arm E-stop did not propagate to the connected conveyor belt PLC, "
            "leaving the belt running after an emergency stop."
        ),
        "marketing_notes": (
            "## NyankoOS v1.1.10 — Critical Safety & Stability Patch\n\nNyankoOS "
            "v1.1.10 addresses three critical issues including an E-stop propagation "
            "failure and a memory leak that caused controller instability after 72 "
            "hours of continuous operation. All customers on v1.1.x should upgrade "
            "immediately."
        ),
        "traceability": [
            {
                "short_hash": "8b9c0d1",
                "description": "fix(slam): map corruption on hard power cycle",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 15,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/15",
            },
            {
                "short_hash": "9c0d1e2",
                "description": "fix(vision): memory leak in point cloud pipeline",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 16,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/16",
            },
            {
                "short_hash": "0d1e2f3",
                "description": "fix(safety): E-stop not propagating to conveyor PLC",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 17,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/17",
            },
        ],
    },
    {
        "version": "v1.3.0",
        "from_ref": "v1.2.0",
        "days_ago": 360,
        "suggested_bump": "minor",
        "readiness_score": 85,
        "recommendation": "READY",
        "internal_announcement": ("## NyankoOS v1.3.0\n\nBig release — palletizing, RBAC, multi-camera rigs, and Fanuc CRX support.\n\nHeadline: palletizing is now generally available after 6 months in beta. 8 customers already in production."),
        "customer_notes": (
            "## NyankoOS v1.3.0 — What's New\n\n### New Features\n\n**Palletizing — "
            "Generally Available** — NyankoOS now supports full pallet building with "
            "configurable layer patterns, mixed-SKU stacking, and overhang detection. "
            "Graduated from beta after 6 months of pilot deployments.\n\n**Role-Based "
            "Access Control** — Three built-in roles: Operator, Engineer, and Admin. "
            "Restrict dashboard and API access by role. Compatible with your existing "
            "SSO provider via SAML 2.0.\n\n**Multi-Camera Rig Support** — Configure up "
            "to 4 cameras per cell with automatic calibration using the new calibration "
            "wizard. Improves pick accuracy in large bin or conveyor-width scenarios.\n\n"
            "**Fanuc CRX Series Support** — Native integration with Fanuc CRX-10iA and "
            "CRX-25iA collaborative robots. No third-party middleware required.\n\n"
            "**Dark Mode** — The operator dashboard now supports dark mode. Toggle in "
            "user preferences.\n\n### Bug Fixes\n\n- Fixed palletizing pattern editor "
            "not rendering mixed-height layers\n- Fixed controller CPU spike to "
            "100% during point cloud registration\n- Fixed task log export truncating "
            "beyond 10,000 records"
        ),
        "marketing_notes": (
            "## NyankoOS v1.3: Palletizing Goes GA, Enterprise Access Controls Added\n\n"
            "NyankoOS 1.3 marks a major milestone: our palletizing module is now generally "
            "available, supported by 6 months of production deployments across 8 customer "
            "sites.\n\nCombined with new enterprise-grade RBAC and multi-camera support, "
            "NyankoOS 1.3 is our most enterprise-ready release to date."
        ),
        "traceability": [
            {
                "short_hash": "1e2f3a4",
                "description": "feat(palletizing): GA release of palletizing module",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 20,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/20",
            },
            {
                "short_hash": "2f3a4b5",
                "description": "feat(auth): RBAC with Operator/Engineer/Admin roles",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 21,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/21",
            },
            {
                "short_hash": "3a4b5c6",
                "description": "feat(vision): multi-camera rig with calibration wizard",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 22,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/22",
            },
            {
                "short_hash": "4b5c6d7",
                "description": "feat(integration): Fanuc CRX-10iA and CRX-25iA support",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 23,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/23",
            },
        ],
    },
    {
        "version": "v1.5.0",
        "from_ref": "v1.4.0",
        "days_ago": 270,
        "suggested_bump": "minor",
        "readiness_score": 90,
        "recommendation": "READY",
        "internal_announcement": ("## NyankoOS v1.5.0\n\nPerformance milestone release. Motion planning latency down 25%, vision pipeline parallelized, Manhattan Associates WMS connector ships.\n\nThis sets the foundation for v2.0 architecture changes."),
        "customer_notes": (
            "## NyankoOS v1.5.0 — What's New\n\n### Performance Improvements\n\n**25% Faster "
            "Motion Planning** — Upgraded path planner reduces average planning time from "
            "160ms to 120ms. Most noticeable on high-mix, high-frequency picking lines.\n\n"
            "**Parallel Vision Pipeline** — Object detection and depth estimation now run in "
            "parallel, cutting total vision processing time by 30%.\n\n### New Features\n\n"
            "**Manhattan Associates WMS Connector** — Native integration with Manhattan Active "
            "WM. Bidirectional task sync without custom middleware. Contact your account team "
            "to enable.\n\n**Webhook Task Events** — Subscribe to task completion, failure, "
            "and regrasp events via HTTP webhooks. Payload includes full task metadata and "
            "pick outcome.\n\n**Audit Log** — All operator and API actions are now logged with "
            "user identity and timestamp. Exportable from the dashboard.\n\n### Bug Fixes\n\n"
            "- Fixed false positive collision detection in reflective packaging environments\n"
            "- Fixed vision pipeline hang on zero-byte USB camera frames\n- Fixed throughput "
            "metrics not accounting for regrasp attempts"
        ),
        "marketing_notes": ("## NyankoOS v1.5: 25% Faster Planning, Enterprise WMS Connectivity\n\nNyankoOS 1.5 delivers measurable throughput gains without hardware changes, and expands enterprise connectivity with the Manhattan Active WM integration."),
        "traceability": [
            {
                "short_hash": "5c6d7e8",
                "description": "perf(planner): reduce latency 25% with upgraded path planner",
                "commit_type": "perf",
                "is_breaking": False,
                "pr_number": 28,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/28",
            },
            {
                "short_hash": "6d7e8f9",
                "description": "perf(vision): parallelize detection and depth estimation",
                "commit_type": "perf",
                "is_breaking": False,
                "pr_number": 29,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/29",
            },
            {
                "short_hash": "7e8f9a0",
                "description": "feat(integration): Manhattan Associates WMS connector",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 30,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/30",
            },
            {
                "short_hash": "8f9a0b1",
                "description": "feat(security): audit log for all operator and API actions",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 31,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/31",
            },
        ],
    },
    {
        "version": "v2.0.0",
        "from_ref": "v1.5.0",
        "days_ago": 210,
        "suggested_bump": "major",
        "readiness_score": 78,
        "recommendation": "HOLD",
        "internal_announcement": (
            "## NyankoOS v2.0.0 — Major Release\n\nv2.0 is our biggest architectural change "
            "since launch. Async task engine, new v2 API, Python SDK 2.0, and multi-arm "
            "support.\n\n**⚠️ Breaking changes** — v1 API and SDK are deprecated (18-month "
            "support window). All customers need migration plans.\n\nReadiness: HOLD — we "
            "released with known compat CI failures on two v1 endpoints. Patch incoming."
        ),
        "customer_notes": (
            "## NyankoOS v2.0.0 — What's New\n\n### Architecture\n\n**Async Task Engine** — "
            "The core task execution engine has been rewritten with an async event loop. This "
            "enables NyankoOS to handle 10x more concurrent tasks without proportional CPU "
            "cost.\n\n**Multi-Arm Coordination** — Up to 4 robot arms can now share a workspace "
            "with automatic conflict resolution and priority-based handoff zones.\n\n### API & "
            "SDK\n\n**REST API v2** — Cleaner resource model, consistent pagination, and OpenAPI "
            "3.1 spec. See the [migration guide](docs/api/v2-migration.md).\n\n**Python SDK 2.0** "
            "— New async-first SDK with full type annotations. Install: `pip install "
            "nyankoos-sdk>=2.0`.\n\n### Important: Breaking Changes\n\n**REST API v1 Deprecated** "
            "— `/api/v1/*` endpoints will continue to work for 18 months (until NyankoOS v2.6). "
            "All new integrations should use `/api/v2/*`.\n\n**SDK v1 Deprecated** — "
            "`RobotClient.connect_v1()` is deprecated. Migrate to `RobotClient.connect()`. "
            "Removal planned for v2.3."
        ),
        "marketing_notes": (
            "## NyankoOS 2.0: Built for Scale\n\nNyankoOS 2.0 is a ground-up redesign of "
            "the task execution engine, purpose-built for large-scale, multi-robot "
            "warehouse operations.\n\nThe new async architecture enables a single controller "
            "to coordinate up to 4 robot arms simultaneously — tripling the capacity of a "
            "v1.x installation without additional hardware."
        ),
        "traceability": [
            {
                "short_hash": "9a0b1c2",
                "description": "feat(core)!: async task engine rewrite",
                "commit_type": "feat",
                "is_breaking": True,
                "pr_number": 35,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/35",
            },
            {
                "short_hash": "0b1c2d3",
                "description": "feat(api)!: REST API v2 with OpenAPI 3.1 spec",
                "commit_type": "feat",
                "is_breaking": True,
                "pr_number": 36,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/36",
            },
            {
                "short_hash": "1c2d3e4",
                "description": "feat(planning): multi-arm coordination up to 4 arms",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 37,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/37",
            },
            {
                "short_hash": "2d3e4f5",
                "description": "feat(sdk)!: Python SDK 2.0 async-first rewrite",
                "commit_type": "feat",
                "is_breaking": True,
                "pr_number": 38,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/38",
            },
        ],
    },
    {
        "version": "v2.0.1",
        "from_ref": "v2.0.0",
        "days_ago": 200,
        "suggested_bump": "patch",
        "readiness_score": 95,
        "recommendation": "READY",
        "internal_announcement": ("## NyankoOS v2.0.1 — Hotfix\n\nFixes the two failing CI checks that shipped with v2.0.0. Backward-compat endpoints restored. All customers should upgrade from v2.0.0."),
        "customer_notes": (
            "## NyankoOS v2.0.1 — Patch Release\n\n### Fixes\n\n- **Restored API v1 backward "
            "compatibility** — Two v1 endpoints (`/api/v1/tasks` and `/api/v1/status`) were "
            "returning 404 in v2.0.0 due to a routing regression. Both are restored and will "
            "continue to function through the deprecation window.\n- **SDK v1 connect "
            "fallback** — `RobotClient.connect_v1()` no longer raises `NotImplementedError` "
            "in v2.0.0. The deprecation warning is preserved."
        ),
        "marketing_notes": (
            "## NyankoOS v2.0.1 — API Compatibility Restored\n\nNyankoOS v2.0.1 restores full backward compatibility with the v1 API after a routing regression in the v2.0.0 launch. Customers using v1 API endpoints can upgrade from v2.0.0 immediately with no integration changes required."
        ),
        "traceability": [
            {
                "short_hash": "3e4f5a6",
                "description": "fix(api): restore v1 backward-compat routing regression",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 39,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/39",
            },
            {
                "short_hash": "4f5a6b7",
                "description": "fix(sdk): restore connect_v1 deprecation shim",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 40,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/40",
            },
        ],
    },
    {
        "version": "v2.1.0",
        "from_ref": "v2.0.1",
        "days_ago": 150,
        "suggested_bump": "minor",
        "readiness_score": 91,
        "recommendation": "READY",
        "internal_announcement": ("## NyankoOS v2.1.0\n\nSAML SSO, OpenTelemetry tracing, Cognex camera support, and a new guided setup wizard.\n\nFirst release to hit 99.2% pick accuracy in customer telemetry (up from 97.8% in v2.0)."),
        "customer_notes": (
            "## NyankoOS v2.1.0 — What's New\n\n### New Features\n\n**SAML 2.0 SSO** — Connect "
            "NyankoOS to your identity provider (Okta, Azure AD, Google Workspace) using SAML 2.0. "
            "All user sessions are brokered through your IdP.\n\n**OpenTelemetry Tracing** — "
            "Distributed traces for all controller operations are now exported in OTLP format. "
            "Compatible with Jaeger, Grafana Tempo, and any OpenTelemetry-compatible backend.\n\n"
            "**Cognex In-Sight 9000 Camera Support** — Native integration with Cognex In-Sight "
            "9000 series smart cameras. No separate Cognex runtime license required.\n\n"
            "**Guided Setup Wizard** — New step-by-step wizard walks operators through first-time "
            "cell configuration: robot registration, camera calibration, gripper profile, and "
            "first task.\n\n### Performance\n\nPick accuracy across the fleet has improved to "
            "**99.2%** (up from 97.8% in v2.0), driven by improved depth sensor calibration and "
            "confidence-gating tuning.\n\n### Bug Fixes\n\n- Fixed NTP sync drift causing task "
            "timestamp skew on isolated networks\n- Fixed CSV import rejecting files with BOM "
            "encoding\n- Fixed arm oscillation at end-effector deceleration on payloads >10kg"
        ),
        "marketing_notes": (
            "## NyankoOS v2.1: Enterprise Identity, Observability, and 99.2% Pick Accuracy\n\nNyankoOS 2.1 raises the bar on enterprise readiness with native SAML SSO, full OpenTelemetry observability, and a pick accuracy improvement that translates directly to fewer line stoppages."
        ),
        "traceability": [
            {
                "short_hash": "5a6b7c8",
                "description": "feat(auth): SAML 2.0 SSO integration",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 41,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/41",
            },
            {
                "short_hash": "6b7c8d9",
                "description": "feat(observability): OpenTelemetry OTLP trace export",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 42,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/42",
            },
            {
                "short_hash": "7c8d9e0",
                "description": "feat(vision): Cognex In-Sight 9000 native integration",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 43,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/43",
            },
            {
                "short_hash": "8d9e0f1",
                "description": "feat(ux): guided setup wizard for first-time configuration",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 44,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/44",
            },
        ],
    },
    {
        "version": "v2.2.0",
        "from_ref": "v2.1.0",
        "days_ago": 90,
        "suggested_bump": "minor",
        "readiness_score": 87,
        "recommendation": "READY",
        "internal_announcement": ("## NyankoOS v2.2.0\n\nStability & performance cycle. Variable conveyor speed, KUKA iiQKA support, offline task queuing, and QA test suite expansion.\n\nKey metric: zero critical bugs in the last 30-day soak test."),
        "customer_notes": (
            "## NyankoOS v2.2.0 — What's New\n\n### New Features\n\n"
            "**Variable Conveyor Speed** — Conveyor belt speed can now be dynamically "
            "controlled via PLC analog signal or API. NyankoOS automatically adjusts "
            "tracking parameters in real time.\n\n**KUKA iiQKA OS 1.2 Support** — NyankoOS "
            "now integrates natively with KUKA's iiQKA OS 1.2 motion interface. Supports all "
            "KUKA LBR iisy models.\n\n**Offline Task Queuing** — When cloud connectivity is "
            "lost, controllers now buffer up to 10,000 tasks locally and sync automatically "
            "on reconnection. No tasks are lost during network outages.\n\n**Predictive "
            "Maintenance Alerts** — Joint vibration data is now analyzed for anomalies. "
            "Alerts fire when vibration patterns suggest impending bearing wear, giving "
            "maintenance teams advance warning.\n\n### Performance\n\n- Conveyor tracking "
            "now stable at speeds up to 2.5 m/s (up from 2.0 m/s)\n- Point cloud registration "
            "CPU usage reduced by 35%\n\n### Bug Fixes\n\n- Fixed cycle count reset at midnight "
            "UTC crossover\n- Fixed task log export truncation at 10,000 records\n- Fixed URDF "
            "import failure with non-standard joint naming"
        ),
        "marketing_notes": (
            "## NyankoOS v2.2: Resilient Operations and Predictive Maintenance\n\n"
            "NyankoOS 2.2 focuses on operational resilience — offline queuing ensures zero "
            "task loss during network outages, and predictive maintenance alerts help "
            "customers get ahead of hardware failures before they impact throughput."
        ),
        "traceability": [
            {
                "short_hash": "9e0f1a2",
                "description": "feat(conveyor): variable speed via PLC analog signal",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 44,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/44",
            },
            {
                "short_hash": "0f1a2b3",
                "description": "feat(integration): KUKA iiQKA OS 1.2 motion interface",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 45,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/45",
            },
            {
                "short_hash": "1a2b3c4",
                "description": "feat(resilience): offline task queuing with auto-sync",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 46,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/46",
            },
            {
                "short_hash": "2b3c4d5",
                "description": "feat(monitoring): predictive maintenance from joint vibration",
                "commit_type": "feat",
                "is_breaking": False,
                "pr_number": 47,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/47",
            },
        ],
    },
    {
        "version": "v2.2.1",
        "from_ref": "v2.2.0",
        "days_ago": 60,
        "suggested_bump": "patch",
        "readiness_score": 96,
        "recommendation": "READY",
        "internal_announcement": ("## NyankoOS v2.2.1 — Patch Release\n\nAddresses QA regression failures found in v2.2.0 palletizing smoke suite and load test results. Fixes thread pool exhaustion under high API concurrency."),
        "customer_notes": (
            "## NyankoOS v2.2.1 — Patch Release\n\n### Fixes\n\n"
            "- **Thread Pool Exhaustion** — Fixed a bug where sustained API load above 200 "
            "concurrent requests caused the thread pool to exhaust, resulting in 503 errors. "
            "The pool is now dynamically sized.\n\n- **Palletizing Smoke Suite Regression** — "
            "Fixed a regression in the palletizing layer solver introduced in v2.2.0 that "
            "caused incorrect pallet patterns for SKUs with aspect ratio > 3:1.\n\n"
            "- **Vision Model Accuracy After OpenCV Upgrade** — Corrected a calibration "
            "parameter that caused a 3% accuracy drop after the OpenCV 4.8 upgrade in v2.2.0. "
            "Accuracy is restored to v2.1.0 baseline."
        ),
        "marketing_notes": (
            "## NyankoOS v2.2.1 — Pick Accuracy and Palletizing Reliability Restored\n\n"
            "NyankoOS v2.2.1 corrects a vision calibration drift introduced in v2.2.0, "
            "restoring pick accuracy to the v2.1.0 baseline, and fixes a palletizing pattern "
            "regression for high aspect-ratio SKUs. Customers running v2.2.0 should upgrade."
        ),
        "traceability": [
            {
                "short_hash": "3c4d5e6",
                "description": "fix(api): dynamic thread pool sizing under high concurrency",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 48,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/48",
            },
            {
                "short_hash": "4d5e6f7",
                "description": ("fix(palletizing): layer solver regression for high aspect-ratio SKUs",),
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 49,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/49",
            },
            {
                "short_hash": "5e6f7a8",
                "description": "fix(vision): restore accuracy after OpenCV 4.8 calibration drift",
                "commit_type": "fix",
                "is_breaking": False,
                "pr_number": 50,
                "pr_url": "https://github.com/nyanko/nyankoos/pull/50",
            },
        ],
    },
]


def seed_releases(db_path: str = config.DB_PATH) -> int:
    """Insert mock historical releases. Returns count of releases inserted."""
    seeded = 0
    with sqlite3.connect(db_path) as conn:
        for r in _RELEASES:
            exists = conn.execute("SELECT 1 FROM releases WHERE version = ?", (r["version"],)).fetchone()
            if exists:
                # Patch marketing_notes if it was seeded as NULL but now has content
                if r["marketing_notes"]:
                    conn.execute(
                        ("UPDATE releases SET marketing_notes = ? WHERE version = ? AND marketing_notes IS NULL"),
                        (r["marketing_notes"], r["version"]),
                    )
                continue

            created_at = (datetime.now(UTC) - timedelta(days=r["days_ago"])).isoformat()

            cur = conn.execute(
                """INSERT INTO releases
                   (version, from_ref, created_at, readiness_score, recommendation,
                    suggested_bump, internal_announcement, customer_notes, marketing_notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["version"],
                    r["from_ref"],
                    created_at,
                    r["readiness_score"],
                    r["recommendation"],
                    r["suggested_bump"],
                    r["internal_announcement"],
                    r["customer_notes"],
                    r["marketing_notes"],
                ),
            )
            release_id = cur.lastrowid

            for t in r["traceability"]:
                conn.execute(
                    """INSERT INTO traceability_rows
                       (release_id, short_hash, description, commit_type, is_breaking,
                        jira_keys, jira_statuses, pr_number, pr_url,
                        ci_total, ci_passed, ci_failed, ci_failed_names)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        release_id,
                        t["short_hash"],
                        t["description"],
                        t["commit_type"],
                        1 if t["is_breaking"] else 0,
                        "[]",
                        "{}",
                        t.get("pr_number"),
                        t.get("pr_url"),
                        10,
                        10,
                        0,
                        "[]",
                    ),
                )
            seeded += 1
        conn.commit()
    return seeded
