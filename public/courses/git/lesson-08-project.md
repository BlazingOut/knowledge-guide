# 第 8 课：综合实践：审查、隔离并合并一次功能修改

本课把前面知识串起来。目标不是完成复杂功能，而是练习一个安全的 Git 工作流。

## 任务

在 `code/git/git-state-lab` 中模拟一次小功能：为 `note.txt` 增加一段关于 Python 学习的说明。要求使用 feature 分支或独立 worktree 完成，主分支保持可运行、可解释。

## 推荐流程

1. 用 `git status` 确认起点干净，并用 `git log --oneline --decorate --graph` 记录起点。
2. 创建 `feature/python-note` 分支，或使用 `git worktree add` 创建独立目录。
3. 修改文件，先查看 `git diff`，确认只包含目标变化。
4. 暂存目标文件，查看 `git diff --staged` 和 `git diff --check`。
5. 提交一个意图清晰的 commit。
6. 查看 `git show --stat --oneline HEAD` 和完整 diff。
7. 回到 main，合并 feature；如果冲突，按第 5 课的流程解决。
8. 最后再次检查 `git status`、提交历史和文件内容。

## 验收问题

- 工作区、暂存区、HEAD 和远程分支现在分别是什么状态？
- 你能指出本次提交到底改了哪些行吗？
- 如果误改了文件但还没有暂存，如何恢复？如果已经提交但不能重写共享历史，应该使用什么？
- worktree 与普通分支切换相比解决了什么问题？
- 你能否在不看命令历史的情况下重新完成整个流程？

完成后，把你的 `git status`、`git log --oneline --decorate --graph --all` 和一次 staged diff 发给我，我会根据输出检查你的理解。
