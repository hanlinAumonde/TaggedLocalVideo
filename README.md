# Video App - 全栈视频管理应用

一个简单的本地视频元数据管理、流传输和浏览webUI应用，支持视频分类、标签管理、搜索和网页播放。

## ✨ 功能特性

- 🏷️ **标签管理** - 视频标签系统，支持批量操作
- 📁 **目录浏览** - 本地文件系统目录浏览
- 🖼️ **缩略图生成** - 基于ffmpeg的自动缩略图生成
- ❤️ **收藏功能** - 视频收藏与播放统计
- 📱 **响应式设计** - 适配多种屏幕尺寸

## 🛠️ 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| FastAPI | Web框架 |
| Strawberry | GraphQL服务 |
| MongoDB | 数据库 |
| Beanie | MongoDB ODM |
| pytest | 单元测试 |

### 前端
| 技术 | 用途 |
|------|------|
| Angular 21 | 前端框架 (Standalone) |
| Apollo Client | GraphQL客户端 |
| Angular Material | UI组件库 |
| Tailwind CSS v4 | 样式框架 |
| Video.js | 视频播放器 |

### 部署
| 技术 | 用途 |
|------|------|
| Docker | 容器化 |
| docker-compose | 容器编排 |
| ffmpeg | 缩略图生成 |

## 📁 项目结构

```
video-app/
├── main.py                    # 后端入口 (localhost:12000)
├── config.yaml               # 配置文件
├── Dockerfile                # Docker镜像配置
├── docker-compose.yml        # Docker编排配置
├── src/                      # 后端源码
│   ├── app.py               # FastAPI应用工厂
│   ├── config.py            # 配置管理
│   ├── errors.py            # 自定义异常
│   ├── db/                  # 数据库层
│   │   ├── setup_mongo.py   # MongoDB连接
│   │   └── models/          # 数据模型
│   ├── router/              # HTTP路由
│   ├── schema/              # GraphQL Schema
│   └── resolvers/           # GraphQL解析器
├── tests/                    # 测试文件
└── front-end/               # 前端项目
    └── video-app-front/
        └── src/app/
            ├── core/graphql/    # GraphQL操作
            ├── pages/           # 页面组件
            ├── services/        # 服务层
            └── shared/          # 共享组件
```

## 🚀 快速开始

### 使用 Docker 部署（推荐）

#### 环境要求
- Docker & Docker Compose

#### 步骤

**1. 克隆项目**
```bash
git clone <repository-url>
cd video-app
```

**2. 配置视频资源路径**

编辑 `docker-compose.yml`，修改后端服务的 volumes 映射：

```yaml
backend:
  volumes:
    - ./logs:/app/logs
    # 将宿主机的视频目录映射到容器内
    # 格式: 宿主机路径:容器内路径
    - /your/video/path1:/app/resources/Resource-1
    - /your/video/path2:/app/resources/Resource-2
```

编辑 `config.yaml`，确保 `resource_paths` 与容器内路径一致：

```yaml
resource_paths:
  Resource-1: /your/video/path1
  Resource-2: /your/video/path2

root_path: /app/resources
```

**3. 启动服务**
```bash
docker-compose up -d
```

访问 `http://localhost` 即可使用。

**4. 以watch模式启动docker-compose（便于开发调试）**
```bash
docker-compose watch
# or
docker-compose up --build -d
```

---

### 手动安装（开发环境）

#### 环境要求

- [uv](https://docs.astral.sh/uv/) (Python 包管理器)
- Node.js 24+
- MongoDB 6.0+
- ffmpeg (用于缩略图生成)

#### 步骤

**1. 安装 uv**
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. 准备 MongoDB**

- 确保 MongoDB 服务已启动，并记录连接信息。
- 可以使用本地安装的 MongoDB，或使用 Docker 运行
- 可在`video_tag_db`数据库中创建有足够权限（CRUD，集合、索引操作）的用户（如有需要），或不设置认证。


**3. 配置后端**

编辑 `config.yaml`：

```yaml
# 视频资源路径（使用本地绝对路径）
resource_paths:
  Resource-1: /your/video/path1
  Resource-2: /your/video/path2

# 本地开发时注释掉 root_path
# root_path: /app/resources

# MongoDB 配置
mongo:
  host: localhost
  port: 27017
  database: video_tag_db
  username: your_username    # 如无认证可留空
  password: your_password    # 如无认证可留空
```

**4. 启动后端**
```bash
# 安装依赖
uv sync

# 启动服务
uv run main.py
```

后端将运行在 `http://localhost:12000`

**5. 配置前端**

编辑 `front-end/video-app-front/src/environments/environment.development.ts`：

```typescript
export const environment = {
    production: false,
    backend_api: "http://localhost:12000",  // 后端地址
    // ... 其他配置保持默认
}
```

**6. 启动前端**
```bash
cd front-end/video-app-front

# 安装依赖
npm install

# 若开发中修改了后端 GraphQL schema，需重新生成代码
npm run codegen

# 启动开发服务器
npm start
```

前端将运行在 `http://localhost:4200`

## ⚙️ 配置说明

### config.yaml 完整配置

```yaml
# 视频资源路径映射
# Docker部署: 使用容器内路径 (需配合docker-compose.yml的volumes)
# 手动安装: 使用本地绝对路径
resource_paths:
  Resource-1: /app/resources/Resource-1  # Docker
  Resource-2: /app/resources/Resource-2
  # Resource-1: D:/videos/folder1        # 手动安装示例
  # Resource-2: E:/videos/folder2

# Docker部署时需要设置，手动安装时注释掉
root_path: /app/resources

# 缓存配置
cache_config:
  max_size: 2048    # 最大缓存条目数
  ttl: 300          # 缓存过期时间（秒）

# 分页配置
page_size_default:
  homepage_videos: 5
  homepage_tags: 50
  searchpage: 15

# 搜索建议数量限制
suggestion_limit:
  name: 10
  author: 10
  tag: 20

# 支持的视频格式
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

# 验证规则 (需与前端 environment.ts 保持同步)
validation:
  name_max_length: 200
  author_max_length: 50
  introduction_max_length: 2000
  tag_max_length: 30
  max_tags_count: 50
  page_number_min: 1
  page_number_max: 10000

# 日志配置
logging:
  log_dir: logs
  rotation: "10 MB"
  retention: "30 days"

# MongoDB 配置
# Docker部署时会通过环境变量覆盖 host
mongo:
  host: localhost       # Docker时会被MONGO_HOST环境变量覆盖
  port: 27017
  database: video_tag_db
  username: ""          # 如无认证可留空
  password: ""
```

### 前端环境配置

**开发环境** (`environment.development.ts`):
```typescript
backend_api: "http://localhost:12000"  // 指向本地后端
```

**生产环境** (`environment.ts`):
```typescript
backend_api: ""  // 空字符串，使用相对路径（nginx代理）
```

## 📖 API 文档

### GraphQL 端点

```
http://localhost:12000/graphql
```


### 查询 (Queries)

| 查询 | 描述 |
|------|------|
| `SearchVideos` | 搜索视频 |
| `getTopTags` | 获取热门标签 |
| `getSuggestions` | 获取搜索建议 |
| `getVideoById` | 根据ID获取视频 |
| `browseDirectory` | 浏览目录 |

### 变更 (Mutations)

| 变更 | 描述 |
|------|------|
| `updateVideoMetadata` | 更新视频元数据 |
| `batchUpdate` | 批量更新 |
| `recordVideoView` | 记录播放次数 |
| `deleteVideo` | 删除视频 |

### HTTP 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/video/stream/{id}` | GET | 视频流（支持Range请求，1MB分块） |
| `/video/thumbnail` | GET | 获取缩略图 |



