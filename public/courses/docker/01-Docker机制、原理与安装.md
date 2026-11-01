# 第1课:Docker 机制、原理与安装

> 这一课解决两个问题：Docker 到底是什么，以及怎样把它装到自己的电脑上。
>
> 先建立镜像、容器和隔离的心智模型，再完成安装、验证和第一次运行。学完这一课，你应该能解释容器为什么能独立运行，也能在自己的机器上跑起一个 Redis 容器。

命令示例中 `#` 后面的文字是注释，实际执行时不输入。

## 1. 这一课要解决什么问题

Redis 课程里我们用一条命令启动了 Redis。这里先省略端口映射，只看核心动作：

```bash
docker run --name redis-demo -d redis:7
```

真实命令还会通过 `-p` 把容器端口映射到本机；端口映射在第 5 课展开，本课先不引入。

这条命令背后值得追问：

```text
为什么一条命令就能跑起 Redis，不用先安装？
    -> Redis 的运行环境被打包成了镜像
    -> 镜像在任何装有 Docker 的机器上都能运行
    -> 那"能运行"和"互不干扰"是怎么做到的？
```

本课回答五个问题：

1. Docker 到底是一个什么程序？
2. 使用者看到的是什么，机制上它又是什么？
3. 容器是怎么做到隔离的？
4. 镜像和容器是什么关系？
5. 为什么容器启动快、占用小？

同时完成安装：确认系统条件、启用 WSL2、安装 Docker Desktop、验证安装，并跑起第一个容器。

## 2. 一个类比：集装箱

可以把 Docker 理解成货运中的标准集装箱：

```text
传统方式
    货物散装 -> 每个码头装卸方式不同 -> 换港口很麻烦

集装箱
    货物装进统一规格的箱子 -> 任何港口都能用同一种吊机装卸 -> 换港口很方便
```

应用和它的运行环境（依赖库、系统库、配置文件、启动命令）被打包成一个"标准箱子"，这个箱子就是**镜像**。它在任何装有 Docker 的机器上都能用同一种方式打开运行。

Docker 主要解决三个问题：

- 环境一致性："在我机器上能跑"变成"在别的机器上也能跑"；
- 依赖隔离：不同项目需要不同版本的 Python、Redis，互不干扰；
- 快速复制与清理：一条命令启动，一条命令删除，不污染宿主机。

## 3. 容器是什么：三个视角

同一个容器，可以从三个角度理解。

### 3.1 使用者视角：一台独立的小电脑

```text
docker run redis:7 之后
    你得到一台"装好了 Redis 的小电脑"
    -> 它有自己的文件系统、进程和端口
    -> 进入容器看到的，是一个小型的 Linux 环境
```

对使用者来说，容器像一台随时能开、能关、能扔掉的电脑。

### 3.2 机制视角：一个被隔开的进程

```text
在你的 Windows 眼里
    docker run 只是启动了一些进程
    -> 这些进程被"看不见的墙"隔开
    -> 墙内的进程以为自己在独立的世界里运行
```

容器不是完整的操作系统，它共享宿主机的内核。内核把一组进程"关"进隔离空间，让它们拥有自己的进程列表、文件视图和网络端口。

### 3.3 分发视角：一个分层的模板

```text
镜像 = 分层的只读模板
    ├── 基础系统层（多数镜像共用）
    ├── 依赖层
    └── 应用层
```

多个容器共享相同的底层，只复制各自的差异部分。这是镜像下载一次、多处复用的原因，也是它占用小的原因之一。

一句话总结：

```text
使用者看到：独立的小电脑
机制上：一组共享内核的隔离进程
分发上：分层的只读模板
```

## 4. 镜像和容器

### 4.1 两个核心概念

```text
镜像 image：只读模板，包含应用 + 依赖 + 配置
    |
    | docker run
    v
容器 container：镜像运行起来的实例
```

类比：

```text
镜像 ≈ 菜谱：写好了原料和步骤，本身不能吃
容器 ≈ 按菜谱做出来的菜：可以吃，凉了可以重做，吃完可以倒掉
```

| 概念 | 类比 | 特点 |
|---|---|---|
| 镜像 image | 菜谱 / 设计图纸 | 只读模板，包含应用、依赖和配置 |
| 容器 container | 做出来的菜 / 盖好的楼 | 镜像运行后的实例，可启动、停止、删除 |
| Dockerfile | 菜谱的写作过程 | 定义"镜像怎么做"，第 3 课展开 |

### 4.2 常见误解：镜像不是容器

```text
镜像：模板，静止的
容器：实例，运行中的
```

一个镜像可以同时创建多个容器，容器之间互不影响。删除容器不会删除镜像。

## 5. 容器是怎么隔离的

### 5.1 三面"看不见的墙"

容器隔离的核心，是让一组进程拥有三个独立的世界：

```text
进程：容器有自己的进程树
    容器里看到的进程列表，和宿主机上看到的不一样

文件系统：容器有自己的文件视图
    容器里的 / 目录，不等于你电脑的 C 盘根目录

网络：容器有自己的端口空间
    容器里的 6379，默认只存在于容器世界里
```

这三面墙分别来自操作系统提供的进程隔离、文件系统隔离和网络隔离能力。Linux 上分别由 namespace、cgroup 和联合文件系统承担：

- **namespace**：隔离"看得见什么"，例如进程号、网络设备、挂载点；
- **cgroup**：限制"能用多少"，例如 CPU、内存；
- **联合文件系统**：把镜像的只读层和容器的可写层叠加成一个文件视图。

本课程只要求知道这三者的职责，不展开内核实现。容器只是把这三样组合起来，形成了"独立小电脑"的体验。

### 5.2 为什么启动快、占用小

```text
虚拟机：每个都要启动一套完整操作系统 -> 慢、占内存
容器：共享宿主机内核，只启动应用进程 -> 快、省资源
```

这就是容器和虚拟机最直观的差别。

### 5.3 常见误解

```text
误解一：容器里是完整的操作系统
    -> 不是，容器共享宿主机内核

误解二：Docker 是虚拟机软件
    -> 不是，容器是隔离进程，不是模拟硬件

误解三：每个容器复制一份完整镜像
    -> 不是，镜像分层共享，容器只多出各自的差异
```

## 6. 容器和虚拟机的区别

### 6.1 虚拟机：每个都装完整系统

```text
虚拟机 A
    ├── 完整操作系统
    └── 应用

虚拟机 B
    ├── 完整操作系统
    └── 应用
```

虚拟机需要模拟完整的硬件和操作系统，启动要经过整个系统启动过程，内存和磁盘开销比较大。

### 6.2 容器：共享宿主机内核

```text
容器 A -> 应用 + 依赖
容器 B -> 应用 + 依赖
    └── 共享宿主机操作系统内核
```

容器不需要各自带一套操作系统，它复用宿主机的内核，只打包应用层。

### 6.3 对比

| | 虚拟机 | Docker 容器 |
|---|---|---|
| 操作系统 | 每个虚拟机一个完整系统 | 共享宿主机内核 |
| 启动速度 | 慢（要启动整个系统） | 快（启动应用进程即可） |
| 资源占用 | 大 | 小 |
| 隔离强度 | 强（硬件级隔离） | 较弱（进程级隔离） |
| 典型用途 | 需要严格隔离的场景 | 应用打包与分发 |

容器不是"小虚拟机"：它没有自己完整的操作系统，因此不能像虚拟机那样随便安装任何东西。

## 7. 安装前的系统要求

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

## 8. 启用 WSL2

WSL2 是"适用于 Linux 的 Windows 子系统"，可以简单理解成 Windows 里的一个轻量 Linux 运行环境。Docker Desktop 在 Windows 上默认把容器跑在 WSL2 里面，这也是前面说的"容器共享 Linux 内核"的具体承载方式。

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

## 9. 安装 Docker Desktop

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

## 10. 验证安装

### 10.1 查看版本

```powershell
docker version
```

这条命令会同时显示：

```text
Client：本机的 docker 命令行工具版本
Server：Docker daemon 的版本
```

如果只有 Client 而没有 Server，通常说明 Docker Desktop 还没有启动完成。

### 10.2 运行第一个容器

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

`docker run` 一步完成了三件事：

```text
docker run 镜像    ≈  拉取（如缺） + 创建容器 + 启动容器
```

本课只把 `docker run` 当作"跑起一个容器"的入口；它的完整参数和容器生命周期在第 2 课展开。

### 10.3 跑起课程里的 Redis 容器

```powershell
docker run --name redis-demo -d redis:7
```

参数含义：

| 参数 | 含义 |
|---|---|
| `--name redis-demo` | 给容器起名 redis-demo |
| `-d` | 后台运行 |
| `redis:7` | 使用 Redis 7 镜像，本地没有会自动拉取 |

然后确认容器正在运行：

```powershell
docker ps
```

`docker ps` 只显示正在运行的容器。看到 `redis-demo` 的状态是 `Up`，说明容器已经启动。

这里故意没有加端口映射：容器里的 Redis 现在只能从容器内部访问。怎样从本机连接它，属于端口映射，第 5 课再讲；怎样进入容器、看日志、停止和删除容器，属于容器管理，第 2 课展开。

### 10.4 本课命令速查表

| 命令 | 含义 | 参数说明 |
|---|---|---|
| `docker version` | 查看客户端和 daemon 的版本 | — |
| `docker run 镜像` | 用镜像创建并启动容器 | `-d` 后台运行，`--name` 起名 |
| `docker ps` | 列出正在运行的容器 | 加 `-a` 显示所有容器，第 2 课展开 |

## 11. 常见错误

### 11.1 `Cannot connect to the Docker daemon`

```powershell
docker ps
```

报错 `Cannot connect to the Docker daemon` 时，通常是 Docker Desktop 还没有启动，或者仍在启动过程中。先启动 Docker Desktop，等状态变为 running 再执行命令。

### 11.2 镜像拉取失败或超时

`docker run redis:7` 需要从 Docker Hub 拉取镜像。国内直连 Docker Hub 时，除了慢，还可能出现下面的报错：

```text
failed to resolve reference "docker.io/library/hello-world:latest"
dial tcp 31.13.96.195:443: connectex: A connection attempt failed
```

这种报错说明 Docker 本身是好的，问题出在网络：域名 `registry-1.docker.io` 被解析到了明显不对的地址，连接被卡住。即使本机开了代理软件，Docker Desktop 默认也不读系统代理，所以需要单独配置。两种常见解法：

方法一：配置镜像加速器。在 Docker Desktop 的 Settings → Docker Engine 中修改配置，加入 `registry-mirrors`：

```json
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
```

点击 Apply & Restart 后，用 `docker info` 确认 `Registry Mirrors` 字段已经生效，再重新执行 `docker run hello-world`。可用的加速地址会随时间变化，如果当前地址失效，换一个当前有效的即可。

方法二：给 Docker Desktop 配置代理。在 Settings → Resources → Proxies 中启用手动代理，HTTP 和 HTTPS 都填入本机代理地址（例如 `http://127.0.0.1:7890`），保存后重启 Docker Desktop。

### 11.3 提示虚拟化未开启

安装或启动时提示虚拟化未开启，需要进入 BIOS 开启 "SVM Mode"（AMD）或 "Intel Virtualization Technology"（Intel），保存后重启。也可以先用 `Get-CimInstance` 命令确认状态。

### 11.4 启动 Docker Desktop 时报 WSL 资源不足

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

## 12. 面试高频考点

### 12.1 Docker 是什么？

> Docker 是一种容器化技术，它把应用和运行环境（依赖、配置）打包成镜像，并用镜像创建容器来运行应用。容器共享宿主机内核，启动快、占用小，能够保证应用在任何装有 Docker 的机器上以同样的方式运行。

### 12.2 容器是怎么做到隔离的？

> 容器通过操作系统的 namespace、cgroup 和文件系统能力，让一组进程拥有独立的进程树、文件视图和端口空间，它们共享宿主机内核。所以容器在使用者看来像一台独立的小电脑，机制上是一组被隔离的进程。

### 12.3 镜像和容器有什么区别？

> 镜像是只读的模板，包含应用和依赖；容器是镜像运行起来的实例。一个镜像可以创建多个容器，删除容器不会影响镜像。

### 12.4 容器和虚拟机有什么区别？

> 虚拟机每个都包含完整操作系统，隔离强但启动慢、开销大；容器共享宿主机内核，只打包应用层，启动快、占用小，但隔离强度弱于虚拟机。

### 12.5 WSL2 在 Windows 上装 Docker 时是做什么的？

> WSL2 是 Windows 里的 Linux 运行环境，Docker Desktop 默认把容器跑在 WSL2 上。容器共享 Linux 内核，所以 Windows 上装 Docker 需要先启用 WSL2 和虚拟机平台功能。

## 13. 验收问题 / 过关清单

达到下面的程度，就可以进入下一课：

```text
能用三个视角解释容器（小电脑 / 隔离进程 / 分层模板）
能说出隔离的三个方面（进程、文件系统、网络）
能区分镜像和容器
能区分容器和虚拟机
能解释容器为什么启动快、占用小
能确认系统满足 Docker 的要求（版本、内存、虚拟化）
能启用 WSL2 并理解它的作用
能根据 CPU 架构选择 AMD64 或 ARM64 安装包
能用 docker version 确认 Client 和 Server 都正常
能运行 hello-world 和课程中的 Redis 容器
能说明为什么本课启动 Redis 时没有加端口映射
```

## 14. 下一课预告

下一课把镜像和容器真正用起来：

```text
镜像从哪里来？tag 和 latest 有什么区别？
怎样查看、拉取、删除镜像？
容器有哪些状态？怎样停止、启动、删除？
怎样查看日志、进入容器排查问题？
两个容器同时运行，为什么互不干扰？
```
