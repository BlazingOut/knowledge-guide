# 第六课：使用 Git worktree 管理多个工作目录

前面几课中，我们通过 `git switch` 在同一个目录里切换不同分支。本课学习另一种方式：让同一个 Git 仓库同时拥有多个工作目录，每个目录检出不同的分支。这个功能叫 `git worktree`。

## 1. 为什么需要多个工作目录

使用普通分支切换时，目录和分支是一对一的：

```text
一个目录
   ↓ git switch
一次只能检出一个分支
```

假设你正在 `feature/login` 分支中修改代码，突然需要查看 `main` 的状态。使用普通方式，你需要先保存或 stash 当前修改，再切换分支，查看完后再切回来。

如果使用 worktree，可以同时拥有：

```text
同一个 Git 仓库
├── 主目录          → main
└── 另一个工作目录  → feature/login
```

两个目录都可以独立编辑、运行和提交，不需要反复切换同一个目录。

## 2. worktree 和普通复制目录的区别

直接复制项目目录会复制很多内容，也可能复制 `.git`，并让 Git 误以为它们是不同仓库。worktree 不是普通复制：

- 多个目录属于同一个 Git 仓库；
- 它们共享提交历史和 Git 对象；
- 每个目录有自己的工作区；
- 每个目录可以有自己的当前分支和 HEAD；
- 一个分支通常不能同时被两个 worktree 检出。

可以把它想象成：

```text
共享的 Git 历史和对象
        │
   ┌────┴────┐
主工作树          附加工作树
main              feature/login
```

主工作树和附加工作树共享提交对象，但工作区文件彼此独立。

## 3. 查看当前 worktree

在课程实验仓库中运行：

```bash
cd /Users/yyma/workspace/agents/lifestyle-manager-study/code/git/git-state-lab
git worktree list
```

如果只有一个工作目录，可能看到：

```text
/.../code/git/git-state-lab  8f31a20 [main]
```

每一部分表示：

- 工作目录的路径；
- 当前检出的提交的短 ID；
- 方括号中的当前分支。

## 4. 创建附加 worktree

### 4.1 为已有分支创建 worktree

第二课创建过 `feature/hello` 后，可以执行：

```bash
git worktree add ../git-state-feature feature/hello
```

这条命令表示：使用已经存在的 feature/hello 分支，创建一个新的附加工作目录；这个目录的路径是 ../git-state-feature。

创建后查看：

```bash
git worktree list
```

可能看到：

```text
/.../git-state-lab       abc1234 [main]
/.../git-state-feature   def5678 [feature/hello]
```

现在：

- 原目录仍然检出 `main`；
- 新目录检出 `feature/hello`；
- 两个目录共享同一套提交历史；
- 两个目录的工作文件可以不同。

### 4.2 创建新分支并创建 worktree

如果分支还不存在，可以使用：

```bash
git worktree add -b feature/worktree ../git-state-worktree main
```

这条命令表示：

1. 以 `main` 当前的提交作为起点；
2. 创建名为 `feature/worktree` 的新分支；
3. 在 `../git-state-worktree` 创建附加工作目录；
4. 在新目录检出这个新分支。

注意参数顺序：

```text
git worktree add -b <新分支名> <新目录> <起点分支或提交>
```

如果省略最后的起点，Git 会使用当前分支作为起点。

## 5. 附加 worktree 中的基本操作

进入附加目录：

```bash
cd ../git-state-feature
git status
git branch --show-current
git log --oneline --decorate -3
```

你会发现它和普通目录一样，可以执行：

- 编辑文件；
- `git status`；
- `git add`；
- `git commit`；
- 查看日志；
- 运行项目。

在附加目录修改并提交：

```bash
printf '来自附加工作目录\n' >> note.txt
git add note.txt
git commit -m "Update from feature worktree"
```

然后回到主目录：

```bash
cd ../git-state-lab
git log --oneline --decorate --graph --all
```

主目录会看到同一个新提交，因为两个 worktree 共享仓库历史。主目录的工作区文件不会自动变成附加目录的文件内容；要在主目录看到变化，需要切换或合并对应分支。

## 6. 为什么同一个分支不能同时检出

如果 `feature/hello` 已经在一个 worktree 中，执行：

```bash
git worktree add ../another-feature feature/hello
```

Git 通常会拒绝，<mark>因为同一分支同时出现在两个目录中会造成歧义</mark>：两个目录都可能提交新内容，但分支名称只能有一个明确的最新位置。

如果确实想在两个目录使用相同提交，可以使用 detached HEAD，但这属于后续内容，不在本课展开。

## 7. 原目录能不能切换到附加 worktree 使用的分支？

假设当前状态是：

```text
同一个 Git 仓库
├── git-state-lab/       → main
└── git-state-feature/   → feature/hello
```

此时在原目录执行：

```bash
cd ../git-state-lab
git switch feature/hello
```

Git 通常会拒绝，因为 `feature/hello` 已经被 `git-state-feature/` 这个 worktree 检出。原目录不会自动切换，附加目录也不会自动变化。每个 worktree 都有自己的当前分支。

Git 默认维护这个约束：

```text
一个分支 → 一个当前检出的 worktree
```

如果确实想让原目录改用 `feature/hello`，通常要先让附加目录切换到其他分支，或者先移除附加 worktree。例如：

```bash
cd ../git-state-feature
git switch main
```

之后原目录才可能切换到 `feature/hello`。切换前仍然要确认两个目录的工作区没有需要保留的未提交修改。

### 分支是否被“剥离”了？

使用 `git worktree add` 后，指定的分支会在新目录中成为当前检出的分支，而原目录继续使用原来的分支，于是得到两个独立的工作区：

```text
原工作区：git-state-lab/
当前分支：main

附加工作区：git-state-feature/
当前分支：feature/hello
```

但更准确的说法不是“分支从原工作区中复制或剥离出来”，而是：

> 分支始终属于整个 Git 仓库；`git worktree add` 只是新增一个工作目录，并让这个目录检出指定分支。

因此：

- `main` 和 `feature/hello` 仍然是同一个仓库中的两个分支名称；
- 两个 worktree 共享提交历史和 Git 对象；
- 每个 worktree 拥有自己的工作区文件和当前检出位置；
- 原目录可以通过 `git log --all` 看到附加目录产生的提交；
- 但原目录的文件不会自动变成 `feature/hello` 的内容，因为它仍然检出 `main`。

可以记成：

```text
分支：属于仓库，负责指向提交
worktree：属于目录，负责提供一份可编辑的工作区
```

## 8. 删除附加 worktree

完成工作后，回到主工作树或其他目录，执行：

```bash
git worktree remove ../git-state-feature
git worktree list
```

`git worktree remove` 会移除附加工作目录，并清理 Git 对它的登记。执行前确认目录中的未提交修改已经保存或不再需要。

不要直接使用文件管理器删除目录作为常规操作。若目录已经被手动删除，可以运行：

```bash
git worktree prune
```

`prune` 会清理 Git 中已经不存在的 worktree 登记信息。

## 9. 完整实验

开始前确认主目录状态：

```bash
cd /Users/yyma/workspace/agents/lifestyle-manager-study/code/git/git-state-lab
git status
git branch
git worktree list
```

创建新的分支和附加 worktree：

```bash
git worktree add -b feature/worktree ../git-state-worktree main
git worktree list
```

在新目录中修改并提交：

```bash
cd ../git-state-worktree
printf 'worktree 实验\n' >> note.txt
git add note.txt
git commit -m "Add worktree experiment note"
git status
```

回到主目录查看共享历史：

```bash
cd ../git-state-lab
git log --oneline --decorate --graph --all
git worktree list
```

最后清理附加 worktree：

```bash
git worktree remove ../git-state-worktree
git branch -d feature/worktree
git worktree list
```

如果分支的提交尚未合并，`git branch -d` 可能拒绝删除。此时先保留分支，不要使用强制删除。

## 10. 本课小结

```text
git worktree list
    查看所有工作树

git worktree add <目录> <分支>
    为已有分支创建附加工作树

git worktree add -b <分支> <目录> <起点>
    创建分支并创建附加工作树

git worktree remove <目录>
    移除附加工作树

git worktree prune
    清理已经不存在的工作树登记
```

## 11. 课后练习

1. 创建一个 `feature/isolated` 分支，并为它建立附加 worktree。
2. 在两个 worktree 中分别运行 `git status` 和 `git branch --show-current`，比较结果。
3. 在附加 worktree 中提交修改，在主目录查看 `git log`。
4. 尝试为已经被检出的分支创建第二个 worktree，观察 Git 的错误信息。
5. 解释 worktree 和复制整个项目目录的区别。
6. 清理附加 worktree 后，再运行 `git worktree list` 确认结果。

完成本课后，继续学习第七课综合实践。
