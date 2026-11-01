# 第6课:Docker Compose

> 第 3 课构建了 `takeout-api` 镜像，第 4 课给 MySQL/Redis 挂了数据卷，第 5 课讲了端口映射和容器网络。现在把三个容器一起启动，需要记端口、卷、网络、环境变量和启动顺序。
>
> Compose 用一份 `compose.yaml` 描述整套环境，一条命令启动，一条命令清理。这一课围绕外卖系统的 `app + redis + mysql`，逐字段理解 Compose 文件，再讲它如何构建和启动容器。

命令示例中 `#` 后面的文字是注释，实际执行时不输入。

## 1. 场景：三条 docker run 太难维护

如果不用 Compose，启动外卖系统大概要这样：

```bash
# 1. 创建网络
docker network create takeout-net

# 2. 启动 MySQL
docker run -d --name mysql --network takeout-net -e MYSQL_ROOT_PASSWORD=example -e MYSQL_DATABASE=takeout -v mysql-data:/var/lib/mysql -v "${PWD}/04-init.sql:/docker-entrypoint-initdb.d/init.sql:ro" mysql:8

# 3. 启动 Redis
docker run -d --name redis --network takeout-net -v redis-data:/data redis:7

# 4. 构建并启动 app
docker build -f 03-app.Dockerfile -t takeout-api:1 .
docker run -d --name app --network takeout-net -p 8000:8000 -e REDIS_HOST=redis -e MYSQL_HOST=mysql takeout-api:1
```

问题很明显：

```text
命令很长，参数容易漏
重启时要按顺序再敲一遍
换一台机器要重新记住所有参数
多个项目容易端口/容器名冲突
不知道哪个服务先启动、什么时候算就绪
```

Compose 把这些内容写进一个文件，变成可重复执行的配置。

## 2. Compose 是什么

**Docker Compose** 是 Docker 的多容器编排工具：

```text
compose.yaml        -> 描述多个 service
docker compose up   -> 按配置创建网络、卷、容器
docker compose down -> 停止并删除容器和网络
```

几个核心概念：

| 概念 | 含义 |
|---|---|
| `compose.yaml` | 多容器环境的声明式配置文件 |
| service | 一个服务，通常对应一个容器，例如 `app`、`redis`、`mysql` |
| project | 一组 service 的集合，默认用所在目录名作为项目名 |
| network | Compose 自动创建的网络，service 之间通过服务名通信 |
| volume | 持久化数据，声明在顶层 `volumes:` 下 |

Compose 有两个常见命令：

```text
docker compose     -> Compose v2 插件，当前推荐
docker-compose     -> 旧版独立程序，逐步淘汰
```

本课程统一使用 `docker compose`。

### 2.1 容器开销与拆分边界

一个常见疑问：每个容器都有自己的 Linux 用户态，跑多个容器会不会很重？为什么不把 app、Redis、MySQL 塞进一个容器？

容器不是虚拟机：

- 所有容器共享宿主机内核；
- 镜像层是只读的，可以在多个容器、多个镜像之间共享；
- 容器只额外增加一个很薄的可写层。

真正的内存和 CPU 开销主要来自服务本身：MySQL 最重，Redis 次之，Python app 再次。容器本身的额外开销通常是几 MB 到几十 MB 级别。

但"开销小"不等于"应该塞进一个容器"：

| 维度 | 一个容器装全部 | 每个服务一个容器 |
|---|---|---|
| 生命周期 | 一起启动、停止、崩溃 | 独立重启和升级 |
| 依赖版本 | 容易冲突 | 各自镜像，互不干扰 |
| 扩缩容 | 只能整体复制 | 可以单独扩 app |
| 故障隔离 | 一个进程 OOM 影响全部 | 只影响一个服务 |
| 日志和监控 | 混在一起 | 按服务分开 |
| 数据持久化 | 数据和应用混在一起 | volume 只挂数据库 |
| 安全 | 攻击面更大 | 每个容器权限更小 |

所以"一个容器一个主要服务"是工程约定，不是 Docker 硬性规则。

## 3. 一个完整例子：逐字段理解 compose.yaml

课程示例文件：`code/docker/06-compose.yaml`。

```yaml
services:
  app:
    build:
      context: .
      dockerfile: 03-app.Dockerfile
    ports:
      - "8000:8000"
    environment:
      APP_ENV: compose
      REDIS_HOST: redis
      MYSQL_HOST: mysql
    depends_on:
      redis:
        condition: service_healthy
      mysql:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 5s

  redis:
    image: redis:7
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: example
      MYSQL_DATABASE: takeout
    volumes:
      - mysql-data:/var/lib/mysql
      - ./04-init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-pexample"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 20s

volumes:
  redis-data:
  mysql-data:
```

三个服务：

| service | 作用 | 镜像来源 | 对外端口 | 数据 |
|---|---|---|---|---|
| `app` | 外卖 API | 用 `03-app.Dockerfile` 构建 | 8000 | 无状态 |
| `redis` | 缓存/会话/队列 | 官方 `redis:7` | 不对外 | `redis-data:/data` |
| `mysql` | 订单/用户/菜单 | 官方 `mysql:8` | 不对外 | `mysql-data:/var/lib/mysql` |

下面逐个字段解释。

### 3.1 services 与 build / image

`services:` 是顶层列表，每个 service 通常对应一个容器。

两种指定镜像来源的方式：

```yaml
services:
  app:
    build:
      context: .
      dockerfile: 03-app.Dockerfile

  redis:
    image: redis:7
```

- `build`：用 Dockerfile 自己构建镜像；
  - `context`：构建上下文，相对于 `compose.yaml` 所在目录；
  - `dockerfile`：要用的 Dockerfile 路径，相对于 context。
- `image`：直接使用已有镜像，本地没有会拉取。

`app` 用 `build`，因为它是你自己的代码；`redis`、`mysql` 用 `image`，因为它们有官方镜像。

可以同时写 `build` 和 `image`，让构建出的镜像带固定名字：

```yaml
services:
  app:
    build:
      context: .
      dockerfile: 03-app.Dockerfile
    image: takeout-api:1
```

不写 `image` 时，Compose 自动命名，例如 `docker-app`。

### 3.2 ports

```yaml
services:
  app:
    ports:
      - "8000:8000"
```

格式和第 5 课 `-p` 一样：

```text
"宿主机端口:容器端口"
```

这里只有 `app` 发布端口；`redis` 和 `mysql` 不写 `ports`，所以它们只在 Compose 网络内部，不暴露到宿主机。

```text
app     -> 宿主机 8000 -> 容器 8000
redis   -> 不发布，只在内部
mysql   -> 不发布，只在内部
```

如果想改宿主机入口，例如避免 8000 冲突：

```yaml
ports:
  - "8080:8000"
```

### 3.3 environment

```yaml
services:
  app:
    environment:
      APP_ENV: compose
      REDIS_HOST: redis
      MYSQL_HOST: mysql
```

`environment` 把环境变量注入容器。app 代码里：

```text
REDIS_HOST=redis
MYSQL_HOST=mysql
```

`redis`、`mysql` 是 service 名，不是 `127.0.0.1`，因为容器里的 `localhost` 是 app 自己。

也可以从文件读取：

```yaml
services:
  app:
    env_file:
      - .env.app
```

`.env.app`：

```text
APP_ENV=dev
REDIS_HOST=redis
```

Compose 还会自动读取 `compose.yaml` 同目录的 `.env` 做 `${VAR}` 替换：

```yaml
services:
  app:
    ports:
      - "${APP_PORT}:8000"
```

区别：

```text
environment / env_file -> 把变量注入容器
.env                    -> 给 compose.yaml 做 ${VAR} 替换
```

密码不要写死在 compose 里，用 `.env`、Docker secrets 或外部密钥管理。

### 3.4 volumes

```yaml
volumes:
  redis-data:
  mysql-data:

services:
  redis:
    volumes:
      - redis-data:/data
  mysql:
    volumes:
      - mysql-data:/var/lib/mysql
      - ./04-init.sql:/docker-entrypoint-initdb.d/init.sql:ro
```

两种挂载：

- `redis-data:/data` 是 **named volume**，Docker 管理，删除容器不删除数据；
- `./04-init.sql:/docker-entrypoint-initdb.d/init.sql:ro` 是 **bind mount**，把宿主机文件只读挂进容器。

bind mount 短语法：

```text
[宿主机源:]容器路径[:模式]
```

```text
./04-init.sql                          宿主机源，相对于 compose.yaml 所在目录
/docker-entrypoint-initdb.d/init.sql   容器内路径
:ro                                    只读；默认是 rw
```

MySQL 第一次初始化时会执行 `/docker-entrypoint-initdb.d/` 下的 `.sql` 文件；如果 `mysql-data` 已有数据，不会重复执行。

`docker compose down` 保留 volume；`down -v` 删除 volume，数据丢失。

### 3.5 networks 与服务名

这个例子没有写 `networks:`，Compose 会自动创建一个默认网络，例如 `takeout_default`，并把所有 service 接进去。这里的 `takeout` 来自 compose.yaml 顶部的 `name: takeout`。

在这个网络里，**service 名就是 DNS 名**：

```text
app 容器
    -> redis:6379
    -> mysql:3306
```

所以 app 里写 `REDIS_HOST=redis`、`MYSQL_HOST=mysql`，不写 IP，也不写 `localhost`。

可以自定义网络：

```yaml
networks:
  takeout-net:

services:
  app:
    networks:
      - takeout-net
  redis:
    networks:
      - takeout-net
  mysql:
    networks:
      - takeout-net
```

默认网络对绝大多数本地开发已经够用；需要多个网络隔离时才自定义。

容器名和 service 名不是一回事：

```text
service 名：app、redis、mysql   -> 网络里的 DNS 名
容器名：takeout-app-1 等          -> Docker 自动生成，带项目前缀
```

一般不要在 Compose 里写 `container_name`，让 Compose 自己管理命名。

### 3.6 depends_on 与 healthcheck

短写法：

```yaml
depends_on:
  - redis
  - mysql
```

它只保证 Compose 先启动 Redis/MySQL，再启动 app；**不保证服务已经可以接受请求**。

健康检查：

```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
  timeout: 3s
  retries: 5
```

| 参数 | 含义 |
|---|---|
| `test` | 执行的命令；退出码 0 表示健康 |
| `interval` | 两次检查的间隔 |
| `timeout` | 单次检查超时 |
| `retries` | 连续失败多少次后标记 unhealthy |
| `start_period` | 启动宽限期，期间失败不计入 retries |

让 app 等待健康状态：

```yaml
depends_on:
  redis:
    condition: service_healthy
  mysql:
    condition: service_healthy
```

`condition` 的常用值：

```text
service_started                   依赖容器已启动
service_healthy                   依赖容器健康检查通过
service_completed_successfully    依赖容器成功结束（适合一次性任务）
```

`depends_on` 不是万能的：健康检查只说明"检查命令通过了"，应用自身仍要有重试和超时。

### 3.7 资源限制与 profiles

给 app 限制 CPU 和内存：

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
```

不同 Compose 版本对资源限制的支持略有差异；学习阶段先知道"Compose 可以声明资源上限"即可。

有些服务只在调试时启动：

```yaml
services:
  adminer:
    image: adminer
    ports:
      - "8080:8080"
    profiles:
      - tools
```

默认 `docker compose up` 不会启动 `adminer`；需要时：

```bash
docker compose -f code/docker/06-compose.yaml --profile tools up -d
```

## 4. Compose 的生命周期：构建、创建、启动、停止

### 4.1 先分清几个动词

Compose 把镜像和容器分成不同阶段，对应不同命令：

| 命令 | 作用 | 操作对象 |
|---|---|---|
| `docker compose build` | 根据 Dockerfile 构建镜像 | 镜像 |
| `docker compose create` | 用镜像创建容器，但不启动 | 容器 |
| `docker compose start` | 启动已创建的容器 | 容器 |
| `docker compose up` | create + start；`--build` 时先 build | 镜像 + 容器 |
| `docker compose stop` | 停止容器，容器还在 | 容器 |
| `docker compose down` | 停止并删除容器和网络 | 容器 + 网络 |

生命周期图：

```text
代码 + Dockerfile
    --build--> 镜像
    --create--> 容器（未启动）
    --start--> 运行中
    --stop--> 已停止（容器还在）
    --down--> 已删除（容器和网络都没了）
```

**build 和 create 的区别**：

- `build` 生成**镜像**，不产生容器；
- `create` 用镜像生成**容器**，但进程还没跑起来。

```text
build  -> 做菜谱上的菜（镜像）
create -> 把菜装进盘子（容器）
start  -> 端上桌开始吃（运行）
```

### 4.2 一个常用流程

先进入 compose 文件所在目录，就能省去 `-f`：

```bash
cd code/docker
```

构建镜像（不启动）：

```bash
docker compose build
# 只执行 build 字段，产出镜像，不创建容器
```

创建并启动容器：

```bash
docker compose up -d
# create + start；-d 表示后台运行
```

注意：`docker compose up` 在镜像不存在时会**自动构建**（有 `build` 的 service）或**自动拉取**（有 `image` 的 service），不会因为"还没 build"就报错。

如果改了代码或 Dockerfile，需要重新构建再启动：

```bash
docker compose up -d --build
# 先 build，再 create + start
```

什么时候用哪个：

| 场景 | 命令 |
|---|---|
| 第一次启动 | `up`（镜像缺失会自动 build/pull） |
| 改了代码或 Dockerfile | `up --build` |
| 只想构建、不启动 | `build` |
| 只想启动已有镜像 | `up` |

停止但保留容器：

```bash
docker compose stop
# 容器还在，可以再 start
```

停止并删除容器和网络：

```bash
docker compose down
# 容器和网络删除，volume 默认保留
```

`-f` 和 `cd` 的关系：

```text
docker compose -f code/docker/06-compose.yaml up   -> 从仓库根目录指定文件
cd code/docker && docker compose up                -> 进入目录，Compose 自动找 compose.yaml
```

`-f` 只负责"选哪个文件"；项目名由 `name:` 或 `-p` 决定，两者是不同的事。

### 4.3 给这一组容器起名字

compose.yaml 顶部已经写了：

```yaml
name: takeout
```

这样这一组容器叫 `takeout`，所有资源都带前缀：

```text
项目：takeout
网络：takeout_default
容器：takeout-app-1、takeout-redis-1、takeout-mysql-1
volume：takeout_redis-data、takeout_mysql-data
```

不写 `name:` 时，Compose 默认用目录名（这里是 `docker`）作为项目名。

所以后面的 `docker compose exec redis`、`docker compose restart app` 都不需要写 `-p`：`docker compose` 会读取当前目录的 compose.yaml，从 `name: takeout` 知道项目名，再把 service 名 `redis` 映射到容器 `takeout-redis-1`。

也可以在命令行用 `-p` 覆盖：

```bash
docker compose -p takeout-dev -f code/docker/06-compose.yaml up -d
```

或者用环境变量：

```bash
COMPOSE_PROJECT_NAME=takeout-dev docker compose -f code/docker/06-compose.yaml up -d
```

作用：

- 同一个 compose 文件可以起多套环境，例如 `takeout-dev` 和 `takeout-test`；
- 容器名、网络名、卷名都带项目前缀，互不冲突；
- 不用每次手动给容器起不重复的名字。

### 4.4 stop 和 down 的区别

| | `stop` | `down` |
|---|---|---|
| 停止容器 | 是 | 是 |
| 保留容器 | 是 | 否 |
| 保留网络 | 是 | 否 |
| 保留 volume | 是 | 是（`down -v` 才删） |
| 再次启动 | `start` 或 `up` 都可 | 需要重新 `up` 创建 |

记忆：

```text
stop = 关机，机器还在
down = 拆掉机器，数据和图纸还在（除非 -v）
```

日常：

```bash
docker compose stop        # 临时停一下，下次 start 起来
docker compose down        # 收工，删容器和网络，保留数据
docker compose down -v     # 连数据卷一起删，确认后使用
```

### 4.6 常用命令速查

| 命令 | 作用 |
|---|---|
| `docker compose config` | 解析并展示最终配置，不启动 |
| `docker compose build` | 只构建镜像 |
| `docker compose create` | 只创建容器，不启动 |
| `docker compose up -d` | create + start |
| `docker compose up -d --build` | build + create + start |
| `docker compose ps` | 查看服务和健康状态 |
| `docker compose logs -f 服务名` | 跟随日志 |
| `docker compose exec 服务名 命令` | 在运行中的容器里执行命令 |
| `docker compose run --rm 服务名 命令` | 用临时容器跑一次性命令 |
| `docker compose restart 服务名` | 重启某个服务 |
| `docker compose stop` | 停止容器，保留容器和网络 |
| `docker compose down` | 停止并删除容器和网络，保留 volume |
| `docker compose down -v` | 连同 volume 一起删除 |

## 5. 完整练习

```bash
# 0. 进入 compose 文件目录，后面的命令可以省略 -f
cd code/docker
# 项目名来自 compose.yaml 顶部的 name: takeout，下面的 exec/restart 都不需要 -p

# 1. 先检查配置
docker compose config

# 2. 构建并启动整套环境
docker compose up -d --build

# 3. 查看服务和健康状态
docker compose ps

# 4. 跟随 app 日志
docker compose logs -f app
# Ctrl+C 退出日志跟随

# 5. 验证接口
curl.exe http://127.0.0.1:8000/
curl.exe http://127.0.0.1:8000/orders
curl.exe http://127.0.0.1:8000/health

# 6. 进入服务容器
docker compose exec app sh
# exit 退出

docker compose exec redis redis-cli ping
# PONG

docker compose exec mysql mysql -uroot -pexample takeout -e "SELECT * FROM orders;"

# 7. 重启 app，观察依赖是否正常
docker compose restart app

# 8. 停止并删除容器和网络，保留数据卷
docker compose down

# 9. 确认数据不再需要时，再删除数据卷
docker compose down -v
```

## 6. 课后作业

1. 给 `app` 增加 `env_file: .env.app`，用 `.env.app` 设置 `APP_ENV=homework`，重启后验证 `/` 返回的 `env` 变成 `homework`；
2. 增加一个 `adminer` 服务，放在 `profiles: ["tools"]` 下，端口 `8080:8080`；用 `--profile tools` 启动，访问 Adminer 连接 MySQL；
3. 修改 MySQL healthcheck 的 `start_period` 和 `retries`，观察 `docker compose ps` 的健康状态变化；
4. 用 `docker compose -p takeout-homework ...` 启动第二套环境，观察容器名和网络名的项目前缀；
5. 回答：`depends_on` 能不能保证 MySQL 已经可以执行 SQL？为什么？

要求：

- 能解释每个字段的作用；
- 能用 `docker compose config` 验证配置；
- 能区分 `down` 和 `down -v`；
- 不把密码提交到仓库。

## 7. 验收问题 / 过关清单

达到下面的程度，就可以进入下一课：

```text
能解释 Compose 解决什么问题
能区分 service、container、project、network、volume
能读懂并解释 compose.yaml 的每个字段
能解释 build 和 image 的区别
能解释 ports 左右两侧
能解释 environment、env_file 和 .env 的区别
能解释 named volume 和 bind mount
能解释 service 名就是容器网络里的 DNS 名
能解释 depends_on 和 healthcheck 的区别
能说明 up 做了哪些步骤
能用 config、build、up、ps、logs、exec、restart、down 操作服务
能解释 down 和 down -v 的区别
能说明项目名如何影响容器和网络的命名
```

## 8. 面试高频考点

### 8.1 Docker Compose 是什么？

> Compose 是 Docker 的多容器编排工具，用一份 YAML 描述多个 service、网络和数据卷，一条 `docker compose up` 就能创建并启动整套环境。它适合本地开发、测试和单机多服务部署。

### 8.2 Compose 和 Dockerfile 有什么区别？

> Dockerfile 描述"一个镜像怎么构建"；Compose 描述"多个容器怎么一起运行"，包括镜像来源、端口、环境变量、数据卷、网络和依赖。Compose 可以调用 Dockerfile 构建镜像，但它本身不是构建指令。

### 8.3 Compose 和 Kubernetes 有什么区别？

> Compose 面向单机多容器，配置简单，适合开发和测试；Kubernetes 面向集群，提供调度、扩缩容、滚动发布、服务发现和自愈。Compose 更轻量，Kubernetes 更适合生产级集群。

### 8.4 `depends_on` 能保证服务就绪吗？

> 短写法只保证启动顺序，不保证服务已经可以接受请求。需要配合 healthcheck 和 `condition: service_healthy`，并且应用自身要有重试和超时。

### 8.5 Compose 里 service 之间怎么通信？

> Compose 会创建项目网络，把所有 service 接进去；service 名就是 DNS 名。app 里用 `mysql:3306`、`redis:6379` 访问，而不是 `127.0.0.1`。

### 8.6 `docker compose down` 和 `down -v` 有什么区别？

> `down` 停止并删除容器和网络，保留 named volume；`down -v` 还会删除 volume，数据会丢失。确认数据不再需要时才加 `-v`。

### 8.7 Compose 里的 volume 怎么声明？

> 在顶层 `volumes:` 声明 named volume，在 service 的 `volumes:` 里引用，例如 `mysql-data:/var/lib/mysql`。bind mount 则直接写宿主机路径和容器路径，例如 `./04-init.sql:/docker-entrypoint-initdb.d/init.sql:ro`。

### 8.8 多个 Compose 项目怎么隔离？

> Compose 默认用项目目录名作为项目名，容器、网络、卷都会带项目前缀；也可以用 `-p` 显式指定项目名，避免端口、容器名和卷名冲突。

### 8.9 为什么通常一个容器只跑一个主要服务？

> 容器共享宿主机内核，镜像层也能共享，所以多开容器的额外开销并不大；真正占资源的是 MySQL、Redis、应用进程本身。拆成多个容器主要是为了隔离生命周期、依赖、故障、日志和数据。

## 9. 下一课预告

下一课把前面所有内容串成一个完整项目：

```text
怎样给 FastAPI 写多阶段 Dockerfile？
怎样用 Compose 组织 API、Redis、MySQL？
怎样配置健康检查、环境变量和数据卷？
一条命令启动后，怎样验证整条订单链路？
容器起不来时，按什么顺序排查？
```
