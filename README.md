English | [中文](README.cn.md)

# Video App - Full-Stack Video Management Application

- A full-stack video metadata management, streaming, and browsing web UI application with support for video categorization, tag management, search, and web playback. Supports both local filesystem and S3-compatible storage (MinIO, RustFS, etc.).

- By mapping your existing video directories or S3 buckets to the application in the configuration, it will automatically scan, generate thumbnails, and allow you to manage video metadata (title, favorites, tags, etc.) through a user-friendly interface.

## ✨ Features

- 🏷️ **Tag Management** - Video tagging system with batch operations support
- 📁 **Directory Browsing** - Multi-source file system browsing with category-level classification
- 🖼️ **Thumbnail Generation** - Automatic thumbnail generation using ffmpeg, with optional S3 persistent storage
- ☁️ **S3-Compatible Storage** - Support for S3-compatible storage backends (MinIO, RustFS, etc.) via Strategy Pattern
- 📦 **File Migration** - Migrate video files between storage locations (local/S3), with preflight checks, conflict handling and a state machine–driven task lifecycle
- ⚙️ **Background Tasks** - Migrations run in a process-wide worker pool, independent of any client connection: closing the tab or refreshing the page never interrupts a task, progress subscriptions are pure observers, and tasks left unfinished by a restart resume from the phase they stopped at
- ❤️ **Favorites** - Video favorites and view statistics
- 📱 **Responsive Design** - Adapts to various screen sizes

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | Web Framework |
| Strawberry | GraphQL Server |
| MongoDB | Database |
| Beanie | MongoDB ODM |
| pytest | Testing (unit + integration + GraphQL) |

### Frontend
| Technology | Purpose |
|------------|---------|
| Angular 21 | Frontend Framework (Standalone) |
| Apollo Client | GraphQL Client |
| Angular Material | UI Component Library |
| Tailwind CSS v4 | Styling Framework |
| Video.js | Video Player |

### Deployment
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| docker-compose | Container Orchestration |
| ffmpeg | Thumbnail Generation |
| RustFS / MinIO | S3-Compatible Object Storage (optional) |


## 🚀 Quick Start

### Docker Deployment (Recommended)

#### Requirements
- Docker & Docker Compose

#### Steps

**1. Clone the project**
```bash
git clone <repository-url>
cd video-app
```

**2. Configure video resource paths**

Edit `docker-compose.yml` to modify the backend service volumes mapping:

```yaml
backend:
  volumes:
    - ./logs:/app/logs
    # Map host video directories to container
    # Format: host_path:/app/resources/CategoryName/PseudoName
    - /your/video/path1:/app/resources/Local-resource/Resource-1
    - /your/video/path2:/app/resources/Local-resource/Resource-2
  environment:
    - ROOT_PATH=/app/resources
    - MONGO_HOST=mongodb
    # S3 storage (optional, override config.yaml defaults for Docker networking)
    # - S3_RESOURCE_1_ENDPOINT_URL=http://rustfs:9000
    # - S3_RESOURCE_1_ACCESS_KEY=rustfsadmin
    # - S3_RESOURCE_1_SECRET_KEY=rustfsadmin
    # - S3_RESOURCE_1_BUCKET=video-app
```

Edit `config.yaml` to configure resource paths (envyaml `$VAR|default` syntax is supported):

```yaml
resource_paths:
  Local-resource:              # category name
    Resource-1: /your/video/path1   # pseudo_name: host_path
    Resource-2: /your/video/path2
```

> **Note**: The `docker-compose.yml` includes a RustFS service (S3-compatible storage) by default. To enable S3 storage, uncomment the S3 environment variables above and the `handler_config` / `thumbnail_config` sections in `config.yaml`.

**3. Start services**
```bash
docker-compose up -d
```

Access `http://localhost` to use the application.

**4. Start docker-compose in watch mode (for development)**
```bash
docker-compose watch
# or
docker-compose up --build -d
```

---

### Manual Installation (Development)

#### Requirements

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 24+
- MongoDB 6.0+
- ffmpeg (for thumbnail generation)

#### Steps

**1. Install uv**
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Prepare MongoDB**

- Ensure MongoDB service is running and note the connection details.
- You can use a locally installed MongoDB or run it via Docker.
- Optionally create a user with sufficient permissions (CRUD, collection, index operations) in the `video_tag_db` database, or run without authentication.

**3. Configure backend**

Edit `config.yaml` (uses [envyaml](https://github.com/thesimj/envyaml) `$VAR|default` syntax):

```yaml
# ROOT_PATH should be empty for local development
ROOT_PATH: $ROOT_PATH|

# Video resource paths (use local absolute paths)
resource_paths:
  Local-resource:                    # category name
    Resource-1: /your/video/path1   # pseudo_name: local absolute path
    Resource-2: /your/video/path2

# MongoDB configuration
mongo:
  host: $MONGO_HOST|localhost
  port: $MONGO_PORT|27017
  database: $MONGO_DATABASE|video_tag_db
  username: $MONGO_USERNAME|         # Leave empty if no auth
  password: $MONGO_PASSWORD|

# Optional: S3-compatible storage (MinIO, RustFS, etc.)
# See "Full config.yaml Configuration" section for details
```

**4. Start backend**
```bash
# Install dependencies
uv sync

# Start service
uv run main.py
```

Backend will run at `http://localhost:12000`

**5. Configure frontend**

Edit `front-end/video-app-front/src/environments/environment.development.ts`:

```typescript
export const environment = {
    production: false,
    backend_api: "http://localhost:12000",  // Backend address
    // ... keep other settings as default
}
```

**6. Start frontend**
```bash
cd front-end/video-app-front

# Install dependencies
npm install

# Regenerate code if backend GraphQL schema was modified
npm run codegen

# Start development server
npm start
```

Frontend will run at `http://localhost:4200`

## ⚙️ Configuration

### Full config.yaml Configuration

Configuration uses [envyaml](https://github.com/thesimj/envyaml) syntax: `$ENV_VAR|default_value` for environment variable substitution with defaults.

```yaml
# Container mount base path (set via env var in Docker, leave empty for local dev)
ROOT_PATH: $ROOT_PATH|

# Video resource path mapping (category -> pseudo_name -> host_path)
resource_paths:
  Local-resource:                              # Local filesystem category
    Resource-1: /your/video/path1             # pseudo_name: host_path
    Resource-2: /your/video/path2
  # S3-resource:                              # S3-compatible storage category
  #   Resource-1: /                           # host_path is unused for S3

# S3 handler configuration (only for categories that need it)
# Categories with handler_config use S3ResourceHandler; others use LocalFSResourceHandler
# handler_config:
#   S3-resource:
#     Resource-1:
#       endpoint_url: $S3_RESOURCE_1_ENDPOINT_URL|http://localhost:9000
#       access_key: $S3_RESOURCE_1_ACCESS_KEY|admin
#       secret_key: $S3_RESOURCE_1_SECRET_KEY|admin
#       bucket: $S3_RESOURCE_1_BUCKET|video-app
#       region: $S3_RESOURCE_1_REGION|us-east-1

# Thumbnail persistent storage (optional, requires S3-compatible storage)
# If not configured, thumbnails are generated on-the-fly with ffmpeg (no persistence)
# thumbnail_config:
#   storage_category: S3-resource
#   storage_pseudo_name: Resource-1

# Cache configuration
cache_config:
  max_size: 2048        # Maximum cache entries
  ttl: 300              # Cache expiration time (seconds)
  cache_type: cachetools # Cache implementation type

# ffmpeg/ffprobe concurrency limit (effective value is max(ffmpeg_semaphore_limit, cpu_count // 2))
ffmpeg_semaphore_limit: 4

# Search suggestion limits
suggestion_limit:
  name: 10
  author: 10
  tag: 20

# Supported video formats
video_extensions:
  - .mp4
  - .avi
  - .mkv
  - .mov
  - .wmv
  - .flv
  - .webm
  - .m4v
  - .mpg
  - .mpeg

# Validation rules (must sync with frontend environment.ts)
validation:
  name_max_length: 200
  author_max_length: 50
  introduction_max_length: 2000
  tag_max_length: 30
  max_tags_count: 50
  page_number_min: 1
  page_number_max: 10000
  series_name_max_length: 100

# Background task runner
tasks:
  max_concurrent: 2            # Tasks running at once; also the worker pool size.
                               # Migrations are IO-bound, so a high value mostly makes
                               # them compete for bandwidth.
  progress_flush_interval: 3.0 # Seconds between progress writes to MongoDB. Live progress
                               # is kept in memory, so this only bounds how stale the task
                               # list looks to a client with no active subscription.

# Logging configuration
logging:
  log_dir: logs
  rotation: "10 MB"
  retention: "30 days"

# MongoDB configuration
mongo:
  host: $MONGO_HOST|localhost
  port: $MONGO_PORT|27017
  database: $MONGO_DATABASE|video_tag_db
  username: $MONGO_USERNAME|
  password: $MONGO_PASSWORD|
```

### Frontend Environment Configuration

**Development** (`environment.development.ts`):
```typescript
backend_api: "http://localhost:12000"  // Points to local backend
```

**Production** (`environment.ts`):
```typescript
backend_api: ""  // Empty string, uses relative path (nginx proxy)
```

## 📖 Reference

### Project Structure

#### Backend

The backend is organised by business capability, with a strictly one-way dependency chain:

```
resolvers/ + schema/   GraphQL delivery — validate, delegate, map
        ↓
features/              catalog · browsing · playback · migration
        ↓
platform/              storage · media · cache · jobs (reusable, knows no feature)
```

```
video-app/
├── main.py                          # Backend entry (localhost:12000)
├── config.yaml                      # Configuration file (envyaml syntax)
├── Dockerfile                       # Docker image config
├── docker-compose.yml               # Docker compose config
├── src/
│   ├── app.py                      # FastAPI app factory, CORS, lifespan, GraphQL router mount
│   ├── config.py                   # Configuration management (Settings, envyaml)
│   ├── context.py                  # DI container: service factories + GraphQL context (13 services)
│   ├── errors.py                   # Custom exceptions
│   ├── logger.py                   # Logging config (loguru)
│   │
│   ├── db/
│   │   └── setup_mongo.py         # AsyncMongoClient + Beanie init (registers the 4 documents)
│   │
│   ├── platform/                   # ── Reusable core; imports no feature ──
│   │   ├── cache/
│   │   │   ├── base_cache.py           # Cache abstract base class
│   │   │   ├── cachetools_cache.py     # cachetools implementation
│   │   │   └── cache_service.py        # Cache factory/dispatcher
│   │   ├── media/
│   │   │   └── ffmpeg_service.py       # ffmpeg/ffprobe wrapper: thumbnail, duration, on-the-fly transcoding (semaphore-gated)
│   │   ├── storage/                    # Resource handler (Strategy Pattern)
│   │   │   ├── base_resource_handler.py  # Abstract base class
│   │   │   ├── base_file_entry.py        # File entry abstraction + FileStat
│   │   │   ├── absolute_path.py          # AbsolutePath abstraction (DB / FS format conversion)
│   │   │   ├── resource_handler_service.py # Handler factory/dispatcher
│   │   │   ├── local_fs/                 # Local filesystem implementation
│   │   │   │   ├── local_fs_handler.py
│   │   │   │   └── local_fs_file_entry.py
│   │   │   └── s3/                       # S3-compatible storage implementation
│   │   │       ├── s3_handler.py         # boto3 resource API
│   │   │       └── s3_file_entry.py
│   │   └── jobs/                       # Generic background-task template
│   │       ├── task_model.py           # TaskStatus + BaseTaskModel (progress via accessors)
│   │       ├── progress.py             # ProgressFrame — unit-agnostic current/total
│   │       ├── state_machine.py        # TaskStateMachine[TTask] — three-phase lifecycle, crash recovery
│   │       └── task_runner.py          # FIFO queue, worker pool, progress broadcast, recovery on boot
│   │
│   ├── features/                   # ── Business capabilities ──
│   │   ├── catalog/                    # Video metadata: search, autocomplete, edit, delete, views
│   │   │   ├── video.py                # VideoModel (category, series, duration fields)
│   │   │   ├── video_tag.py            # VideoTagModel
│   │   │   ├── catalog_service.py      # Search / suggest / update / record view / delete
│   │   │   ├── series_service.py       # Series search + ordered listing
│   │   │   └── tag_operation_service.py# Tag reference-count management
│   │   ├── browsing/                   # Directory browsing and batch operations
│   │   │   ├── dir_metadata.py         # DirMetadataModel
│   │   │   ├── dir_metadata_service.py # Directory metadata (size/mtime, Cache-Aside)
│   │   │   ├── browse_file_service.py  # 3-level navigation, batched document sync
│   │   │   └── batch_operation_service.py # Batch update/delete (streaming progress)
│   │   ├── playback/                   # Streaming and thumbnails (REST)
│   │   │   ├── video_stream_service.py # Range streaming, chunked, transcoded fallback
│   │   │   ├── thumbnail_service.py    # ffmpeg + optional S3 persistence
│   │   │   └── video_router.py         # /video/stream/{id}, /video/thumbnail
│   │   └── migration/                  # File migration
│   │       ├── migration_task.py       # MigrationTaskModel (extends BaseTaskModel)
│   │       └── migration_service.py    # TaskStateMachine subclass: copy, repoint DB, clean up
│   │
│   ├── resolvers/                  # ── GraphQL delivery ──
│   │   ├── query_resolver.py
│   │   ├── mutation_resolver.py
│   │   ├── subscription_resolver.py    # Batch operation subscriptions
│   │   └── migration_resolver.py       # Preflight, CRUD, progress/retry subscriptions
│   │
│   └── schema/
│       ├── query_schema.py             # GraphQL query root
│       ├── mutation_schema.py          # GraphQL mutation root
│       ├── subscription_schema.py      # GraphQL subscription root
│       ├── strawberry_schema.py        # Schema assembly + custom scalar config (BigInt) + error logging
│       └── types/
│           ├── video_type.py           # Video, VideoTag types
│           ├── search_type.py          # Search types (enums registered from catalog)
│           ├── fileBrowse_type.py      # File browse / batch operation types
│           ├── migration_type.py       # Migration task types + preflight result
│           ├── scalars.py              # Custom scalars (BigInt)
│           └── pydantic_types/         # GraphQL input contracts (Pydantic)
│               ├── video_type.py
│               ├── search_type.py
│               ├── fileBrowe_type.py   # RelativePath parsing (3-level path)
│               ├── batch_operation_type.py
│               └── migration_type.py
└── tests/                           # Test suite, 449 cases (pytest --strict-markers)
    ├── unit/
    │   ├── test_architecture.py     # Dependency-direction guards (AST scan)
    │   ├── jobs/                    # Task template: model, progress frame, state machine
    │   └── services/                # Per-service unit tests (@pytest.mark.unit)
    ├── graphql/                     # GraphQL resolver tests (queries, mutations, subscriptions)
    └── integration/                 # End-to-end integration tests
```

> **Dependency direction is enforced, not just documented.** `tests/unit/test_architecture.py` parses every module's imports and fails the build if a feature imports strawberry or a GraphQL type, if a resolver imports a document model, or if `platform/` imports a feature. A reversed import is invisible in review and in green tests — it only surfaces later as a service that cannot be reused and a file-walk test that has to build a GraphQL schema.

> **Delivery types are mapped, never returned directly.** Features return their own dataclasses and documents; the GraphQL layer converts them (`Video.from_mongoDB`, `BatchOperationStatus.from_service`, `MigrationProgressStatus.from_service`, ...). That mapping doubles as a shield for the published schema: the task template reports progress as unit-agnostic `current`/`total`, yet the API still publishes `bytesTransferred`/`totalBytes`.

> **Dependency injection**: `src/context.py` provides FastAPI `Depends`-based factories for every service and assembles them into the GraphQL `context` (keyed by `ContextEnum`). Resolvers retrieve services with `get_context_value(info, ContextEnum.XXX)`; HTTP routes use the exported `*Dep` annotations (e.g. `ThumbnailServiceDep`, `VideoStreamServiceDep`).

> **Adding a background task type**: subclass `BaseTaskModel` (declaring its own `Settings.name`) and `TaskStateMachine[YourModel]`, implement the three phases, then register it with `TaskRunner.register_executor(key, executor)`. The scheduler needs no changes — this is covered by a test that drives a non-migration task type through the template.

#### Frontend

```
front-end/video-app-front/src/app/
├── app.ts, app.routes.ts, app.config.ts   # Root component, routes, Apollo config
├── core/graphql/
│   ├── documents/                         # GraphQL operation documents
│   │   ├── queries.graphql.ts
│   │   ├── mutations.graphql.ts
│   │   ├── subscription.graphql.ts
│   │   └── migration.graphql.ts          # Migration operations (preflight, CRUD, progress)
│   └── generated/graphql.ts              # graphql-codegen auto-generated (BigInt → string)
├── pages/
│   ├── homepage/                          # Home (Loved/Latest/MostViewed + Top tags)
│   ├── search/                            # Search page
│   ├── video-player/                      # Video player (video.js)
│   ├── file-browser/                      # File browser (directory browse/batch ops)
│   └── management/                        # Management (Tasks tab + Settings tab)
├── services/
│   ├── GQL-service/                       # GraphQL operations service
│   ├── Http-client-service/               # HTTP client service
│   ├── Page-state-service/                # Page state management
│   ├── path-history-service/              # Path history management
│   ├── theme-service/                     # Theme switching
│   ├── toast-service/                     # Toast notifications
│   ├── validation-service/                # Input validation service
│   └── video-update-event-service/        # Video update events
├── shared/
│   ├── components/
│   │   ├── video-card/                    # 16:9 thumbnail + skeleton card
│   │   ├── video-edit-panel/              # Dual-mode (full/filter) edit panel
│   │   ├── batch-operation-panel/         # Batch tag operation panel
│   │   ├── delete-check-panel/            # Delete confirmation dialog
│   │   ├── file-browse-table/             # File browse table (resizable columns)
│   │   ├── migration-panel/              # Migration dialog (select target + preflight)
│   │   ├── migration-task-list/          # Migration task list with status/progress
│   │   ├── series-panel/                 # Series management panel
│   │   ├── series-reorder-list/          # Series reorder drag list
│   │   ├── pagination/                    # Pagination (loading state support)
│   │   ├── bottom-toolbar/                # Bottom toolbar
│   │   ├── toast-displayer/               # Toast display (Error/Warning/Success)
│   │   ├── sidebar/                       # Sidebar
│   │   └── header/                        # Top navigation bar
│   ├── interceptor/
│   │   └── ImageRequest.interceptor.ts    # Image request interceptor
│   └── models/                            # Type definitions
│       ├── GQL-result.model.ts            # ResultState<T>
│       ├── management.model.ts
│       ├── migration.model.ts             # Migration task models + status map
│       ├── search.model.ts
│       ├── events.model.ts
│       ├── panels.model.ts
│       └── toast.model.ts                 # ToastType (Error/Warning/Success)
├── route-resolver/
│   └── video-player.resolver.ts           # Route guard
└── environments/                          # Environment config
```

### GraphQL Endpoint

```
http://localhost:12000/graphql
```

### Queries

| Query | Description |
|-------|-------------|
| `SearchVideos` | Search videos (with category filtering) |
| `getTopTags` | Get top tags |
| `getSuggestions` | Get search suggestions |
| `getVideoById` | Get video by ID |
| `browseDirectory` | Browse directory (category -> pseudo_name -> subdirs) |
| `getDirectoryMetadata` | Get directory metadata (size/mtime) |
| `searchSeriesByPrefix` | Prefix-search series names (case-insensitive, distinct over `seriesName`) |
| `getSeriesVideos` | List videos in a series, ordered by `seriesOrder` |
| `getMigrationTasks` | List migration tasks with pagination and status filtering |

### Mutations

| Mutation | Description |
|----------|-------------|
| `updateVideoMetadata` | Update video metadata (incl. series name/order) |
| `deleteVideo` | Delete video |
| `recordVideoView` | Record view count |
| `migrationPreflight` | Pre-migration validation (space, conflicts, duplicate check) |
| `createMigrationTask` | Create a file migration task and queue it on the background runner |
| `cancelMigrationTask` | Cancel a migration task (immediate while queued, cooperative once copying) |

### Subscriptions

| Subscription | Description |
|--------------|-------------|
| `batchUpdateSubscription` | Batch update videos (streaming progress) |
| `batchDeleteSubscription` | Batch delete videos (streaming progress) |
| `migrationProgressSubscription` | Observe a background migration's progress. Subscribing never starts the task and unsubscribing never stops it, so refreshing the page or watching from several tabs is safe |
| `migrationRetrySubscription` | Re-queue a failed migration, resuming from the phase it failed at, then observe its progress |

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video/stream/{video_id}` | GET | Video stream — Range-supported direct streaming (1MB chunks) for `mp4`/`webm`; on-the-fly fragmented MP4 transcoding for other formats |
| `/video/thumbnail?video_id=...` | GET | Get thumbnail (served from S3 if `thumbnail_config` is set, otherwise generated on-the-fly) |