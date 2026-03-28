English | [中文](README.cn.md)

# Video App - Full-Stack Video Management Application

- A simple local video metadata management, streaming, and browsing web UI application with support for video categorization, tag management, search, and web playback. 

- By mapping your existing video directories to the application in the configuration, it will automatically scan, generate thumbnails, and allow you to manage video metadata (title, favorites, tags, etc.) through a user-friendly interface.

## ✨ Features

- 🏷️ **Tag Management** - Video tagging system with batch operations support
- 📁 **Directory Browsing** - Multi-source file system browsing with category-level classification
- 🖼️ **Thumbnail Generation** - Automatic thumbnail generation using ffmpeg
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
| pytest | Unit Testing (Refactoring in progress) |

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
```

Edit `config.yaml` to ensure `resource_paths` matches the container paths:

```yaml
resource_paths:
  Local-resource:              # category name
    Resource-1: /your/video/path1   # pseudo_name: host_path
    Resource-2: /your/video/path2

root_path: /app/resources
```

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

Edit `config.yaml`:

```yaml
# Video resource paths (use local absolute paths)
resource_paths:
  Local-resource:                    # category name
    Resource-1: /your/video/path1   # pseudo_name: local absolute path
    Resource-2: /your/video/path2

# Comment out root_path for local development
# root_path: /app/resources

# MongoDB configuration
mongo:
  host: localhost
  port: 27017
  database: video_tag_db
  username: your_username    # Leave empty if no auth
  password: your_password    # Leave empty if no auth
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

```yaml
# Video resource path mapping (category -> pseudo_name -> host_path)
# Docker deployment: host_path is the host machine path, requires docker-compose.yml volumes + root_path
# Manual installation: host_path is the local absolute path, comment out root_path
resource_paths:
  Local-resource:                              # category name
    Resource-1: /app/resources/Resource-1      # Docker deployment
    Resource-2: /app/resources/Resource-2
    # Resource-1: D:/videos/folder1            # Manual installation example
    # Resource-2: E:/videos/folder2

# Required for Docker deployment, comment out for manual installation
root_path: /app/resources

# Cache configuration
cache_config:
  max_size: 2048        # Maximum cache entries
  ttl: 300              # Cache expiration time (seconds)
  cache_type: cachetools # Cache implementation type

# ffmpeg/ffprobe concurrency limit
ffmpeg_semaphore_limit: 4

# Pagination configuration
page_size_default:
  homepage_videos: 5
  homepage_tags: 50
  searchpage: 15

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

# Logging configuration
logging:
  log_dir: logs
  rotation: "10 MB"
  retention: "30 days"

# MongoDB configuration
# Docker deployment will override host via environment variable
mongo:
  host: localhost       # Overridden by MONGO_HOST env var in Docker
  port: 27017
  database: video_tag_db
  username: ""          # Leave empty if no auth
  password: ""
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

```
video-app/
├── main.py                          # Backend entry (localhost:12000)
├── config.yaml                      # Configuration file
├── Dockerfile                       # Docker image config
├── docker-compose.yml               # Docker compose config
├── migrations/                      # Database migration scripts
│   └── add_category_field.py       # Category field migration
├── src/
│   ├── app.py                      # FastAPI app factory, CORS, lifespan
│   ├── config.py                   # Configuration management (Settings)
│   ├── errors.py                   # Custom exceptions
│   ├── logger.py                   # Logging config (loguru)
│   ├── db/
│   │   ├── setup_mongo.py         # AsyncMongoClient + Beanie init
│   │   └── models/
│   │       ├── Video_model.py     # VideoModel (with category field)
│   │       ├── VideoTag_model.py  # VideoTagModel
│   │       └── DirMetadata_model.py # DirMetadataModel (with category field)
│   ├── router/
│   │   └── video_router.py        # /video/stream/{id}, /video/thumbnail
│   ├── schema/
│   │   ├── query_schema.py        # GraphQL query root
│   │   ├── mutation_schema.py     # GraphQL mutation root
│   │   ├── subscription_schema.py # GraphQL subscription root
│   │   ├── strawberry_schema.py   # Schema assembly
│   │   └── types/
│   │       ├── video_type.py      # Video, VideoTag types
│   │       ├── search_type.py     # Search-related types
│   │       ├── fileBrowse_type.py # File browse types
│   │       └── pydantic_types/    # Input validation models (Pydantic)
│   │           ├── video_type.py
│   │           ├── search_type.py
│   │           ├── fileBrowe_type.py   # RelativePath parsing (3-level path)
│   │           └── batch_operation_type.py
│   ├── resolvers/
│   │   ├── query_resolver.py          # Query resolvers
│   │   ├── mutation_resolver.py       # Mutation resolvers
│   │   ├── subscription_resolver.py   # Subscription resolvers (batch ops)
│   │   └── video_stream_resolver.py   # Video streaming (Range, chunked)
│   └── services/
│       ├── browse_file_service.py     # Directory browsing (3-level nav)
│       ├── batch_operation_service.py # Batch update/delete
│       ├── dir_metadata_service.py    # Directory metadata (size/mtime)
│       ├── tag_operation_service.py   # Tag count management
│       ├── thumbnail_service.py       # Thumbnail generation (ffmpeg/ffprobe)
│       ├── path_convert_service.py    # AbsolutePath abstraction
│       ├── cache/                     # Cache service
│       │   ├── base_cache.py         # Cache abstract base class
│       │   ├── cachetools_cache.py   # cachetools implementation
│       │   └── cache_service.py      # Cache factory/dispatcher
│       └── resource_handler/          # Resource handler (IO abstraction)
│           ├── base_resource_handler.py  # Abstract base class
│           ├── base_file_entry.py        # File entry abstraction + FileStat
│           ├── resource_handler_service.py # Handler factory/dispatcher
│           └── local_fs/                  # Local filesystem implementation
│               ├── local_fs_handler.py    # LocalFS handler
│               └── local_fs_file_entry.py # LocalFS file entry
└── tests/                           # Test files
```

#### Frontend

```
front-end/video-app-front/src/app/
├── app.ts, app.routes.ts, app.config.ts   # Root component, routes, Apollo config
├── core/graphql/
│   ├── documents/                         # GraphQL operation documents
│   │   ├── queries.graphql.ts
│   │   ├── mutations.graphql.ts
│   │   └── subscription.graphql.ts
│   └── generated/graphql.ts              # graphql-codegen auto-generated
├── pages/
│   ├── homepage/                          # Home (Loved/Latest/MostViewed + Top tags)
│   ├── search/                            # Search page
│   ├── video-player/                      # Video player (video.js)
│   └── management/                        # Management (directory browse/batch ops)
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
│   │   ├── pagination/                    # Pagination (loading state support)
│   │   ├── bottom-toolbar/                # Bottom toolbar
│   │   ├── toast-displayer/               # Toast display component
│   │   ├── sidebar/                       # Sidebar
│   │   └── header/                        # Top navigation bar
│   ├── interceptor/
│   │   └── ImageRequest.interceptor.ts    # Image request interceptor
│   └── models/                            # Type definitions
│       ├── GQL-result.model.ts            # ResultState<T>
│       ├── management.model.ts
│       ├── search.model.ts
│       ├── events.model.ts
│       ├── panels.model.ts
│       └── toast.model.ts
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
| `directoryMetadata` | Get directory metadata (size/mtime) |

### Mutations

| Mutation | Description |
|----------|-------------|
| `updateVideoMetadata` | Update video metadata |
| `deleteVideo` | Delete video |
| `recordVideoView` | Record view count |

### Subscriptions

| Subscription | Description |
|--------------|-------------|
| `batchUpdate` | Batch update videos (streaming progress) |
| `batchDelete` | Batch delete videos (streaming progress) |

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video/stream/{id}` | GET | Video stream (supports Range requests, 1MB chunks) |
| `/video/thumbnail` | GET | Get thumbnail |