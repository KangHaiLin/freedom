# A股量化交易系统 - 前端

基于 React 18 + TypeScript + Vite + Ant Design 开发。

## 开发

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

开发服务器默认启动在 `http://localhost:5173`，API 请求会通过代理转发到后端 `http://localhost:8000`。

### 运行测试

```bash
npm test
# 或
npm run test:watch
```

### 代码检查

```bash
npm run lint
```

### 生产构建

```bash
npm run build
```

构建产物输出到 `dist/` 目录。

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design 5
- **图表**: ECharts
- **HTTP客户端**: Axios
- **路由**: React Router 6

## 项目结构

```
src/
├── api/              # API层（类型定义、客户端、各模块接口）
├── components/       # 可复用组件
├── context/          # React Context全局上下文
├── hooks/            # 自定义Hooks
├── pages/            # 页面组件
├── utils/            # 工具函数和常量
├── config/           # 配置
├── App.tsx           # 根组件（路由配置）
└── main.tsx          # 应用入口
```

## 后端集成

后端 FastAPI 会在启动时自动挂载前端静态文件，无需额外配置。构建后直接运行后端即可访问完整应用。

## 功能模块

- **仪表板**: 系统概览、健康状态、实时自选股行情
- **行情数据**: 股票搜索、K线图查询、实时行情推送
- **策略监控**: 回测任务监控、性能指标可视化
- **系统状态**: CPU/内存/磁盘监控、数据源状态、系统信息

## 环境变量

创建 `.env.development` 或 `.env.production` 文件：

```
VITE_API_BASE_URL=/api
VITE_WS_BASE_URL=ws://localhost:8000/ws
```
