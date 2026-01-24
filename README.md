English | [中文](README.cn.md)

# Video App - Full-Stack Video Management Application

A simple local video metadata management, streaming, and browsing web UI application with support for video categorization, tag management, search, and web playback.

## ✨ Features

- 🏷️ **Tag Management** - Video tagging system with batch operations support
- 📁 **Directory Browsing** - Local file system directory browsing
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
| pytest | Unit Testing |

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

## 📁 Project Structure

```
video-app/
├── main.py                    # Backend entry (localhost:12000)
├── config.yaml               # Configuration file
├── Dockerfile                # Docker image config
├── docker-compose.yml        # Docker compose config
├── src/                      # Backend source code
│   ├── app.py               # FastAPI application factory
│   ├── config.py            # Configuration management
│   ├── errors.py            # Custom exceptions
│   ├── db/                  # Database layer
│   │   ├── setup_mongo.py   # MongoDB connection
│   │   └── models/          # Data models
│   ├── router/              # HTTP routes
│   ├── schema/              # GraphQL Schema
│   └── resolvers/           # GraphQL resolvers
├── tests/                    # Test files
└── front-end/               # Frontend project
    └── video-app-front/
        └── src/app/
            ├── core/graphql/    # GraphQL operations
            ├── pages/           # Page components
            ├── services/        # Service layer
            └── shared/          # Shared components
```

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
    # Format: host_path:container_path
    - /your/video/path1:/app/resources/Resource-1
    - /your/video/path2:/app/resources/Resource-2
```

Edit `config.yaml` to ensure `resource_paths` matches the container paths:

```yaml
resource_paths:
  Resource-1: /your/video/path1
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
  Resource-1: /your/video/path1
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
# Video resource path mapping
# Docker deployment: use container paths (must match docker-compose.yml volumes)
# Manual installation: use local absolute paths
resource_paths:
  Resource-1: /app/resources/Resource-1  # Docker
  Resource-2: /app/resources/Resource-2
  # Resource-1: D:/videos/folder1        # Manual installation example
  # Resource-2: E:/videos/folder2

# Required for Docker deployment, comment out for manual installation
root_path: /app/resources

# Cache configuration
cache_config:
  max_size: 2048    # Maximum cache entries
  ttl: 300          # Cache expiration time (seconds)

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

## 📖 API Documentation

### GraphQL Endpoint

```
http://localhost:12000/graphql
```

### Queries

| Query | Description |
|-------|-------------|
| `SearchVideos` | Search videos |
| `getTopTags` | Get top tags |
| `getSuggestions` | Get search suggestions |
| `getVideoById` | Get video by ID |
| `browseDirectory` | Browse directory |

### Mutations

| Mutation | Description |
|----------|-------------|
| `updateVideoMetadata` | Update video metadata |
| `batchUpdate` | Batch update |
| `recordVideoView` | Record view count |
| `deleteVideo` | Delete video |

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video/stream/{id}` | GET | Video stream (supports Range requests, 1MB chunks) |
| `/video/thumbnail` | GET | Get thumbnail |