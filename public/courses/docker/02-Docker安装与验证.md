# Docker 安装与验证

> 第一课讲了机制，这一课把 Docker 装到你的电脑上，并确认它真的能用。
>
> 目标：安装 Docker Desktop，跑起 hello-world，再跑起 Redis 课程要用的 redis:7 容器。

## 一、这一课要解决什么问题

```text
第一课：理解了机制
这一课：把它装到电脑上
    -> 确认系统满足要求
    -> 安装 Docker Desktop
    -> 验证安装
    -> 跑起 Redis 课程用的 redis:7
```

本课回答五个问题：

1. 安装前要确认哪些系统条件？
2. WSL2 是什么，为什么需要它？
3. AMD64 和 ARM64 版本怎么选？
4. 怎样确认 Docker 已经装好？
5. 怎样跑起课程里的 Redis 容器？

命令示例中 `#` 后面的文字是注释，实际执行时不输入。

---

## 二、安装前的系统要求

以常见的 Windows 10 为例，安装 Docker Desktop 前确认三件事：

```text
系统：Windows 10 22H2（build 19045）或更高版本
内存：建议 8 GB 或以上
虚拟化：BIOS 中已开启硬件虚拟化（VT-x / AMD-V）
```

开启虚拟化的方法因主板而异，一般在开机时进入 BIOS 设置，找到 "SVM Mode"（AMD）或 "Intel Virtualization Technology" 并开启。也可以用命令先确认系统是否已经开启：

```powershell
Get-CimInstance Win32_Processor | Select-Object VirtualizationFirmwareEnabled
```

返回 `True` 表示已经开启。

---

## 三、启用 WSL2

WSL2 是"适用于 Linux 的 Windows 子系统"，可以简单理解成 Windows 里的一个轻量 Linux 运行环境。Docker Desktop 在 Windows 上默认把容器跑在 WSL2 里面，这也是第一课说的"容器共享 Linux 内核"的具体承载方式。

以管理员身份打开 PowerShell，执行：

```powershell
wsl --install
```

这条命令会启用"适用于 Linux 的 Windows 子系统"和"虚拟机平台"两个功能。执行后重启电脑。

如果 `wsl --install` 在当前系统不可用，可以手动启用这两个功能后再重启：

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

---

## 四、安装 Docker Desktop

从 Docker 官网下载 Windows 版安装包（个人学习使用免费）：

```text
https://www.docker.com/products/docker-desktop/
```

下载页会提供 AMD64 和 ARM64 两种架构的安装包，选择依据是电脑 CPU 的架构：

```text
AMD64：Intel 和 AMD 的 x86_64 处理器，绝大多数电脑属于这一类
ARM64：ARM 处理器，常见于骁龙系列 Windows 笔记本
```

可以用命令确认本机架构：

```powershell
$env:PROCESSOR_ARCHITECTURE
```

返回 `AMD64` 就下载 AMD64 版本，返回 `ARM64` 就下载 ARM64 版本。

安装过程中保持默认选项，在选择后端时选择 WSL 2。安装完成后启动 Docker Desktop，等待界面右下角的状态变成 running。

Docker Desktop 本身只是一个管理界面，真正运行容器的是它启动的后台服务（Docker daemon）。

---

## 五、验证安装

### 1. 查看版本

```powershell
docker version
```

这条命令会同时显示：

```text
Client：本机的 docker 命令行工具版本
Server：Docker daemon 的版本
```

如果只有 Client 而没有 Server，通常说明 Docker Desktop 还没有启动完成。

### 2. 运行第一个容器

```powershell
docker run hello-world
```

`hello-world` 是一个极小的测试镜像。这条命令的执行过程是：

```text
本机没有 hello-world 镜像
    -> 先从 Docker Hub 拉取
    -> 创建一个容器并运行
    -> 容器打印一段欢迎文字后退出
```

看到欢迎文字，说明拉取、创建、运行整条链路都是通的。注意 `hello-world` 打印完就会自动退出，这是正常行为。

### 3. 跑起课程里的 Redis 容器

```powershell
docker run --name redis-course -p 6379:6379 -d redis:7
```

参数含义：

| 参数 | 含义 |
|---|---|
| `--name redis-course` | 给容器起名 redis-course |
| `-p 6379:6379` | 把本机 6379 端口映射到容器 6379 端口 |
| `-d` | 后台运行 |
| `redis:7` | 使用 Redis 7 镜像，本地没有会自动拉取 |

然后确认容器正在运行：

```powershell
docker ps
```

`docker ps` 只显示正在运行的容器。启动成功后，就可以按 Redis 课程第一课的方式连接 Redis 了。

### 4. 容器的基本生命周期（本课先够用）

`docker run` 一步完成了三件事：本地没有镜像就拉取、创建容器、启动容器。

```text
docker run 镜像    ≈  拉取（如缺） + 创建容器 + 启动容器
```

容器创建并启动后，还经常需要三个操作：

```powershell
docker stop redis-course      # 停止容器：进程结束，容器本身还在
docker start redis-course     # 启动已停止的容器，不用重新创建
docker exec -it redis-course redis-cli   # 进入运行中的容器执行命令
```

停止后容器并没有消失，用 `docker ps -a` 仍然能看到它，随时可以再 `docker start`。真正删除容器才用 `docker rm`。

进入容器后，输入 `exit`（或在 redis-cli 里输入 `quit`、按 Ctrl+D）退出，回到本机终端。注意：**退出 exec 不会停止容器**——容器的主进程 `redis-server` 仍然在后台运行，`docker ps` 依然显示它 Up；停止容器要用 `docker stop`。

这一课先够用即可。容器的完整管理（查看、停止、启动、删除、日志、进入容器）在第四课展开。

### 5. 本课命令速查表

| 命令 | 含义 | 参数说明 |
|---|---|---|
| `docker version` | 查看客户端和 daemon 的版本 | — |
| `docker run 镜像名` | 用镜像创建并启动容器 | `-d` 后台运行，`--name` 起名，`-p` 端口映射 |
| `docker ps` | 列出正在运行的容器 | 加 `-a` 显示所有容器 |
| `docker stop 容器` | 停止容器 | 容器还在，可再次 `start` |
| `docker start 容器` | 启动已停止的容器 | — |
| `docker exec 容器 命令` | 在运行中的容器里执行命令 | 加 `-it` 进入交互式模式 |

镜像和容器的更多管理命令，会在后面的课程继续。

---

## 六、常见错误

### 1. `Cannot connect to the Docker daemon`

```powershell
docker ps
```

报错 `Cannot connect to the Docker daemon` 时，通常是 Docker Desktop 还没有启动，或者仍在启动过程中。先启动 Docker Desktop，等状态变为 running 再执行命令。

### 2. 镜像拉取失败或超时

`docker run redis:7` 需要从 Docker Hub 拉取镜像。国内直连 Docker Hub 时，除了慢，还可能出现下面的报错：

```text
failed to resolve reference "docker.io/library/hello-world:latest"
dial tcp 31.13.96.195:443: connectex: A connection attempt failed
```

这种报错说明 Docker 本身是好的，问题出在网络：域名 `registry-1.docker.io` 被解析到了明显不对的地址（例如 Facebook 的 IP 段），连接被卡住。即使本机开了代理软件，Docker Desktop 默认也不读系统代理，所以需要单独配置。两种常见解法：

方法一：配置镜像加速器。在 Docker Desktop 的 Settings → Docker Engine 中修改配置，加入 `registry-mirrors`：

```json
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
```

点击 Apply & Restart 后，用 `docker info` 确认 `Registry Mirrors` 字段已经生效，再重新执行 `docker run hello-world`。可用的加速地址会随时间变化，如果当前地址失效，换一个当前有效的即可。

方法二：给 Docker Desktop 配置代理。在 Settings → Resources → Proxies 中启用手动代理，HTTP 和 HTTPS 都填入本机代理地址（例如 `http://127.0.0.1:7890`），保存后重启 Docker Desktop。

### 3. 端口被占用

```powershell
docker run --name redis-course -p 6379:6379 -d redis:7
```

如果提示端口被占用，可能是本机已经有一个 Redis 在监听 6379。换一个本机端口映射：

```powershell
docker run --name redis-course-6380 -p 6380:6379 -d redis:7
```

这样客户端连接本机的 `6380`，容器内部仍然是 `6379`。这个细节在 Redis 课程第一课已经讲过，在"环境隔离与切换"一课还会再展开。

### 4. 提示虚拟化未开启

安装或启动时提示虚拟化未开启，需要进入 BIOS 开启 "SVM Mode"（AMD）或 "Intel Virtualization Technology"（Intel），保存后重启。也可以先用第五课之前介绍的 `Get-CimInstance` 命令确认状态。

### 5. 启动 Docker Desktop 时报 WSL 资源不足

```text
Wsl/Service/CreateInstance/CreateVm/HCS/ERROR_NO_SYSTEM_RESOURCES
系统资源不足，无法完成请求的服务
```

Docker Desktop 启动时，WSL2 需要创建一个虚拟机实例来承载容器。这个报错说明创建实例的瞬间系统分配不到足够的资源，不代表 WSL 没有装好。按顺序排查：

```text
先执行 wsl --shutdown，再重新启动 Docker Desktop
    -> 仍失败：重启电脑（休眠、快速启动后容易出现）
    -> 反复出现：在用户目录创建 .wslconfig 限制 WSL2 内存
```

`.wslconfig` 示例（限制 WSL2 最多使用 6 GB 内存）：

```text
[wsl2]
memory=6GB
```

排查前可以先执行 `wsl --status` 确认 WSL 本身安装正常。

---

## 七、面试回答模板

### 题目：为什么课程用 Docker 跑 Redis？

> 用 Docker 可以把 Redis 的版本、配置和运行方式固定下来，一条命令启动，练习结束后一条命令删除，不会污染本机环境，也避免了手动安装 Redis 时的平台差异。Redis 的镜像由官方维护，直接使用比自己搭建环境更可靠。

### 题目：WSL2 在 Windows 上装 Docker 时是做什么的？

> WSL2 是 Windows 里的 Linux 运行环境，Docker Desktop 默认把容器跑在 WSL2 上。容器共享 Linux 内核，所以 Windows 上装 Docker 需要先启用 WSL2 和虚拟机平台功能。

---

## 八、这一课学到什么程度可以继续

达到下面的程度，就可以进入下一课：

```text
能确认系统满足 Docker 的要求（版本、内存、虚拟化）
能启用 WSL2 并理解它的作用
能根据 CPU 架构选择 AMD64 或 ARM64 安装包
能安装并启动 Docker Desktop
能用 docker version 确认安装成功
能运行 hello-world 和课程中的 Redis 容器
能停止、重新启动容器，并用 docker exec 进入容器执行命令
能排查 daemon 未启动、镜像拉取失败和端口被占用
```

下一课将亲手验证隔离，并学习切换环境：

```text
两个 Redis 容器同时跑，为什么互不干扰？
怎样证明数据是隔离的？
换镜像 tag 是不是就在切换环境？
```
