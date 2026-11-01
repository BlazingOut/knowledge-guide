# Docker 实战

本课程建立“应用如何被打包、运行和编排”的基础心智模型，服务于 Redis、FastAPI 和后续部署学习。前两课把机制、安装、镜像、容器和隔离讲清楚，后六课进入镜像构建、数据持久化、端口与网络、Compose 和生产排障，目标是能独立把一套多服务应用装进 Docker，并能解释常见故障。

本课程属于工程基础，不追求 Docker 内核源码和 Kubernetes 编排细节；原理讲到 namespace、cgroup、联合文件系统的职责层，重点放在能构建、能运行、能排障。当前第 1~8 课已全部编写完成。

## 前置知识

- 会用终端执行命令，理解路径、环境变量、进程和端口的基本含义；
- 能运行 Python 文件，了解函数和异常；第 7 课会用到 FastAPI 和 Redis，未学过可先按示例跑通；
- 不要求 Linux 系统管理经验；Windows 用户按第 1 课的 WSL2 步骤操作。

## 课程目标

完成本课程后，你应当能够：

- 用使用者、机制、分发三个视角解释 Docker 和容器；
- 在 Windows 上安装并验证 Docker Desktop，理解 WSL2 的作用；
- 管理镜像和容器的生命周期，证明容器在进程、文件系统、数据三个维度是隔离的；
- 分清云服务器镜像、Docker 镜像、官方服务镜像和应用镜像，理解服务端/客户端是运行时角色；
- 写出可复现、体积合理、以非 root 用户运行的 Dockerfile，理解构建缓存和多阶段构建；
- 用 volume 和 bind mount 持久化数据，处理权限和备份问题；
- 解释端口映射的数据路径，用自定义网络和容器 DNS 让容器通过服务名通信；
- 配置环境变量和 `env_file`，区分普通配置与敏感信息；
- 用 Docker Compose 编排多服务环境，配置健康检查、依赖和资源限制；
- 把 FastAPI、Redis 和数据库装进一套本地开发环境；
- 定位端口占用、镜像拉取失败、容器起不来、磁盘占满等常见故障，并说明 registry、CI 和容器安全的边界。

## 课程结构

课时与文件对应：

| 课 | 课文文件 | 状态 |
| --- | --- | --- |
| 第 1 课 | `01-Docker机制、原理与安装.md` | 已编写 |
| 第 2 课 | `02-镜像、容器与隔离.md` | 已编写 |
| 第 3 课 | `03-Dockerfile 与镜像构建.md` | 已编写 |
| 第 4 课 | `04-数据卷与持久化.md` | 已编写 |
| 第 5 课 | `05-端口映射与容器网络.md` | 已编写 |
| 第 6 课 | `06-Docker Compose.md` | 已编写 |
| 第 7 课 | `07-综合练习：把课程项目装进 Docker.md` | 已编写 |
| 第 8 课 | `08-生产化与排障.md` | 已编写 |

### 第 1 课：Docker 机制、原理与安装

目标：建立容器的心智模型，能区分镜像、容器和虚拟机，并完成 Docker 安装与第一次运行。

内容：Docker 解决什么问题；镜像与容器的关系；镜像分层与共享；容器隔离的三面墙（进程、文件系统、网络）；namespace、cgroup、联合文件系统的职责；容器与虚拟机的差异；Windows 系统要求、硬件虚拟化、WSL2、Docker Desktop、Client 与 daemon；`hello-world` 的完整链路。

实践：完成 WSL2 和 Docker Desktop 安装；用 `docker version` 查看 Client/Server；运行 `hello-world`；用 `docker run --name redis-demo -d redis:7` 启动 Redis，并用 `docker ps` 确认状态。本课不展开容器生命周期和端口映射。

面试考点：Docker 是什么；容器是怎么隔离的；镜像和容器有什么区别；容器和虚拟机有什么区别；WSL2 在 Windows 上起什么作用；`docker run` 一步做了哪些事。

### 第 2 课：镜像、容器与隔离

目标：把镜像和容器两个对象用起来，能管理生命周期、查看日志、进入容器，并验证容器隔离。

内容：镜像来源与可信判断；`images`、`pull`、tag、`latest`、`history`、`inspect`、`search`、`rmi`；容器状态与生命周期；Docker CLI 短参数与长参数（`--key=value`、`-it`、值内分隔符）；`run`、`start`、`stop`、`restart`、`rm`、`ps`、`ps -a`、`logs`、`exec`、`inspect`；进入容器终端（`exec -it`、`sh`/`bash`、`-u root`、`docker attach` 与 `exec` 的区别）；容器内目录结构（Linux 根目录、`/app`、`/data`）；两个 Redis 容器的进程、文件系统、数据隔离；换 tag 和换容器的环境切换。

实践：拉取并查看镜像；跑一遍“创建 → 查看日志 → 进入容器 → 停止 → 启动 → 删除”的生命周期；用 `docker exec -it 容器 sh` 进入容器终端，观察 `pwd`、`ls /`、`/etc/os-release`；同时运行两个 Redis 容器，用 `docker top`、`ls /`、`SET/GET` 验证隔离；清理容器和镜像。本课不涉及端口映射，端口映射在第 5 课。

面试考点：镜像和容器有什么区别；`docker stop` 和 `docker rm` 有什么区别；`docker exec` 能做什么；`docker exec` 和 `docker attach` 有什么区别；容器里的路径和宿主机路径有什么区别；为什么不推荐依赖 `latest`；怎样判断镜像是否可信；两个容器为什么互不干扰。

### 第 3 课：Dockerfile 与镜像构建

目标：能从外卖系统上云的场景拆出 app、MySQL、Redis 三个容器，分清云服务器镜像、Docker 基础镜像、官方服务镜像和应用镜像，并写出可复现、体积合理、以非 root 用户运行的 Dockerfile。

内容：云服务器镜像与 Docker 镜像的区别；服务端/客户端是运行时角色；外卖系统的容器拆分与端口边界；"环境"的组成；Dockerfile 指令 `FROM`、`RUN`、`COPY`、`ADD`、`WORKDIR`、`ENV`、`ARG`、`EXPOSE`、`CMD`、`ENTRYPOINT`；构建上下文与 `docker build -t`；镜像层与缓存；`.dockerignore`；多阶段构建；非 root 用户；`HEALTHCHECK`；镜像体积与最小权限。

实践：用 `code/docker/03-minimal-app.py` 构建 `takeout-api` 镜像并运行；修改一层观察缓存命中与失效；改成多阶段构建并比较镜像体积；用非 root 用户启动容器。

面试考点：云服务器镜像和 Docker 镜像的区别；为什么 Redis/MySQL 不装进 app 镜像；客户端/服务端角色；`RUN` 和 `CMD` 的区别；`COPY` 和 `ADD` 的区别；`CMD` 和 `ENTRYPOINT` 的区别；构建缓存什么时候失效；多阶段构建解决什么问题；为什么容器里不建议用 root；怎样减小镜像体积。

### 第 4 课：数据卷与持久化

目标：理解容器可写层的生命周期，能根据场景选择 volume 或 bind mount。

内容：容器可写层与删除容器后的数据命运；volume、bind mount、tmpfs；`-v` 与 `--mount`；named volume 与 bind mount 的选择；MySQL 数据目录 `/var/lib/mysql`、Redis 数据目录 `/data`；初始化 SQL 的执行条件；UID/GID 与文件权限；`mysqldump` 备份恢复；volume 原始备份；Compose 中的 volumes。

实践：分别用无挂载、named volume 运行 Redis，删除容器后检查数据；用 named volume + bind mount 初始化 MySQL，删除容器后重建并验证订单；用 `mysqldump` 备份和恢复；清理 volume。

面试考点：volume 和 bind mount 的区别；删除容器后数据会不会丢；数据库为什么必须挂载；初始化 SQL 为什么没有执行；挂载后权限不对怎么处理；怎样备份 MySQL；`docker compose down -v` 有什么风险。

### 第 5 课：端口映射与容器网络

目标：能从外卖系统的三条网络路径出发，解释用户怎么访问 app、app 怎么访问 Redis/MySQL、容器怎么访问宿主机，并能排查端口和服务名问题。

内容：容器网络命名空间；公网 IP、云安全组、宿主机端口、容器端口的完整访问链路；`-p 宿主机端口:容器端口` 的映射路径；只暴露 app、不暴露 MySQL/Redis；自定义 bridge 网络；容器 DNS 与服务名；多个容器都监听 6379 为什么不冲突；`host.docker.internal`；bridge、host、none 网络模式；`-e`、`--env-file` 与环境变量；换 tag、换容器、换端口、换网络四种环境切换方式。

实践：用 `takeout-net` 连接 `takeout-api`、`takeout-redis`、`takeout-mysql`；app 只发布 `8080:8000`；用 socket 验证 app 能解析并连接 Redis/MySQL；用临时客户端执行 `redis-cli`；用 `127.0.0.1:6380:6379` 做本地 Redis 调试；清理容器和网络。

面试考点：端口映射是怎么工作的；容器之间怎么通信；为什么用服务名而不是容器 IP；多个容器为什么可以都用 6379；bridge 和 host 网络有什么区别；`host.docker.internal` 的作用；为什么 MySQL/Redis 不暴露到公网；环境变量和 secret 有什么区别。

### 第 6 课：Docker Compose

目标：用 Compose 描述多服务环境，能配置依赖、健康检查、环境变量和资源限制。

内容：`compose.yaml` 的 services、volumes、networks；`build` 与 `image`；`ports`、`environment`、`volumes`、`depends_on`、`healthcheck`、`profiles`、资源限制逐字段解释；service 名与项目网络；`env_file` 与 `.env`；Compose 如何构建和启动容器（`config`、`build`、`up`、`ps`、`logs`、`exec`、`restart`、`down`）；项目名与容器命名。

实践：用 `code/docker/06-compose.yaml` 启动 app、Redis、MySQL；先 `config` 校验，再 `up --build`；用 `ps/logs/exec/restart` 观察服务；用 `down` 清理；观察项目名对容器命名的影响。

面试考点：Docker Compose 是什么；Compose 和 Dockerfile 的区别；Compose 和 Kubernetes 的边界；`depends_on` 能不能保证服务就绪；service 之间怎么通信；`down` 和 `down -v` 的区别；多个 Compose 项目怎么隔离；为什么通常一个容器只跑一个主要服务；`up` 做了哪些步骤。

### 第 7 课：综合练习：把课程项目装进 Docker

目标：把 FastAPI、Redis 和 MySQL 装进一套可复现的本地开发环境，验证下单、查询和持久化。

内容：FastAPI 应用连接 MySQL/Redis；环境变量与服务名；多阶段构建 API 镜像；非 root 与健康检查；Compose 编排；`depends_on` 与 `wait_for_deps`；volume 持久化；`04-init.sql` 初始化；日志与常见故障。

实践：用 `code/docker/07-*.py/Dockerfile/compose.yaml` 一条命令启动 app、Redis、MySQL；创建订单、查询订单和计数；`down` 后再 `up` 验证数据仍在；用日志定位启动失败；最后清理环境。

面试考点：一套多服务应用怎么装进 Docker；为什么 app 只装客户端库；`depends_on` 和应用重试分别解决什么；怎样验证数据持久化；容器起不来按什么顺序排查。

### 第 8 课：生产化与排障

目标：理解从本地 Docker 到生产交付的关键环节，能按顺序定位常见故障。

内容：镜像仓库与 tag 策略；CI 构建与推送；镜像扫描与最小权限；非 root、只读文件系统、capabilities；资源限制与重启策略；日志驱动；磁盘清理；`logs`、`inspect`、`exec`、`stats`、`events`；Nginx 反向代理（80/443 -> app:8000、HTTPS 终止、负载均衡、流式响应 `proxy_buffering off`、502/504 排查）；WSL2 资源问题；Docker 与 Kubernetes 的边界。

实践：用 `code/docker/08-prod-compose.yaml` 和 `08-nginx.conf` 启动生产版外卖系统；通过 Nginx 的 80 访问 app；用 `docker stats` 观察资源；`stop app` 观察 Nginx 返回 502，再 `start app` 恢复；用 `docker system df` 查看磁盘；按“状态 → 日志 → 配置 → 资源”排查；清理环境。

面试考点：镜像怎么进入生产环境；为什么生产环境不用 `latest`；容器安全从哪些方面做；资源限制怎么配置；Nginx 正向代理和反向代理的区别；502 和 504 分别说明什么；流式响应为什么要关闭 `proxy_buffering`；Docker 和 Kubernetes 有什么区别；线上容器排障按什么顺序进行。

## 综合练习

以第 7 课为基础，完成一套可复现的本地开发环境：

- FastAPI 服务、Redis 和数据库三个服务；
- API 镜像用多阶段构建，容器以非 root 用户运行；
- 用 Compose 编排，服务之间通过自定义网络和服务名通信；
- 数据库和 Redis 数据用 volume 持久化，配置用 `env_file`；
- 配置 healthcheck 和启动依赖；
- 一条命令启动，一条命令清理，重启后数据仍在；
- 能定位端口占用、镜像拉取失败、容器启动即退出三类问题。

## 阶段验收

完成本课程后，应当能够：

1. 用三个视角解释 Docker，并说清容器与虚拟机的区别。
2. 独立完成 Docker Desktop 安装、验证和常见启动问题排查。
3. 管理镜像和容器的生命周期，读懂状态、日志和基本配置。
4. 用两个容器验证进程、文件系统和数据隔离。
5. 写出带缓存优化、多阶段构建和非 root 用户的 Dockerfile。
6. 选择 volume 或 bind mount 持久化数据，并处理权限和备份。
7. 画出端口映射的数据路径，用自定义网络和容器 DNS 让容器通过服务名通信。
8. 用 Compose 编排多服务环境，配置 healthcheck、依赖和资源限制。
9. 把 FastAPI、Redis 和数据库装进一套可复现的本地环境。
10. 按“状态 → 日志 → 配置 → 资源”的顺序定位常见容器故障。
11. 说明镜像仓库、CI、镜像扫描和容器安全的基本做法，以及 Docker 与 Kubernetes 的边界。

## 课程编写约束

- 本课程以终端命令和 Docker 实验为主，不写 Python 作业；第 3、7 课需要的最小示例代码放 `code/docker/`，按 `NN-短语义名.ext` 命名，课文只保留理解概念所需的关键片段。
- 命令块逐行注释；成组命令配“命令 / 含义 / 参数说明”表；危险命令（`rm`、`rmi`、`prune`、`compose down -v`）先说明影响和确认步骤。
- 端口示例统一让宿主机端口与容器端口不同（如 `6380:6379`），帮助读者区分两侧；容器内部端口保持不变。
- 每课只保留一张命令速查表；命令只在首次出现时解释，后续课程直接使用，需要时写“用法见第 N 课”。
- 课程边界：第 1 课不展开生命周期和端口映射；第 2 课不展开端口映射；第 5 课不重复隔离验证；第 3 课不展开 Compose；第 6 课不展开生产 registry/CI。
- 练习容器统一使用课程命名（如 `docker-course-*`、`redis-a`、`redis-b`），结束按“先 stop 再 rm”的顺序清理；删除网络前先移除使用它的容器。
- 原理讲到 namespace、cgroup、联合文件系统的职责层即可，不展开内核源码；不把容器讲成虚拟机。
- 与 Redis、FastAPI 课程保持边界：本课程讲打包、运行、网络、存储和编排，不重复讲 Redis 命令和 FastAPI 语法。
- 以 Windows 10/11 + WSL2 为主，macOS/Linux 只说明差异；第 3、4、6、7、8 课正文按本大纲的目标、内容、实践、面试考点展开。
- 每课结尾保留“下一课预告”，课序调整时同步修正相邻课的预告。
