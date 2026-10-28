# 第九课：HTTPS、TLS 与会话保持

第八课把手写 HTTP 报文走通了。有一个事实当时刻意没展开：那些报文是**明文**。在咖啡馆 Wi-Fi 上 `GET /api/tasks` 连同 `Authorization` 头，路径上每一跳都能读、能改。本课解决两件相关的事：

1. **信道保密**：HTTP 外面套一层 TLS，变成 HTTPS——别人看不见、改不了、还能确认对面真是那个域名；
2. **身份保持**：HTTP 本身无状态，登录一次之后，后续请求必须自己携带"我是谁"。载体是 Cookie、Session、Token 三条路。

学完本课，"浏览器输入 URL 后发生了什么"可以接到：DNS → TCP 握手 → **TLS 握手** → HTTP 请求。第 10 课再讲 HTTP/2 和代理。

本课是概念课，不配 Python 作业文件。练习是读 `curl -v` 的握手输出，以及用 `requests` 观察两种身份头怎么被放进报文。

**学习目标：**

1. 能说明对称加密、非对称加密各自解决什么、各自的致命短板，以及 HTTPS 为什么必须混合使用；
2. 能解释数字证书、CA（Certificate Authority，证书颁发机构）和签名如何防止公钥被掉包；
3. 能按步骤讲述 TLS 握手：验证证书、交换会话密钥、切换到对称加密；
4. 能说明中间人攻击（MITM，Man-in-the-Middle）在什么条件下成功、证书在哪一步把它挡住；
5. 能区分 Cookie、Session、JWT（JSON Web Token，JSON 网络令牌），并说出 `HttpOnly`、`Secure`、`SameSite` 各防什么；
6. 能看懂 `curl -v https://…` 输出里的握手记录，以及 `Authorization: Bearer` 和 `Cookie` 两种携带方式。

## 1. 明文 HTTP 缺的不是格式，是信任

第八课的报文结构在 HTTPS 下**一个字节都不少**：还是请求行、头部、空行、正文。变的是这些字节在 TCP 连接上不再以明文出现，而是先被 TLS 加密再交给内核发送。

缺信任会发生两件事：

- **窃听**：旁路设备读到 Token、Cookie、请求体。调用大模型 API 时，密钥一旦泄露就是额度被盗用；
- **篡改 / 冒充**：中间设备可以把 `200` 改成钓鱼页，也可以假装自己是 `api.example.com`，把你的请求接下来。

只加密不够。如果密钥是和骗子协商出来的，加密反而给了你"安全"的错觉。所以 HTTPS 必须同时做到三件事：

```text
保密   路上的人读不懂          ← 加密
完整   路上的人改了会被发现    ← 报文校验 / AEAD
认证   对面真是这个域名        ← 证书
```

HTTPS 不是新的应用层协议，它是 **HTTP over TLS**：先在 443 端口完成 TCP 三次握手（第 4 课），再做 TLS 握手，之后才发送第八课那种 HTTP 报文。浏览器地址栏的锁头，锁的是这一层。

TLS 的前身叫 **SSL（Secure Sockets Layer，安全套接层）**。现在口语里还说"SSL 证书"，协议本身从 TLS 1.2 / 1.3 起算；面试答"HTTPS 用 TLS"即可，被追问再补一句 SSL 是过时的名字。

## 2. 对称加密与非对称加密

![为什么 HTTPS 要混合加密](./assets/network-hybrid-crypto.svg)

加密算法要回答的问题是：有一段明文，怎么变成只有拥有密钥的人才能还原的密文。密钥的用法把算法分成两类。

### 2.1 对称加密：一把钥匙开一把锁

加密和解密用**同一把密钥**。代表算法是 **AES（Advanced Encryption Standard，高级加密标准）**。特点是快，现代 CPU 有专门指令，加密几 MB 的 JSON 或模型输出几乎不构成瓶颈。HTTPS 里真正保护每一条 HTTP 报文的，就是对称加密（再带上完整性校验，合称 AEAD，Authenticated Encryption with Associated Data，带关联数据的认证加密——知道"既加密又防篡改"即可）。

致命短板：**这把钥匙怎么送到对方手里？** 明文传送，中间人直接拿走；为每个网站预先发一把不同的钥匙，互联网规模下做不到。对称加密解决"传得快"，解决不了"第一次见面"。

### 2.2 非对称加密：公钥锁，私钥开

密钥成对出现：**公钥**可以公开，**私钥**绝不离开持有者。

- 用公钥加密的数据，只有对应私钥能解密——用来**保密地送东西给持有私钥的那一方**；
- 用私钥"签名"的数据，任何人用公钥都能验证"确实是私钥持有者签的、中途没被改"——用来**证明身份**。

代表算法：**RSA（Rivest-Shamir-Adleman，三位发明人的姓氏）**；密钥交换还常用 **ECDHE（Elliptic Curve Diffie-Hellman Ephemeral，椭圆曲线临时迪菲-赫尔曼）**——双方各自出一份临时公钥，算出同一份共享秘密，共享秘密本身不在网上传递。

致命短板：**慢**，比 AES 慢一到三个数量级，不能拿它加密每一个数据包。第二个短板更隐蔽：你从网上收到的"公钥"，怎么知道是服务器的、不是中间人塞给你的？没有额外机制，非对称加密会被掉包攻击直接掏空。

### 2.3 为什么必须混合

把两类算法的短板对着一放，HTTPS 的设计就是唯一说得通的拼法：

1. **用证书把服务器公钥的身份钉死**（第 3 节，解决"公钥被掉包"）；
2. **用非对称算法（或 ECDHE 密钥交换）协商出一把一次性的会话密钥**——这把钥匙只在这一次 TCP 连接里用，用完即弃；
3. **之后所有 HTTP 字节都用这把会话密钥做对称加密**。

非对称只在握手时跑一小段，贵得起；对称承担全部业务流量，快得起。面试问"为什么不全程 RSA / 为什么不全程 AES"，按这两个短板答。

额外收益叫**前向保密（Forward Secrecy，前向保密）**：每次握手的会话密钥都是临时生成的。即便几年后服务器私钥泄露，过去已经结束的那些连接也解不开——因为当时的会话密钥并不是用"服务器长期私钥加密一份密钥再传过去"这种方式产生的，而是 ECDHE 当场算出来、从未离开过两台机器。TLS 1.3 强制要求前向保密。

## 3. 证书、CA 与中间人

![证书如何挡住中间人](./assets/network-cert-mitm.svg)

### 3.1 没有证书时，中间人直接成功

假设只做非对称、不做证书。你向 `api.example.com` 发起连接，中间人截获 Client Hello，把自己的公钥发给你。你用这把公钥加密，中间人解开，再转发给真服务器。你看到的是"已经加密"，实际上密钥握在中间人手里。这就是中间人攻击。

证书要挡住的，正是"**网上传来的公钥，凭什么是这个域名的**"。

### 3.2 一张证书里有什么

数字证书是一份被签名过的文件，核心字段：

| 字段 | 含义 |
| --- | --- |
| 主体 / 域名 | 这张证书证明谁。现代浏览器看 **SAN（Subject Alternative Name，主体备用名称）**，不再只看 CN（Common Name，通用名称） |
| 公钥 | 服务器握手时要用的那把公钥 |
| 有效期 | `notBefore` ~ `notAfter`，过期即失败 |
| 签发者 | 哪一家 CA 签的 |
| 签名 | CA 用自己的**私钥**对上面这些字段做的签名 |

验证过程：客户端用签发者的**公钥**解开签名，得到的摘要如果和证书内容一致，这份证书就没被改过，公钥也确实是 CA 当时担保过的那把。

### 3.3 信任链：你预装的是根，不是每一张网站证书

客户端不可能预存全世界每一张网站证书。它预存的是少数**根 CA** 的公钥（操作系统和浏览器出厂自带，`curl` 在 macOS 上用 `/etc/ssl/cert.pem`）。实际网站证书通常由**中间 CA** 签发，中间 CA 的证书再由根 CA 签发。验证时从网站证书往上追，直到追到本机已经信任的根——这条链叫**证书链**。

CA 在这里扮演的角色是**公证处**：网站向 CA 证明"我控制这个域名"（常见手段是在 DNS 加一条指定记录，或在 80 端口放一个指定文件），CA 才肯签。你信任浏览器，浏览器信任根 CA，根 CA 信任中间 CA，中间 CA 信任这张网站证书——信任是传导的。

### 3.4 证书过四关；中间人何时仍能成功

客户端对服务器证书至少做四件事，任何一件失败就中止握手，HTTP 请求不会发出：

1. **验签**：用链上 CA 的公钥验证签名；
2. **核对域名**：证书 SAN 必须覆盖你正在访问的主机名（访问 `api.example.com` 却拿到 `example.com` 且 SAN 不含前者，失败）；
3. **核对有效期**；
4. **追到信任锚**：签发者必须能连到系统信任的根 CA。自签证书卡在这一关。

中间人要伪造成功，必须让你的设备**信任他的签发者**。常见缺口不是算法被破解，而是：

- 用户在警告页点了"仍然访问"；
- 公司电脑安装了公司自己的根证书，HTTPS 代理才能解密员工流量（合法的企业审计，机制上就是中间人）；
- 设备被植入恶意根证书。

所以证书证明的是"**这把公钥属于这个域名**"，不是"这个网站是好人"。钓鱼站也可以买到合法证书——锁头只保证信道，不保证站点品德。

开发环境常见自签证书：自己当 CA 给 `localhost` 签发。`curl` 和浏览器默认拒绝，需要 `curl -k` 或把自签根加进信任库。生产环境不要关校验。

## 4. TLS 握手

![TLS 握手](./assets/network-tls-handshake.svg)

### 4.1 它插在哪一层

```text
输入 URL
  → DNS 把域名变成 IP                         （第 7 课）
  → TCP 三次握手连上 443 端口                  （第 4 课；HTTP 明文是 80）
  → TLS 握手：验证证书、协商会话密钥           （本课）
  → 在加密隧道里写出 HTTP 请求                 （第 8 课，内容不变）
  → 读回加密的 HTTP 响应
```

TLS 对应用层来说是一条已经保密的字节管道。第八课手写的那些 `\r\n`，在 HTTPS 里仍然原样存在，只是 `send` 之前被 TLS 记录层封成密文。框架和 `requests` 把这一步藏掉了，所以日常写业务时你感觉不到。

**SNI（Server Name Indication，服务器名称指示）**：Client Hello 里会带上你要访问的域名。一台服务器用同一个 IP 托管多个 HTTPS 站点时，必须在出示证书之前知道你要哪一个——否则它不知道把哪张证书给你。SNI 目前是明文的（加密 SNI 还在演进），所以"访问了哪个域名"有可能被路径上的设备看到，但路径和正文仍然是密文。

**ALPN（Application-Layer Protocol Negotiation，应用层协议协商）**：握手时客户端声明自己会 HTTP/1.1、HTTP/2，服务器选一个。`curl -v` 里那行 `ALPN: server accepted h2` 就是它。HTTP/2 本身第 10 课再讲，这里只要知道：它是在 TLS 里谈妥的，不是另一次握手。

### 4.2 按面试口径拆步骤

教材和面试仍按 TLS 1.2 的逻辑来问，目标四件事：**打招呼、验证身份、换钥匙、确认钥匙可用**。TLS 1.3 把其中几步合并，来回更少（1-RTT，Round-Trip Time，一个往返），目的不变。下面按"逻辑步骤"讲，不背记录类型编号。

**① Client Hello。** 客户端说：我支持的 TLS 版本、密码套件列表、一个随机数。密码套件是"密钥交换 + 签名 + 对称加密 + 哈希"的组合清单，服务器从中挑一套双方都会的。

**② Server Hello + 证书。** 服务器选定版本和套件，出示证书链。客户端立刻做第 3.4 节的四道检查。失败则连接断开，浏览器弹红页。

**③ 密钥交换。** 双方用 ECDHE 各自生成临时密钥对，把公钥交给对方，两边独立算出**同一把会话密钥**。会话密钥从不在网上传递。服务器还会用证书对应的私钥对这部分握手做签名，证明"刚才那张证书的私钥确实在我手里"——光出示证书不够，得证明你拥有私钥。

**④ Finished。** 双方用刚刚得到的会话密钥加密一段握手摘要发给对方。这一步同时确认：密钥算对了，握手消息没被中间人改过。从此应用数据全部对称加密。

TLS 1.3 把 ②③ 压进更少的报文，所以 `curl -v` 里你会看到 `Client hello`、`Server hello`、`Certificate`、`CERT verify`、`Finished` 紧挨着出现，而不是教科书上分得很开的四次来回。被问"TLS 1.3 和 1.2 的差别"，答：更少的往返、去掉了老旧算法、强制前向保密；被问"握手过程"，仍按上面四件事答。

### 4.3 握手之后、会话恢复

握手比发一条 HTTP 请求贵（非对称运算 + 至少一次往返）。同一台客户端短时间再次连接同一站点时，可以用会话票据 / 会话 ID 恢复，跳过完整证书校验和密钥交换，这叫**会话恢复（session resumption）**。知道"完整握手很贵，所以有快捷通道"即可，细节面试较少追到实现。

应用数据开始流动后，解密、完整性校验都由 TLS 记录层完成。你在 Wireshark 里看到的是"TLS Application Data"，看不到 URL 和 JSON——除非你在本机加载了服务器私钥做调试解密。

### 4.4 失败时是什么现象

把现象和关卡对上，排错才不跑偏：

| 现象 | 卡在哪 |
| --- | --- |
| 浏览器报证书不受信任 / `curl: SSL certificate problem` | 验签或信任锚失败（自签、公司代理、过期链） |
| 证书与域名不匹配 | SAN 对不上，多半 CDN 或反向代理配错证书 |
| 证书过期 | 有效期失败，Let's Encrypt 等短周期证书漏续期很常见 |
| 握手超时、连得上 443 但 TLS 完不成 | 中间设备干扰 TLS，或服务器只支持你客户端没有的套件 |
| 握手成功但 HTTP 4xx / 5xx | TLS 已经完成，问题回到第八课的应用层 |

`curl -k`（跳过证书校验）能让自签环境连通，也等于主动放弃第 3 节的全部保护，只适合本地调试。

## 5. HTTP 无状态：为什么需要"会话"

TLS 解决的是**这一条连接上的信道**。它不记得你是谁。HTTP 更是无状态：服务器处理完一条请求就可以忘掉它，第八课的作业服务器正是这样做的。

但产品需要状态："这个人已经登录"、"购物车里有三件商品"。办法只有一个——**让后续每个请求自己带上身份证明**。带什么、存在哪、服务器怎么验，分成三条常见路。它们不是互斥的三个登录按钮，而是两层东西：

```text
载体（怎么运）     Cookie 头  或  Authorization 头
内容（运的是什么）  随机 session_id  或  自包含的 JWT
```

![三种会话方式](./assets/network-session-compare.svg)

## 6. Cookie：浏览器自动回带的小票

### 6.1 一次完整往返

1. 你用账号密码 `POST /login`（走 HTTPS，否则密码明文）；
2. 服务器在**响应**里带 `Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Lax`；
3. 浏览器把这份 Cookie 存下来；
4. 之后对同一站点的请求，浏览器**自动**在请求头加 `Cookie: session_id=abc123`，页面 JS 不用、也常常不该插手。

`Set-Cookie` 是响应头，`Cookie` 是请求头，不要写反。Cookie 是 HTTP 协议提供的载体，里面装什么由应用决定：可以装 session_id，也可以装 Token。所以"Cookie vs Token"这种问法本身就不精确——Token 可以放在 Cookie 里运。

### 6.2 三个必须能讲清的属性

| 属性 | 作用 | 关掉会怎样 |
| --- | --- | --- |
| **HttpOnly** | 禁止 JavaScript 读这份 Cookie | XSS（Cross-Site Scripting，跨站脚本）偷到 Cookie 就能冒充登录 |
| **Secure** | 只在 HTTPS 上发送 | 站点若仍提供 HTTP，Cookie 会在明文请求里泄露 |
| **SameSite** | 限制跨站请求是否带上 Cookie：`Strict` 最严、`Lax` 为默认（顶级导航的 GET 会带）、`None` 必须同时 Secure | 跨站表单 / 图片请求会自动带上你的登录 Cookie，这就是 CSRF（Cross-Site Request Forgery，跨站请求伪造）的弹药 |

三个属性解决的是**浏览器这个特殊客户端**才有的问题。`curl` 和 Python `requests` 不会自动存 Cookie（除非你用 `Session` 对象），也不会执行页面里的 JS，所以 HttpOnly / SameSite 对它们几乎无感——它们要冒充你，得你自己把 Cookie 值写进请求。

另外两个常见字段：`Domain` / `Path` 控制哪些 URL 会带上这份 Cookie；`Max-Age` / `Expires` 控制过期。会话 Cookie（不写过期）在浏览器关闭时清除。

## 7. Session：状态放在服务器

Session 方案的要点是**状态不放在客户端**：

1. 登录成功，服务器在内存或 Redis 里创建一条记录 `{user_id, 过期时间, 权限…}`，生成一个随机、无含义的 `session_id`；
2. `session_id` 通过 `Set-Cookie` 下发给浏览器（所以 Session **几乎总是配 Cookie 用**）；
3. 后续请求带上这个 id，服务器拿它去存储里查完整状态。

优点直接来自"服务器说了算"：注销就是删记录，立刻失效；改权限立刻生效；客户端即使被抄走 id，管理员也能踢人。

代价也直接来自"服务器得记住"：每个登录用户占一份存储；多台应用服务器必须共享 Session 存储，否则用户这次打到 A 机器、下次打到 B 机器就会掉登录。这就是"Session 粘滞 / 集中式 Redis"在架构里出现的原因。

`session_id` 必须是密码学意义上的随机数。如果是 `user_id=1` 这种可猜的值，改一个数字就能变成别人。

## 8. Token 与 JWT：状态放在令牌里

开放 API、移动 App、前后端分离里更常见的是：**服务器不保存登录态，签发一张自包含的令牌，以后只验这张票。**

### 8.1 怎么携带

请求头（第八课见过）：

```text
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

`Bearer`（持有者）的含义是"谁持有这串字符，谁就被当作这个人"。所以 Token 泄露 = 身份泄露，必须走 HTTPS。调用大模型 API 的 `sk-…` 密钥，本质就是一种长期 Token。

和 Cookie 的关键差别：浏览器**不会**自动附加 `Authorization`。页面 JS 或 App 代码每次自己放进头里。这让它适合非浏览器客户端，也让它少掉一部分 CSRF（跨站页面没法让浏览器自动带上你的 Bearer Token）；但若你把 JWT 存进 `localStorage`，XSS 可以直接读走——换了个偷法。

### 8.2 JWT 的三段

一份 JWT 长这样，三段用 `.` 拼接：

```text
header.payload.signature
```

- **header**：算法，例如 HMAC-SHA256 或 RSA。只是 Base64URL 编码，谁都能解码；
- **payload**：声明（claims），如 `sub`（用户 id）、`exp`（过期时间）。**同样只是编码，不是加密**。不要把密码、密钥放进 payload。任何人拿到 JWT 都能读出你写进去的字段；
- **signature**：用服务器私钥或共享密钥对前两段做的签名。服务器验签通过，才能相信 payload 没被改过。

"JWT 是加密的"是常见误区。JWT 默认解决的是**防篡改**（完整性和认证），不是**防读取**。防读取靠 HTTPS。

### 8.3 和无状态的代价

优点：服务器不必查询 Session 存储，水平扩展简单，微服务之间传一份 JWT 就能识别调用者。

代价：

- **注销困难**。票已经签发出去，在 `exp` 之前都有效。真要立刻作废，还得维护一份黑名单——那又变回"服务器保存状态"；
- **权限变更滞后**。把管理员降为普通用户之后，旧 JWT 在过期前仍带着旧角色；
- **体积**。Cookie 里的 session_id 几十字节，JWT 常要几百字节，每个请求都带着。

工程上的折中是短寿命的 access token + 较长寿命的 refresh token：前者过期得快，被盗窗口小；刷新时服务器有机会拒绝。本课知道"短 + 刷新"这个组合即可。

## 9. 怎么选，以及它们如何组合

口诀：

```text
Cookie   是卡车——浏览器自动运
Session  是仓库里的档案——状态在服务器，卡车里只放钥匙
JWT      是自带公章的介绍信——状态写在信上，服务器只验章
```

典型组合：

| 场景 | 常见做法 |
| --- | --- |
| 浏览器访问自己的网站 | Session + Cookie（HttpOnly、Secure、SameSite） |
| 手机 App / 桌面客户端 | JWT 放 `Authorization`，存在系统钥匙串，不靠 Cookie |
| 调用第三方 HTTPS API | 长期 Token / API Key，放 `Authorization` |
| 需要"点一下就踢人下线" | 倾向 Session，或 JWT + 黑名单 / 短过期 |
| 需要网关无状态校验、服务之间传递身份 | 倾向 JWT |

没有 HTTPS，这三种都是路上可被读走的字符串。会话方案建立在第 2～4 节的信道之上，不能单独成立。

## 10. 终端演示

命令详解在第 11 课，这里先会看输出。

### 10.1 用 curl 观察 TLS 握手

`example.com` 是 IANA 保留的演示域名，专门给文档用：

```bash
curl -vI --http1.1 https://example.com
```

`-v` 打印握手过程，`-I` 只取响应头，`--http1.1` 让应用层仍是第八课熟悉的报文（否则现代服务器会通过 ALPN 升级到 HTTP/2，响应头长相对不上号）。输出里按时间顺序对这几行：

```text
Connected to example.com (...) port 443     ← TCP 握手已完成
TLS handshake, Client hello                 ← 第 4.2 节①
CAfile: /etc/ssl/cert.pem                   ← 本机信任锚
TLS handshake, Server hello                 ← ②
TLS handshake, Certificate                  ← 证书链到来
TLS handshake, CERT verify                  ← 证明服务器持有私钥
TLS handshake, Finished                     ← ④ 双方 Finished
SSL certificate verify ok                   ← 第 3.4 节四关都过了
subject: CN=example.com                     ← 域名对得上
issuer: ... CA ...                          ← 签发者，可追到根
```

对比一次失败（自签或域名不匹配时才会看到，不必强行制造）：

```bash
curl -vI https://expired.badssl.com
```

会在证书校验处停下，后面没有 HTTP 响应——这就是"握手失败则请求发不出去"。

看完握手，再对照第八课读 `>` 请求头和 `<` 响应头：内容仍是 HTTP，只是它们现在走在 TLS 隧道里。

### 10.2 用 requests 看两种身份怎么进报文

`requests` 是第三方库（`pip install requests` 或课程环境 `agent_dev` 里已有）。它内部用标准库 `ssl` 完成 TLS 握手，用 CookieJar 管理 Cookie，用预备好的头部发送 HTTP——第八课手写的那些字节，被它藏起来了。

下面两段**不依赖外网服务是否实现了登录**，只把"报文上会出现什么头"打印出来。在项目环境执行（`conda run` 默认会吞掉输出，这里加上 `--no-capture-output`；如果已经 `conda activate agent_dev`，直接跑 `python` 即可）：

```bash
conda run -n agent_dev --no-capture-output python - <<'PY'
import requests

cookie_req = requests.Request(
    "GET",
    "https://api.example.com/v1/tasks",
    cookies={"session_id": "abc123"},
).prepare()
print("携带 Cookie 时的请求头：")
print(dict(cookie_req.headers))

token_req = requests.Request(
    "GET",
    "https://api.example.com/v1/tasks",
    headers={"Authorization": "Bearer sk-demo-token"},
).prepare()
print("携带 Bearer Token 时的请求头：")
print(dict(token_req.headers))
PY
```

应当看到前者自动出现 `Cookie: session_id=abc123`，后者出现 `Authorization: Bearer sk-demo-token`。这就是第 6 节和第 8 节在报文上的全部差别。

`requests.Session()` 会在多次请求之间记住 `Set-Cookie`，模拟浏览器的自动回带；默认的一次性 `requests.get` 不会。想观察"登录响应里的 Set-Cookie 被下一跳自动带上"，用 `Session`。本课不接真实登录接口，知道这个对象的职责即可。

## 11. 验收问题

1. HTTPS 和 HTTP 的报文结构有什么不同？TLS 插在第 4 课和第 8 课之间的哪一步？
2. 对称加密和非对称加密各自的短板是什么？HTTPS 如何把它们拼在一起？什么是前向保密？
3. 证书里最关键的字段有哪些？客户端验证时过哪四关？
4. 中间人攻击在"只有加密、没有证书"时为什么能成功？有了 CA 之后，攻击者还要具备什么条件？
5. 按逻辑步骤讲述 TLS 握手。TLS 1.3 主要改了什么、没改什么？
6. Cookie、Session、JWT 分别把状态放在哪？为什么说"Cookie vs Token"这个问法不精确？
7. `HttpOnly`、`Secure`、`SameSite` 各防什么？对 `curl` / `requests` 为什么几乎无感？
8. JWT 的 payload 是加密的吗？Token 泄露和 Session ID 泄露，各自最坏的后果是什么？注销哪一种更容易立刻生效？

## 12. 面试高频考点

- HTTPS = HTTP + TLS；明文 HTTP 的窃听 / 篡改 / 冒充问题。
- 对称 vs 非对称，以及**必须混合**的原因（速度 × 密钥分发 × 公钥认证）。
- 前向保密：临时会话密钥，私钥日后泄露也解不开旧流量。
- 证书链、CA、签名；中间人攻击；证书验证四关（签名、域名、有效期、信任锚）。
- TLS 握手逻辑四步：Hello、证书、密钥交换、Finished。TLS 1.3 减少往返、强制前向保密。
- Cookie 是载体；Session 状态在服务端；JWT 状态在令牌里。三者可以组合。
- Cookie 属性：HttpOnly / Secure / SameSite 与 XSS、窃听、CSRF。
- JWT 三段，payload 可解码不可篡改；`Authorization: Bearer`；无状态带来的注销难题。
- "输入 URL 之后发生了什么"补上 TLS 这一段（DNS 第 7 课，HTTP 报文第 8 课，加密信道本课）。
