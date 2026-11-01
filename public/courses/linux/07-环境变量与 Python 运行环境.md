# 第7课:环境变量与 Python 运行环境

上一课（第 6 课）预告过：脚本有时要用 `./script.sh` 而不是 `script.sh` 运行，答案在 PATH 里。本课讲清楚环境变量和 Python 运行环境：PATH 决定 Shell 去哪里找命令，`which` 确认命令位置，`python --version`、`which python`、`sys.executable` 三者的区别，以及虚拟环境 venv 如何通过 PATH 切换解释器。这是排查"包装了却 import 不到"这类问题的基础。本课命令示例中，`#` 后是注释，实际执行时不输入。

**学习目标：**

1. 能解释环境变量是什么、进程和环境变量的关系；
2. 能用 `echo`、`env`、`export` 查看和设置环境变量，理解单双引号对变量展开的影响；
3. 能解释 PATH 的查找顺序，回答"command not found"的两个常见原因；
4. 能区分 `which python` 与 `sys.executable`，解释为什么只输出版本号不足以确认环境；
5. 能用 venv 创建并激活虚拟环境，解释激活后 PATH 发生了什么变化；
6. 知道密钥只通过环境变量传递，不写进代码或仓库。

## 1. 环境变量是什么：进程启动时拿到的一组配置

程序启动时需要一些"外界配置"：用户主目录在哪、当前用户是谁、去哪里找命令。这些信息由**环境变量（environment variable）**携带——它是操作系统传给每个进程的一组"名称=值"的配置，进程启动时继承一份，运行中随时可以读取。

三个最常见的环境变量：

| 变量 | 含义 |
| --- | --- |
| `HOME` | 当前用户的主目录路径 |
| `USER` | 当前用户名 |
| `PATH` | Shell 找命令的目录列表（第 3 节展开） |

**边界**：环境变量是**进程级**的——你在一个终端窗口里 `export` 的变量，只对当前 Shell 和它启动的子进程可见，不影响其他窗口；进程退出就消失。所以"配置只在当前会话有效"是常态，不是 bug。

## 2. 查看和设置环境变量：echo、env、export

第 5 课日志脚本里出现过 `echo`，本课正式介绍它：**`echo`** 把后面的文字打印到屏幕，常用来查看变量值。

**常用形式**

```text
echo [文字 ...]
```

| 写法 | 含义 |
| --- | --- |
| `echo hello` | 打印 `hello` 这几个字符 |
| `echo "$HOME"` | 打印 `HOME` 变量的值（`$` 表示"取变量的值"） |
| `echo '$HOME'` | 打印字面量 `$HOME`（单引号内不展开变量） |

**`env`** 列出当前进程的全部环境变量：

**常用形式**

```text
env
```

```bash
echo "$HOME"    # 打印主目录路径
echo "$USER"    # 打印当前用户名
env             # 列出所有环境变量
```

**`export`** 设置或修改环境变量（对当前 Shell 及它启动的子进程生效）：

**常用形式**

```text
export 名称=值
```

```bash
export MY_VAR=hello    # 设置当前 Shell 的 MY_VAR
echo "$MY_VAR"         # 打印出 hello
```

注意单双引号的差别：`echo "$HOME"` 会展开变量、输出主目录路径；`echo '$HOME'` 输出的是字符 `$HOME`。排查"变量值为什么没展开"时，先看引号。

## 3. PATH：Shell 去哪里找命令

输入 `python` 时，Shell 并不知道 `python` 在哪。它靠 **PATH** 找：PATH 是一个由目录组成的列表（用 `:` 分隔），Shell 按顺序在**每个目录里**找输入的命令名，找到第一个就运行它。

```text
你输入 python
  -> 读 PATH：/usr/local/bin:/usr/bin:/bin ...
  -> 依次去每个目录找名叫 python 的可执行文件
  -> 找到第一个就运行，找不到报 command not found
```

```bash
echo "$PATH"    # 看 PATH 内容，目录之间用 : 分隔
```

**command not found 的两个常见原因**：命令没安装；命令装了但所在目录不在 PATH 里（比如手动装到 `/opt/xxx/bin`）。后者不需要重装，把目录加进 PATH 即可，但修改 PATH 属于"改环境配置"，本课只要求理解机制，不展开持久化写法。

这也解释了第 6 课的遗留问题：当前目录 `.` 通常**不在** PATH 里，所以直接输入 `script.sh` 会 command not found；`./script.sh` 是显式写出路径"当前目录下的 script.sh"，Shell 不再依赖 PATH。

## 4. which：确认命令的真实位置

**`which`** 按 PATH 的规则替你把命令找一遍，输出找到的完整路径：

**常用形式**

```text
which 命令名
```

```bash
which python    # 输出 Shell 会运行的 python 完整路径
which rg        # 第 2 课用过的 rg 在哪
```

`which` 和 PATH 的关系：它就是"按 PATH 顺序找第一个命中"的查询工具。系统里可能同时存在多个 `python`（系统自带一个、虚拟环境一个），`which python` 显示的永远是 PATH 里先命中的那个。

## 5. 确认 Python 解释器：--version、which、sys.executable

排查"pip 装了包，但 `import` 不到"这类问题时，关键不是版本号，而是**当前用的是哪个解释器**。三个命令回答三个不同的问题：

| 命令 | 回答的问题 | 局限 |
| --- | --- | --- |
| `python --version` | 版本号是多少 | 系统 Python 和 venv Python 版本可能完全相同 |
| `which python` | Shell 从 PATH 找到的 python 命令在哪 | 显示 PATH 命中的第一个 |
| `python -c 'import sys; print(sys.executable)'` | 当前进程**真正**使用的解释器路径 | 需要实际运行 Python |

```bash
python --version                                   # 只看到版本号
which python                                       # Shell 用的是哪个 python
python -c 'import sys; print(sys.executable)'      # 当前解释器的真实路径
```

`sys.executable` 是最可信的答案：它由正在运行的 Python 自己报告"我是谁"。**只输出版本号不足以确认环境**——版本相同但解释器不同（系统 vs venv）是完全常见的情况，这就是面试里"确认 Python 环境要看路径而不是版本号"的原因。

## 6. 虚拟环境 venv：通过 PATH 切换解释器

不同项目依赖不同版本的库，全装到系统里会互相冲突。**虚拟环境（venv）** 为每个项目准备一份独立的 Python 环境，有自己的依赖目录，互不干扰。

**`venv` 的工作原理**：`python -m venv myenv` 在 `myenv` 目录里放一份指向解释器的入口和独立的依赖目录；激活时把 `myenv/bin` 插到 PATH 的**最前面**，于是输入 `python` 先命中 venv 里的入口，用的就是 venv 的解释器：

```text
激活前 PATH:  /usr/local/bin:/usr/bin:...
  -> python = /usr/bin/python            # 系统解释器
激活后 PATH:  ~/myenv/bin:/usr/local/bin:/usr/bin:...
  -> python = ~/myenv/bin/python         # venv 解释器（排在最前，先命中）
```

**常用形式**

```text
python -m venv 环境目录
source 环境目录/bin/activate
deactivate
```

| 命令 | 含义 |
| --- | --- |
| `python -m venv myenv` | 创建虚拟环境 `myenv` |
| `source myenv/bin/activate` | 激活它：把 `myenv/bin` 插到 PATH 最前面 |
| `deactivate` | 退出虚拟环境，PATH 恢复原样 |

```bash
python -m venv ~/linux-course-tmp/myenv                 # 创建
source ~/linux-course-tmp/myenv/bin/activate            # 激活
which python                                            # 变成 venv 里的 python
python -c 'import sys; print(sys.executable)'           # 也变成 venv 路径
deactivate                                              # 退出
which python                                            # 恢复系统 python
```

注意三点：激活只改**当前 Shell** 的环境变量，换一个终端窗口就失效，需要重新 `source`；退出终端也一样；Windows 的 cmd 里激活脚本名不同（`activate.bat`），本课以 Linux（含 WSL）的 `source` 为准。

## 7. 密钥只走环境变量

`env` 会把全部环境变量打印出来，其中可能包含 API Key 等敏感信息。工程规范是：

1. 密钥用 `export` 设置（如 `export API_KEY=...`），程序运行时从环境变量读取，**不写进代码、不写进仓库**；
2. 不要把完整 `env` 输出贴到公开场合（第 1 课提过，这里正式强调）；
3. 换机器或换人时，环境变量不随代码走，密钥也就不会因为代码分发而泄露。

## 8. 本课命令速查表

| 命令 | 含义 | 常用参数 |
| --- | --- | --- |
| `echo` | 打印文字或变量值 | `"$变量"` 展开取值 |
| `env` | 列出当前进程的全部环境变量 | 无 |
| `export` | 设置或修改环境变量 | `名称=值` |
| `which` | 显示命令在 PATH 中的完整路径 | 命令名 |
| `python -m venv` | 创建虚拟环境 | 环境目录路径 |
| `source` | 执行脚本并修改当前 Shell 环境（激活 venv 用） | 脚本路径 |
| `deactivate` | 退出当前虚拟环境 | 无 |

## 9. 常见错误

| 常见错误 | 现象 | 正确做法 |
| --- | --- | --- |
| 直接输入脚本名 | command not found | 当前目录的脚本用 `./script.sh` |
| 只查 `python --version` | 版本号正确但环境不对 | 再看 `which python` 和 `sys.executable` |
| 忘记激活 venv | pip 装到了全局环境 | 每个新终端先 `source .../bin/activate` |
| 激活后换窗口 | venv 又失效 | 激活只对当前 Shell 有效，重新 `source` |
| `echo '$HOME'` | 输出的是 `$HOME` 而不是路径 | 用双引号 `echo "$HOME"` |
| 把密钥写进代码 | 密钥随代码进仓库 | 用 `export` 设置，代码从环境变量读 |

## 10. 运行本课命令练习

```bash
echo "$HOME"                                             # 主目录
echo "$USER"                                             # 用户名
env                                                      # 全部环境变量（别把输出贴到公开地方）
echo "$PATH"                                             # PATH 内容，目录用 : 分隔
which python                                             # Shell 找到的 python 位置
python --version                                         # 版本号
python -c 'import sys; print(sys.executable)'            # 当前解释器真实路径
# 创建并激活虚拟环境，观察 PATH 变化：
python -m venv ~/linux-course-tmp/myenv
source ~/linux-course-tmp/myenv/bin/activate
which python                                             # 应变成 venv 里的 python
python -c 'import sys; print(sys.executable)'            # 也应变成 venv 路径
deactivate                                               # 退出
which python                                             # 恢复系统 python
```

## 11. 课后作业（命令练习）

本课没有代码文件，请在终端完成以下任务并记录结果：

1. 执行 `echo "$PATH"`，把输出按 `:` 拆开，写出前三个目录。
2. 用 `which` 分别查看 `python`、`rg`、`ls` 的位置，说明 `which` 和 PATH 的关系。
3. 创建 venv 并激活，分别记录激活前后 `which python` 和 `sys.executable` 的输出，解释为什么"只输出版本号不足以确认环境"。
4. 用 `export MY_VAR=test` 设置变量，分别用 `echo "$MY_VAR"` 和 `echo '$MY_VAR'` 输出，解释差异；再开一个新终端窗口执行 `echo "$MY_VAR"`，说明为什么为空。
5. 用自己的话解释：为什么直接输入 `script.sh` 会 command not found，而 `./script.sh` 可以。

## 12. 验收问题 / 过关清单

1. 环境变量是什么？它和进程是什么关系？"只对当前 Shell 有效"是什么意思？
2. `echo "$HOME"` 和 `echo '$HOME'` 输出有什么不同，为什么？
3. PATH 是什么？Shell 怎么用 PATH 找命令？command not found 的两个常见原因是什么？
4. `which python` 回答什么问题？它和 `sys.executable` 有什么区别？
5. 为什么只输出版本号不足以确认 Python 环境？
6. venv 是什么？激活之后 PATH 和 `which python` 发生了什么变化？`deactivate` 做了什么？
7. 设置 API Key 的正确方式是什么？为什么不能写进代码或仓库？

## 13. 面试高频考点

- **PATH 是什么、为什么 command not found**：口述模板："PATH 是目录列表，Shell 按顺序在目录里找输入的命令。command not found 要么命令没装，要么它所在的目录不在 PATH 里；当前目录通常不在 PATH 里，所以运行当前目录的脚本要写 `./script.sh`。"
- **which python 与 sys.executable 的区别**：口述模板："`which python` 是 Shell 按 PATH 规则找到的命令位置，`sys.executable` 是正在运行的 Python 自己报告的解释器路径，后者更可信。两者在 venv 激活后都指向 venv，退出后回到系统路径。"
- **为什么只输出版本号不足以确认环境**：口述模板："系统 Python 和 venv Python 版本可以完全一样，版本号无法区分解释器；确认环境要看路径——`which python` 或 `sys.executable`。"
- **虚拟环境如何工作**：口述模板："venv 在项目目录里建一份独立环境，有自己的 bin 和依赖目录；激活就是把 venv 的 bin 目录插到 PATH 最前面，所以输入 `python` 先命中 venv 的解释器；`deactivate` 把 PATH 恢复原样。激活只对当前 Shell 有效。"
- **密钥管理**：口述模板："密钥用环境变量传递，程序运行时从环境变量读取，不写进代码或仓库；`env` 能列出全部环境变量，不要把输出贴到公开场合。"

## 14. 小结与下一课预告

环境变量是"进程启动时拿到的配置"：PATH 决定去哪找命令，`which` 是 PATH 的查询工具，`sys.executable` 确认真正的解释器，venv 靠把目录插到 PATH 最前面来切换环境。这一套是"为什么这里 python 和那里 python 不一样"的标准答案。

下一课进入进程的世界——**程序、进程与退出**：程序与进程的区别、PID、`ps`/`top` 观察、前台后台运行、`kill` 与信号、退出码与 traceback。本课开始配第一个 Python 代码文件。
