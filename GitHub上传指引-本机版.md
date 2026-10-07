# 上传 GitHub · 本机操作指引

> 这台电脑上操作。项目位置：`C:\Users\lyx\Desktop\campus_second_hand`
> 待上传：**81 个文件 / 6.73 MB**（已核对，venv 和本机脚本都排除了）

---

## 先选路线

| 路线 | 要不要装软件 | 以后更新方便吗 | 适合 |
|---|---|---|---|
| **A. 网页上传** | ❌ 不用装 | ⚠️ 每次都要手动拖 | 现在只想快点搞定 |
| **B. 装 Git 后用命令行** | 装 Git（约 60MB） | ✅ 三条命令搞定 | **推荐，一次装好长期省事** |

**我的建议是 B。** 你这台电脑没有 Git，装一次以后改代码就能直接推，不用再来回折腾。

---

# 路线 B：装 Git + 命令行上传（推荐）

## 第 1 步：下载安装 Git

浏览器打开（国内加速链接）：

```
https://ghproxy.net/https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe
```

如果这个链接失效，用官网：<https://git-scm.com/download/win>

**安装时一路点「下一步」就行**，不用改任何选项。

装完后**关掉所有已打开的命令行窗口**（PATH 需要重开才生效），然后验证：

```bash
git --version
```

能看到版本号就成功了。

## 第 2 步：删掉 GitHub 上的旧仓库

1. 打开 <https://github.com/2969479695/campus_second_hand>
2. **Settings** → 拉到最底 **Danger Zone**
3. **Delete this repository** → 按提示输入仓库名确认

> 因为旧仓库里有 7000 多个文件（venv 全传上去了），重建比清理更省事。

## 第 3 步：生成访问令牌（Token）

GitHub 现在**不能用账号密码推送**，必须用 Token。

1. 打开 <https://github.com/settings/tokens>
2. **Generate new token** → **Generate new token (classic)**
3. **Note** 填 `upload`
4. **Expiration** 选 `90 days`
5. **勾选 `repo`**（第一个大项，勾上会自动全选子项）
6. 拉到底 → **Generate token**
7. **复制那串 token 存到记事本**（只显示一次，关掉页面就看不到了）

## 第 4 步：初始化并上传

**在项目文件夹里打开命令行**：打开 `C:\Users\lyx\Desktop\campus_second_hand`，
在地址栏输入 `cmd` 回车（或按 `Shift + 右键` → 「在此处打开 PowerShell 窗口」）。

依次执行：

```bash
git init
git branch -M main
git add .
```

**⚠️ 这里先停一下，执行下面这条，仔细看输出：**

```bash
git status
```

**应该看到 `new file:` 开头的文件，大约 81 个**，其中包括：

```
new file:   .gitignore
new file:   LICENSE
new file:   README.md
new file:   db.sqlite3
new file:   manage.py
new file:   requirements.txt
new file:   启动.bat
new file:   campus_second_hand/settings.py
new file:   core/models.py
new file:   core/views.py
new file:   docs/images/01-系统架构图.png
... 等
```

**不该看到**：任何 `venv/`、`__pycache__/`、`.pyc`、`安装环境.bat`

确认无误后继续：

```bash
git commit -m "校园二手交易平台：Django 实现与项目文档"
git remote add origin https://github.com/2969479695/campus_second_hand.git
git push -u origin main
```

**推送时会弹窗要求登录：**

- **用户名**：`2969479695`
- **密码**：**粘贴第 3 步生成的 token**（不是你的 GitHub 登录密码）

## 第 5 步：验证

浏览器打开 <https://github.com/2969479695/campus_second_hand>，检查：

- [ ] README 首页能打开，**架构图、ER 图、截图都能正常显示**
- [ ] 文件列表里**没有** `venv`、没有 `__pycache__`、没有 `安装环境.bat`
- [ ] 仓库大小显示 **7 MB 左右**（不是几百 MB）

---

# 路线 A：网页上传（不装任何软件）

**合适的情况**：你现在只想快点传上去，不想装东西。

## 第 1 步：删旧仓库并新建空的

1. 删掉旧仓库（同路线 B 第 2 步）
2. 打开 <https://github.com/new>
3. **Repository name** 填 `campus_second_hand`
4. **Description** 填 `基于 Django 的校园二手交易平台（本科毕业设计）`
5. 选 **Public**
6. **不要勾** Add a README / .gitignore / license（你本地都有）
7. **Create repository**

## 第 2 步：上传文件

1. 在新仓库页面点 **uploading an existing file**（或 **Add file → Upload files**）
2. 打开文件资源管理器，进入 `C:\Users\lyx\Desktop\campus_second_hand`
3. **全选里面的内容**（Ctrl+A），**拖进浏览器上传区**

> ⚠️ 注意：拖**文件夹里面的内容**，不要把 `campus_second_hand` 这个文件夹本身拖进去，
> 否则会出现 `campus_second_hand/campus_second_hand/` 这样的套娃。

4. **在拖之前先手动排除**这几个（网页上传不受 .gitignore 控制）：
   - `venv` 文件夹
   - `安装环境.bat`
   - `.vscode` 文件夹

5. 页面底部 **Commit message** 填 `校园二手交易平台：Django 实现与项目文档`
6. 点 **Commit changes**

## 第 3 步：验证

同路线 B 第 5 步。

---

# 上传后马上做的两件事

## 1. 自己 clone 一次验证能跑

```bash
cd %USERPROFILE%\Desktop
git clone https://github.com/2969479695/campus_second_hand.git test_clone
cd test_clone
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

能打开 <http://127.0.0.1:8000/> 就说明 README 写的步骤是对的——
**面试官如果动手试，也是这么试的。**

## 2. 把链接加进简历

在毕业设计那条加一句：

> 代码已开源：github.com/2969479695/campus_second_hand

改完告诉我，我重新导出两份 PDF。

---

# 以后怎么更新代码

**路线 B（装了 Git）**：

```bash
git add .
git commit -m "这次改了什么"
git push
```

**路线 A（网页）**：进仓库 → 找到要改的文件 → 点铅笔图标编辑 → 提交。
或者重新走一次上传流程（会覆盖同名文件）。

---

# 常见问题

**Q：`git add .` 之后看到 venv 怎么办？**
说明 `.gitignore` 没生效。执行 `git rm -r --cached venv` 把它移出暂存区，
再确认 `git status` 里没有 venv 了。

**Q：`git push` 报 `Authentication failed`？**
八成是把 GitHub 登录密码当 token 用了。必须用第 3 步生成的 token。

**Q：`git push` 卡住不动 / 超时？**
开 VPN 再试；或者改用路线 A 的网页上传。

**Q：中文文件名（`启动.bat`、截图）会不会有问题？**
不会。Git 默认支持 UTF-8 中文文件名，GitHub 网页也能正常显示。

**Q：`db.sqlite3` 该不该上传？**
该。里面有演示数据，别人 clone 下来不用建数据就能看到效果。
这是课程项目的常见做法。
