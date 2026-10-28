
# DFS：深度优先搜索

## 第一部分：核心思想与定义

### 1. 一句话定义

DFS（Depth-First Search，深度优先搜索）是一种沿着一条路径不断深入，直到无法继续前进，再返回上一步尝试其他路径的搜索方法。

DFS 不限定使用某一种数据结构：可以使用递归，也可以显式使用栈。它常用于遍历图、网格和其他具有“连接关系”的数据。

### 2. 核心思想

DFS 的过程可以概括为：

```text
进入当前状态
    ↓
标记当前状态已访问
    ↓
尝试所有可以继续的方向
    ↓
递归或入栈访问下一个状态
    ↓
当前路径无法继续时返回
```

例如在网格中寻找一块区域，可以从一个未访问的格子出发，向上、下、左、右四个方向继续搜索，把能够连通的格子全部访问一遍。

### 3. DFS 的两个关键问题

#### 访问过的状态必须记录

图中可能存在环，网格中的相邻关系也可能让搜索回到之前的位置。如果不记录访问状态，搜索可能在几个节点之间无限循环。

常见做法是使用：

- `visited` 集合保存已经访问过的节点；
- `visited` 二维数组保存已经访问过的网格位置；
- 直接修改输入网格，将已访问位置改成特殊标记。

#### 每个状态的后继状态是什么

写 DFS 前要明确当前状态可以走向哪些状态：

- 图：当前节点的所有邻接节点；
- 网格：当前位置的四个或八个方向；
- 字符串或数组：当前下标之后的其他选择。

### 4. DFS 与递归的关系

递归是实现 DFS 的常见工具，但两者不是同一个概念：

- DFS 是一种搜索顺序；
- 递归是实现这种搜索顺序的一种方式；
- 也可以使用显式栈实现 DFS。

递归 DFS 代码通常更简洁，显式栈 DFS 更容易控制栈空间，也可以避免递归深度过深的问题。

---

## 第二部分：适用场景与问题识别

### 1. 问题特征信号

看到下面这些关键词时，可以考虑 DFS：

- 遍历所有节点或所有连通区域；
- 判断两个节点是否连通；
- 统计连通分量、岛屿数量或区域数量；
- 找出所有满足条件的路径；
- 网格中的染色、填充和区域搜索；
- 图中是否存在环；
- 需要沿一条路径深入，再返回尝试其他方向。

### 2. 先建立选择直觉：DFS 适合什么

把搜索想成走迷宫：DFS 会选择一条路一直走，走到尽头或走不通时，再退回最近的岔路口换路。因此它擅长回答的不是“最近要走几步”，而是下面三类问题：

| 题目真正想问什么 | 优先想 DFS 的原因 | 典型结果 |
| :--- | :--- | :--- |
| 哪些位置属于同一个区域？一共有几个区域？ | 一次深入搜索，正好可以把整个连通区域标记完 | 岛屿数量、区域面积、连通分量 |
| 从这里出发能不能到那里？ | 沿着可走路径不断深入，找到目标就可以结束 | 是否存在路径、是否连通 |
| 所有可能的路径或选择是什么？ | DFS 天然维护“当前正在走的路径”，退回时再换一个选择 | 所有路径、组合、排列（后续回溯课展开） |

一句话记忆：**DFS 像“探洞”——先钻到底；适合找连通区域、判断可达、枚举路径。**

例如“岛屿数量”中，我们不在乎从一块陆地走到另一块陆地最少走几步；我们只想知道这块陆地能连到哪些陆地。因此，从任意一块未访问陆地出发 DFS，把整座岛染掉，正好符合问题目标。

### 3. 与 BFS 的对比：先根据问题目标选方法

| 看到的题目表达 | 应优先想到 | 原因 |
| :--- | :--- | :--- |
| 连通、区域、能否到达、所有路径 | DFS | 沿一条路深入，方便完整探索一块区域或一条路径 |
| 最少几步、最短距离、最少操作 | BFS | 按距离一层层扩散，第一次到达目标就是最短 |
| 从多个起点同时扩散、最近的某个源 | BFS | 所有起点同时作为第 0 层扩散 |
| 只要求遍历或判断可达 | DFS 或 BFS 都可以 | 根据实现方便程度选择；递归 DFS 往往更短 |

核心区别不是“一个能做、另一个不能做”，而是搜索顺序不同：

```text
DFS：一条路走到底 -> 返回 -> 换路
BFS：先走完 1 步能到的所有位置 -> 再走完 2 步能到的所有位置
```

所以：**DFS 不保证最短路径；BFS 在每次移动代价相同的前提下保证最短路径。**

---

## 第三部分：标准化解法模板

### 1. 先记住 DFS 的四个固定结构

不管是图还是网格，DFS 都离不开这四件事：

```text
当前状态：我现在在哪个节点 / 哪个格子？
visited：哪些状态已经访问，不能再走？
directions / neighbors：从当前位置下一步可以去哪里？
搜索容器：递归调用栈，或显式 stack
```

网格题中的 `directions` 通常固定为四个方向：

```python
# 每个元组表示一次坐标移动：(行变化量, 列变化量)
directions = ((1, 0), (-1, 0), (0, 1), (0, -1))
```

它表示下、上、右、左。写成统一的方向数组后，不需要手写四次几乎一样的递归调用，也更不容易漏方向。

### 2. 网格 DFS 万能骨架

```python
# 步骤 0：定义状态转移方向
directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

def dfs(row, col):
    # 步骤 1：检查当前状态是否合法
    if not (0 <= row < rows and 0 <= col < cols):
        return

    # 步骤 2：检查当前状态是否允许继续访问
    if grid[row][col] != "1":
        return

    # 步骤 3：标记当前状态，防止后续重复访问
    grid[row][col] = "0"

    # 步骤 4：递归访问所有相邻状态
    for dr, dc in directions:
        dfs(row + dr, col + dc)
```

这四步就是岛屿数量、图像渲染、最大岛屿面积等题目的共同骨架。不同题目通常只改变两处：什么叫“可走”，以及访问一个格子时需要统计、修改还是返回什么。

### 3. 图的递归 DFS 模板

```python
def dfs(node, graph, visited):
    # 步骤 1：跳过已访问状态
    if node in visited:
        return

    # 步骤 2：标记当前状态
    visited.add(node)

    # 步骤 3：递归访问相邻状态
    for neighbor in graph[node]:
        dfs(neighbor, graph, visited)
```

使用时需要先准备邻接表和访问集合：

```python
# 邻接表：每个节点对应其相邻状态
graph = {
    0: [1, 2],
    1: [0, 3],
    2: [0],
    3: [1],
}

# 访问记录：避免重复处理状态
visited = set()

# 从指定起点开始搜索
dfs(0, graph, visited)
```

### 4. 图的迭代 DFS 模板

```python
def dfs(start, graph):
    # 步骤 1：初始化访问记录和待处理栈
    visited = set()
    stack = [start]

    # 步骤 2：持续处理待访问状态
    while stack:
        # 步骤 3：取出一个待处理状态
        node = stack.pop()

        # 已处理状态直接跳过
        if node in visited:
            continue

        # 步骤 4：标记当前状态
        visited.add(node)

        # 步骤 5：将可访问的相邻状态加入栈
        for neighbor in graph[node]:
            if neighbor not in visited:
                stack.append(neighbor)
```

递归版本由系统调用栈保存待返回的位置，迭代版本由 `stack` 显式保存待访问节点。

### 5. 用 `visited` 而非原地修改的网格 DFS

```python
# 步骤 0：定义状态转移方向
directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

def dfs(row, col, grid, visited):
    # 步骤 1：准备边界信息
    rows, cols = len(grid), len(grid[0])

    # 步骤 2：检查当前状态是否合法
    if row < 0 or row >= rows or col < 0 or col >= cols:
        return

    # 步骤 3：检查当前状态是否允许访问
    if grid[row][col] != "1" or (row, col) in visited:
        return

    # 步骤 4：标记当前状态
    visited.add((row, col))

    # 步骤 5：递归访问相邻状态
    for dr, dc in directions:
        dfs(row + dr, col + dc, grid, visited)
```

`visited` 和“把 `grid[row][col]` 改成其他值”作用相同：都是防止重复访问。原地修改更省空间，但会改变输入；需要保留原网格时使用 `visited`。

### 6. 图的连通分量模板

```python
def count_components(n, edges):
    # 步骤 1：构建状态之间的相邻关系
    graph = [[] for _ in range(n)]
    for a, b in edges:
        # 无向关系需要双向记录
        graph[a].append(b)
        graph[b].append(a)

    # 记录已归属到某个分量的状态
    visited = set()
    count = 0

    def dfs(node):
        # 步骤 2：跳过已访问状态
        if node in visited:
            return

        # 步骤 3：标记当前状态，并搜索其邻居
        visited.add(node)
        for neighbor in graph[node]:
            dfs(neighbor)

    # 步骤 4：从每个未访问状态开始一次新的搜索
    for node in range(n):
        if node not in visited:
            count += 1
            dfs(node)

    # 步骤 5：返回搜索次数，即分量数量
    return count
```

外层循环保证每个没有被访问的节点都能作为一个新连通分量的起点。

### 7. DFS 的复杂度

对于有 `V` 个节点、`E` 条边的图：

- 时间复杂度：$O(V + E)$，每个节点和每条边最多处理有限次；
- 空间复杂度：$O(V)$，包括访问集合和递归栈或显式栈。

对于 `R × C` 的网格：

- 时间复杂度：$O(RC)$；
- 空间复杂度：$O(RC)$，最坏情况下所有格子都进入搜索栈或访问集合。

### 8. DFS 的边界条件与陷阱

- 忘记记录访问状态，导致图中有环时无限搜索；
- 网格 DFS 忘记检查边界，访问非法下标；
- 标记时机太晚，同一个状态可能被重复加入；
- 递归函数没有正确返回，导致结果无法向上层传递；
- 原地修改网格后忘记这是有意的，后续逻辑仍需要原始数据时应使用 `visited`；
- 递归深度过大时触发 `RecursionError`，可以改用显式栈。

---

## 第四部分：DFS 精选题目与学习路径

### 核心母题

1. **[LeetCode #200 岛屿数量](https://leetcode.cn/problems/number-of-islands/)**

   - **为什么选此题**：网格 DFS 的经典题，练习发现一个区域后将整个区域搜索并标记。
   - **核心思路**：遇到未访问的陆地时，答案加一，然后 DFS 淹没与它连通的所有陆地。
   - **复杂度**：时间 $O(RC)$，空间 $O(RC)$（包含最坏递归栈）。

2. **[LeetCode #695 岛屿的最大面积](https://leetcode.cn/problems/max-area-of-island/)**

   - **为什么选此题**：在“统计岛屿数量”的基础上，练习让 DFS 返回当前连通区域的大小。
   - **核心思路**：从每块未访问陆地出发 DFS，返回该岛屿面积，并维护最大值。

3. **[LeetCode #733 图像渲染](https://leetcode.cn/problems/flood-fill/)**

   - **为什么选此题**：虽然不在 Hot 100 中，但它是最直接的区域扩散题，适合专门练习网格边界判断和访问标记。
   - **核心思路**：从起点出发，只访问颜色相同的相邻位置，并将其修改为目标颜色。

### 变式进阶

1. **[LeetCode #130 被围绕的区域](https://leetcode.cn/problems/surrounded-regions/)**：从边界上的 `O` 出发 DFS，标记所有与边界连通的区域。

2. **[LeetCode #133 克隆图](https://leetcode.cn/problems/clone-graph/)**：DFS 遍历图，同时使用哈希表保存原节点到新节点的映射。

3. **[LeetCode #207 课程表](https://leetcode.cn/problems/course-schedule/)**：使用 DFS 的三色标记法检测有向图中是否存在环。

### 学习顺序建议

```text
网格四方向 DFS
    ↓
岛屿与连通区域
    ↓
图的邻接表 DFS
    ↓
有向图环检测
    ↓
需要保存状态的图搜索
```

# BFS：广度优先搜索

## 第一部分：核心思想与定义

### 1. 一句话定义

BFS（Breadth-First Search，广度优先搜索）从起点开始，先访问距离为 1 的所有状态，再访问距离为 2 的所有状态，按照距离由近到远逐层扩展。

BFS 的核心工具是队列：新发现的状态从队尾进入，按照发现顺序从队首取出处理。

### 2. 核心思想

```text
起点入队
    ↓
取出队首状态
    ↓
加入所有未访问的相邻状态
    ↓
继续处理队列中的下一个状态
```

因为距离更近的状态总是先入队、先出队，所以在每一步代价相同的图中，BFS 第一次到达某个状态时，走过的路径就是最短路径。

### 3. 为什么 BFS 能找到最短步数

假设从起点开始：

- 第 0 层只有起点；
- 第 1 层是一步可以到达的状态；
- 第 2 层是两步可以到达的状态；
- 之后依次类推。

队列保证第 `d` 层全部处理完后，才会开始处理第 `d + 1` 层。因此，第一次访问目标状态时，不可能存在一条更短但尚未处理的路径。

这个结论成立的前提是：每条边的移动代价相同，通常就是每次移动代价为 1。

### 4. BFS 的层序处理

如果需要计算“最少几步”，可以在每一轮处理当前层的所有节点：

```python
# 当前层距离起点的步数
steps = 0
while queue:
    # 固定当前层的状态数量
    level_size = len(queue)
    for _ in range(level_size):
        # 处理当前层的一个状态
        pass
    # 进入下一层
    steps += 1
```

`level_size` 固定了当前层的边界，当前层中新发现的节点会留到下一轮处理。

---

## 第二部分：适用场景与问题识别

### 1. 问题特征信号

看到下面这些关键词时，可以优先考虑 BFS：

- 最少几步、最短距离、最少操作次数；
- 从起点扩散到所有位置；
- 同时从多个起点开始扩散；
- 一次操作可以移动到相邻状态；
- 单词转换、密码转换等状态之间的最短转换次数；
- 无权图中的最短路径。

### 2. 先建立选择直觉：BFS 为什么像扩散

把 BFS 想成水面投入一颗石子后的波纹：离起点一步的位置先被波纹碰到，离起点两步的位置随后被碰到。队列保证所有距离相同的状态在同一层被处理。

因此，BFS 最适合下面三类问题：

| 题目真正想问什么 | 优先想 BFS 的原因 | 典型结果 |
| :--- | :--- | :--- |
| 从起点到终点最少几步？ | BFS 按距离从近到远扩散，第一次到达终点必然最短 | 最短路径长度、最少操作次数 |
| 多个源同时扩散，多久覆盖全部？ | 所有起点同时放进第 0 层，扩散过程自然模拟时间 | 腐烂的橘子、传播时间 |
| 每个位置距离最近源多远？ | 第一次被访问时，距离就是最近源距离 | 01 矩阵、最近设施距离 |

一句话记忆：**BFS 像“水波扩散”——一圈一圈向外；适合最少步数、最短距离、同时扩散。**

### 3. 与 DFS 的对比：不要只记“BFS 最短路”

| 问题目标 | DFS 的直觉 | BFS 的直觉 | 更推荐 |
| :--- | :--- | :--- | :--- |
| 数一共有几座岛 | 找到一座就深入搜完 | 也能一层层搜完 | DFS，代码更直接 |
| 从起点能否到终点 | 找到一条路即可 | 也能判断 | 两者都可 |
| 起点到终点最少走几步 | 可能先走到很长的路 | 按步数逐层探索 | BFS |
| 腐烂从多个位置同时传播多久 | 不自然模拟“同时” | 所有腐烂橘子同层扩散 | 多源 BFS |
| 找所有不同的可行路径 | 维护一条当前路径很自然 | 队列会保存大量路径 | DFS |

先问自己：**我关心的是“能走遍哪里”，还是“最少多久到达”？** 前者优先 DFS，后者优先 BFS。

---

## 第三部分：标准化解法模板

### 1. 先记住 BFS 的四个固定结构

```text
queue：保存下一批要处理的状态，先进先出
visited：一个状态只入队一次，防止重复扩散
directions / neighbors：从当前位置下一步可以去哪里
distance / level：当前状态离起点多少步；只在题目问步数时需要
```

最重要的规则：**发现一个未访问状态时，立刻标记并入队。** 不要等到出队才标记，否则它可能被多个位置重复加入队列。

### 2. 图的 BFS 遍历：从城市 A 出发

先看一个真实的图。节点表示城市，边表示两座城市之间有道路：

```text
        B ----- D
       /         \
      A ----- C --- E
```

用邻接表表示为：

```python
roads = {
    "A": ["B", "C"],
    "B": ["A", "D"],
    "C": ["A", "D", "E"],
    "D": ["B", "C", "E"],
    "E": ["C", "D"],
}
```

从城市 `A` 开始，BFS 的访问顺序是一层一层向外扩散：

```text
第 0 层：A
第 1 层：B、C
第 2 层：D、E
```

```python
from collections import deque


def visit_cities_from_a():
    roads = {
        "A": ["B", "C"],
        "B": ["A", "D"],
        "C": ["A", "D", "E"],
        "D": ["B", "C", "E"],
        "E": ["C", "D"],
    }

    # 步骤 1：从城市 A 开始；A 已经入队，因此立刻标记为已访问。
    queue = deque(["A"])
    visited = {"A"}

    # 步骤 2：依次处理队列中的城市。
    while queue:
        # 步骤 3：取出离 A 最近、且最早发现的城市。
        city = queue.popleft()
        print(city)

        # 步骤 4：查看从当前城市可以直接到达的所有城市。
        for next_city in roads[city]:
            if next_city in visited:
                continue

            # 步骤 5：新城市标记后入队，等待下一层访问。
            visited.add(next_city)
            queue.append(next_city)
```

执行 `visit_cities_from_a()` 会依次输出 `A、B、C、D、E`。这里的 `roads`、`city` 和 `next_city` 都可以替换成具体题目中的节点和邻居；保留下来的核心结构仍然是：**队列 + 访问记录 + 遍历邻居**。

通常在“入队时”标记访问，而不是等到出队时再标记。这样可以避免同一个节点被多个前驱重复加入队列。

### 3. 图的最短距离模板

```python
from collections import deque


def shortest_distance(start, target, graph):
    # 步骤 1：队列同时保存状态和距离
    queue = deque([(start, 0)])
    visited = {start}

    while queue:
        # 步骤 2：取出当前状态及其距离
        node, distance = queue.popleft()

        # 步骤 3：达到目标时返回当前距离
        if node == target:
            return distance

        # 步骤 4：将未访问邻居加入下一层
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))

    # 步骤 5：所有状态处理完成后仍未找到目标
    return -1
```

### 4. 网格 BFS 万能骨架

```python
from collections import deque


def grid_bfs(grid, start):
    # 步骤 1：初始化边界、队列、访问记录和方向数组
    rows, cols = len(grid), len(grid[0])
    queue = deque([start])
    visited = {start}
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    while queue:
        # 步骤 2：取出队首状态
        row, col = queue.popleft()

        # 步骤 3：枚举相邻状态
        for dr, dc in directions:
            next_row = row + dr
            next_col = col + dc

            # 步骤 4：检查状态是否合法
            if not (0 <= next_row < rows and 0 <= next_col < cols):
                continue

            # 跳过已访问状态
            if (next_row, next_col) in visited:
                continue

            # 步骤 5：标记新状态并入队
            visited.add((next_row, next_col))
            queue.append((next_row, next_col))
```

网格 BFS 的固定顺序是：出队当前格子 → 枚举 `directions` → 检查边界和可访问性 → `visited.add` → 入队。和 DFS 的区别只有容器：DFS 深入调用或压栈，BFS 将下一层状态加入队尾。

### 5. 按层遍历：什么时候使用 `level_size`

```python
from collections import deque


def bfs_by_level(start, graph):
    # 步骤 1：初始化第 0 层
    queue = deque([start])
    visited = {start}
    distance = 0

    while queue:
        # 步骤 2：记录当前层的状态数量
        level_size = len(queue)

        # 步骤 3：处理当前层的全部状态
        for _ in range(level_size):
            node = queue.popleft()

            # 步骤 4：将新状态加入下一层
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # 步骤 5：更新层数或距离
        distance += 1
```

### 6. 多源 BFS 模板

```python
from collections import deque


def multi_source_bfs(starts, rows, cols):
    # 步骤 1：初始化队列、距离记录和方向数组
    queue = deque()
    distance = [[-1] * cols for _ in range(rows)]
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    # 步骤 2：将全部起点初始化为第 0 层
    for row, col in starts:
        queue.append((row, col))
        distance[row][col] = 0

    while queue:
        # 步骤 3：取出队首状态
        row, col = queue.popleft()

        # 步骤 4：枚举相邻状态
        for dr, dc in directions:
            next_row = row + dr
            next_col = col + dc

            # 跳过非法状态
            if not (0 <= next_row < rows and 0 <= next_col < cols):
                continue

            # 跳过已访问状态
            if distance[next_row][next_col] != -1:
                continue

            # 步骤 5：记录新状态信息并入队
            distance[next_row][next_col] = distance[row][col] + 1
            queue.append((next_row, next_col))

    # 步骤 6：返回搜索结果
    return distance
```

多源 BFS 的关键是：先把所有起点一起入队，并统一设置为距离 `0`。

### 7. BFS 的复杂度

对于有 `V` 个节点、`E` 条边的图：

- 时间复杂度：$O(V + E)$；
- 空间复杂度：$O(V)$，包括访问集合和队列。

对于 `R × C` 的网格：

- 时间复杂度：$O(RC)$；
- 空间复杂度：$O(RC)$。

### 8. BFS 的边界条件与陷阱

- 使用 `list.pop(0)` 模拟队列会导致 $O(n)$ 的出队开销，应使用 `collections.deque`；
- 忘记记录访问状态，导致同一个状态被反复入队；
- 出队时才标记访问，可能产生大量重复状态；
- 层数增加的位置错误，导致步数计算偏一；
- 多源 BFS 没有同时把所有起点放入第 0 层；
- 题目边的代价不相同时，普通 BFS 不一定能求最短路，应根据边权考虑 0-1 BFS、Dijkstra 等方法。

---

## 第四部分：BFS 精选题目与学习路径

### 核心母题

1. **[LeetCode #994 腐烂的橘子](https://leetcode.cn/problems/rotting-oranges/)**

   - **为什么选此题**：多源 BFS 的经典题，所有腐烂橘子同时作为第 0 层起点。
   - **核心思路**：每轮处理当前所有腐烂橘子，将相邻的新鲜橘子变为腐烂，并统计轮数。
   - **复杂度**：时间 $O(RC)$，空间 $O(RC)$。

2. **[LeetCode #127 单词接龙](https://leetcode.cn/problems/word-ladder/)**

   - **为什么选此题**：把每个单词看成图节点，把一次合法替换看成边，练习状态图上的 BFS。
   - **核心思路**：从 `beginWord` 开始逐层尝试，只要第一次到达 `endWord`，就是最少转换次数。

### 变式进阶

1. **[LeetCode #542 01 矩阵](https://leetcode.cn/problems/01-matrix/)**：将所有 `0` 同时入队，求每个 `1` 到最近 `0` 的距离。

2. **[LeetCode #752 打开转盘锁](https://leetcode.cn/problems/open-the-lock/)**：虽然不在 Hot 100 中，但它是理解“状态图 + 最少操作次数”的经典 BFS 题。

3. **[LeetCode #1091 二进制矩阵中的最短路径](https://leetcode.cn/problems/shortest-path-in-binary-matrix/)**：练习网格最短路径、八个方向移动和距离计算。

### 学习顺序建议

```text
队列基础操作
    ↓
无权图 BFS
    ↓
网格最短路径
    ↓
多源 BFS
    ↓
状态转换与最短操作次数
```

DFS 与 BFS 最终都要落到同一个问题上：把题目中的对象抽象成“状态”和“状态之间的连接”。DFS 更关注沿一条路深入和连通区域，BFS 更关注按距离逐层扩散和最短步数。
