[English](README.md) | 中文

# Video App - 全栈视频管理应用

- 一个简单的本地视频元数据管理、流传输和浏览webUI应用，支持视频分类、标签管理、搜索和网页播放。

- 只需在配置中将已有的想要管理的视频目录映射到应用，即可自动扫描、生成缩略图，然后即可管理视频元数据（标题，收藏，tag等）。

## ✨ 功能特性

- 🏷️ **标签管理** - 视频标签系统，支持批量操作
- 📁 **目录浏览** - 多源文件系统目录浏览，支持 category 层级分类
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
| pytest | 单元测试（重构中） |

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
    # 格式: 宿主机路径:/app/resources/Category名称/PseudoName名称
    - /your/video/path1:/app/resources/Local-resource/Resource-1
    - /your/video/path2:/app/resources/Local-resource/Resource-2
```

编辑 `config.yaml`，确保 `resource_paths` 与容器内路径一致：

```yaml
resource_paths:
  Local-resource:              # category 名称
    Resource-1: /your/video/path1   # pseudo_name: 宿主机路径
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
  Local-resource:                    # category 名称
    Resource-1: /your/video/path1   # pseudo_name: 本地绝对路径
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
# 视频资源路径映射 (category -> pseudo_name -> host_path)
# Docker部署: host_path 填宿主机路径, 需配合 docker-compose.yml volumes 和 root_path
# 手动安装: host_path 填本地绝对路径, 注释掉 root_path
resource_paths:
  Local-resource:                              # category 名称
    Resource-1: /app/resources/Resource-1      # Docker 部署
    Resource-2: /app/resources/Resource-2
    # Resource-1: D:/videos/folder1            # 手动安装示例
    # Resource-2: E:/videos/folder2

# Docker部署时需要设置，手动安装时注释掉
root_path: /app/resources

# 缓存配置
cache_config:
  max_size: 2048        # 最大缓存条目数
  ttl: 300              # 缓存过期时间（秒）
  cache_type: cachetools # 缓存实现类型

# ffmpeg/ffprobe 并发限制
ffmpeg_semaphore_limit: 4

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

## 📖 参考

### 项目结构

#### 后端

```
video-app/
├── main.py                          # 后端入口 (localhost:12000)
├── config.yaml                      # 配置文件
├── Dockerfile                       # Docker镜像配置
├── docker-compose.yml               # Docker编排配置
├── migrations/                      # 数据库迁移脚本
│   └── add_category_field.py       # category 字段迁移
├── src/
│   ├── app.py                      # FastAPI应用工厂、CORS、lifespan
│   ├── config.py                   # 配置管理 (Settings)
│   ├── errors.py                   # 自定义异常
│   ├── logger.py                   # 日志配置 (loguru)
│   ├── db/
│   │   ├── setup_mongo.py         # AsyncMongoClient + Beanie 初始化
│   │   └── models/
│   │       ├── Video_model.py     # VideoModel (含 category 字段)
│   │       ├── VideoTag_model.py  # VideoTagModel
│   │       └── DirMetadata_model.py # DirMetadataModel (含 category 字段)
│   ├── router/
│   │   └── video_router.py        # /video/stream/{id}, /video/thumbnail
│   ├── schema/
│   │   ├── query_schema.py        # GraphQL 查询根
│   │   ├── mutation_schema.py     # GraphQL 变更根
│   │   ├── subscription_schema.py # GraphQL 订阅根
│   │   ├── strawberry_schema.py   # Schema 组装
│   │   └── types/
│   │       ├── video_type.py      # Video, VideoTag 类型
│   │       ├── search_type.py     # 搜索相关类型
│   │       ├── fileBrowse_type.py # 文件浏览相关类型
│   │       └── pydantic_types/    # 输入验证模型 (Pydantic)
│   │           ├── video_type.py
│   │           ├── search_type.py
│   │           ├── fileBrowe_type.py   # RelativePath 解析 (三级路径)
│   │           └── batch_operation_type.py
│   ├── resolvers/
│   │   ├── query_resolver.py          # 查询解析器
│   │   ├── mutation_resolver.py       # 变更解析器
│   │   ├── subscription_resolver.py   # 订阅解析器 (批量操作)
│   │   └── video_stream_resolver.py   # 视频流 (Range请求, 分块传输)
│   └── services/
│       ├── browse_file_service.py     # 目录浏览 (三级导航)
│       ├── batch_operation_service.py # 批量更新/删除
│       ├── dir_metadata_service.py    # 目录元数据 (大小/修改时间)
│       ├── tag_operation_service.py   # 标签计数管理
│       ├── thumbnail_service.py       # 缩略图生成 (ffmpeg/ffprobe)
│       ├── path_convert_service.py    # AbsolutePath 路径抽象
│       ├── cache/                     # 缓存服务
│       │   ├── base_cache.py         # 缓存抽象基类
│       │   ├── cachetools_cache.py   # cachetools 实现
│       │   └── cache_service.py      # 缓存工厂/分发
│       └── resource_handler/          # 资源处理器 (IO抽象层)
│           ├── base_resource_handler.py  # 抽象基类
│           ├── base_file_entry.py        # 文件条目抽象 + FileStat
│           ├── resource_handler_service.py # 处理器工厂/分发
│           └── local_fs/                  # 本地文件系统实现
│               ├── local_fs_handler.py    # LocalFS 处理器
│               └── local_fs_file_entry.py # LocalFS 文件条目
└── tests/                           # 测试文件
```

#### 前端

```
front-end/video-app-front/src/app/
├── app.ts, app.routes.ts, app.config.ts   # 根组件、路由、Apollo配置
├── core/graphql/
│   ├── documents/                         # GraphQL 操作文档
│   │   ├── queries.graphql.ts
│   │   ├── mutations.graphql.ts
│   │   └── subscription.graphql.ts
│   └── generated/graphql.ts              # graphql-codegen 自动生成
├── pages/
│   ├── homepage/                          # 首页 (Loved/Latest/MostViewed + Top标签)
│   ├── search/                            # 搜索页面
│   ├── video-player/                      # 视频播放 (video.js)
│   └── management/                        # 管理页面 (目录浏览/批量操作)
├── services/
│   ├── GQL-service/                       # GraphQL 操作统一服务
│   ├── Http-client-service/               # HTTP 客户端服务
│   ├── Page-state-service/                # 页面状态管理
│   ├── path-history-service/              # 路径历史管理
│   ├── theme-service/                     # 主题切换
│   ├── toast-service/                     # Toast 通知
│   ├── validation-service/                # 输入验证服务
│   └── video-update-event-service/        # 视频更新事件
├── shared/
│   ├── components/
│   │   ├── video-card/                    # 16:9缩略图+skeleton双态卡片
│   │   ├── video-edit-panel/              # 双模式(full/filter)编辑面板
│   │   ├── batch-operation-panel/         # 批量标签操作面板
│   │   ├── delete-check-panel/            # 删除确认对话框
│   │   ├── file-browse-table/             # 文件浏览表格 (支持列宽调整)
│   │   ├── pagination/                    # 分页组件 (支持加载状态)
│   │   ├── bottom-toolbar/                # 底部工具栏
│   │   ├── toast-displayer/               # Toast 显示组件
│   │   ├── sidebar/                       # 侧边栏
│   │   └── header/                        # 顶部导航栏
│   ├── interceptor/
│   │   └── ImageRequest.interceptor.ts    # 图片请求拦截器
│   └── models/                            # 类型定义
│       ├── GQL-result.model.ts            # ResultState<T>
│       ├── management.model.ts
│       ├── search.model.ts
│       ├── events.model.ts
│       ├── panels.model.ts
│       └── toast.model.ts
├── route-resolver/
│   └── video-player.resolver.ts           # 路由守卫
└── environments/                          # 环境配置
```

### GraphQL 端点

```
http://localhost:12000/graphql
```


### 查询 (Queries)

| 查询 | 描述 |
|------|------|
| `SearchVideos` | 搜索视频（支持按 category 过滤） |
| `getTopTags` | 获取热门标签 |
| `getSuggestions` | 获取搜索建议 |
| `getVideoById` | 根据ID获取视频 |
| `browseDirectory` | 浏览目录（category -> pseudo_name -> 子目录） |
| `directoryMetadata` | 获取目录元数据（大小/修改时间） |

### 变更 (Mutations)

| 变更 | 描述 |
|------|------|
| `updateVideoMetadata` | 更新视频元数据 |
| `deleteVideo` | 删除视频 |
| `recordVideoView` | 记录播放次数 |

### 订阅 (Subscriptions)

| 订阅 | 描述 |
|------|------|
| `batchUpdate` | 批量更新视频（流式返回进度） |
| `batchDelete` | 批量删除视频（流式返回进度） |

### HTTP 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/video/stream/{id}` | GET | 视频流（支持Range请求，1MB分块） |
| `/video/thumbnail` | GET | 获取缩略图 |
