---
name: frontend-qa
description: Use when frontend, UI, CSS, layout, interaction, route, form, canvas, chart, 3D, media, or user-visible changes need real browser, screenshot, responsive, state, or visual verification.
---

# frontend-qa

## 目标

在前端、UI、样式、布局、交互、媒体、Canvas、3D、图表或用户可见流程发生变化后，用真实运行环境做针对性 QA，尽早发现空白页、资源错误、运行时错误、布局错位、文字截断、响应式破坏、交互失败和视觉状态缺失。

这个 skill 的目标不是替代完整人工验收，而是让 Codex 对用户实际看到和操作到的界面负责。

## 触发场景

在以下情况触发：

- 修改页面、组件、样式、设计系统、路由、表单、弹窗、菜单、导航、图表、Canvas、3D、媒体资源。
- 修改会影响用户可见行为或交互。
- 用户要求 UI、UX、视觉、响应式、移动端、截图、浏览器验证。
- 修复前端 bug 后需要确认实际页面表现。
- 测试或构建无法覆盖视觉风险。

不要为纯后端、纯文档、纯脚本、纯配置且不影响前端展示的改动触发。

## QA 分级

先按风险选择验证深度。

### Level 1：轻量 UI QA

适用于小范围文案、样式、单组件低风险改动。

- 打开受影响页面或组件。
- 检查页面渲染、console 错误、明显布局问题。
- 至少验证一个桌面视口。
- 如果改动可能影响响应式，也验证一个移动视口。

### Level 2：标准 UI QA

适用于页面、表单、交互、路由、状态展示、响应式布局改动。

- 验证桌面和移动端。
- 检查 loading、empty、error、success、disabled、long content 等关键状态。
- 检查主要交互路径。
- 检查 console/runtime 错误和资源加载。
- 发现问题后修复并复测。

### Level 3：高风险视觉 QA

适用于设计系统、核心页面、支付/认证/权限流程、复杂表单、图表、Canvas、3D、游戏、动画、媒体密集页面。

- 使用真实浏览器或项目 E2E/Storybook/preview 工具。
- 验证桌面、移动端和至少一个边界尺寸。
- 检查关键状态和错误路径。
- 对 Canvas/3D/图表/游戏，确认画面非空、主体在视口内、资源加载成功、交互/动画实际工作。
- 如可行，保留截图或明确说明观察结果。

## 工作原则

- 优先使用项目已有 dev server、preview、Storybook、Playwright、Cypress、Vitest browser、组件测试或 E2E 工具。
- 本地 `localhost`、`127.0.0.1`、`::1`、`file://` 或 Codex 内嵌页面验证，优先使用 Browser 插件的 in-app Browser。
- 不要静默降级到 Chrome。Chrome 只在用户明确要求 Chrome/`@chrome`，或任务必须使用用户现有 Chrome 登录态、cookie、扩展、已打开 tab 时使用。
- 如果 in-app Browser 不可用，先说明原因；除非用户批准使用外部 Chrome，否则用项目测试、API/DOM 契约、截图产物或代码审查作为次优证据。
- 不要硬编码 Browser 插件缓存路径、用户目录或版本号。使用当前会话提供的 Browser skill/plugin 路径；需要手动定位时，在 `~/.codex/plugins/cache/openai-bundled/browser/` 下发现当前存在的版本，再导入该版本的 `scripts/browser-client.mjs`。
- 打开实际受影响页面，不只打开首页。
- 用真实渲染结果验证，不只凭代码判断。
- 同时考虑桌面和移动端，除非项目明确不支持移动端。
- 遵循现有设计系统、组件库、间距、颜色、字体、动效和交互约定。
- 不为了视觉效果引入无关大改。
- 如果无法进行浏览器验证，说明原因，并用测试、构建和代码审查作为次优验证。

## QA 步骤

1. 确认前端入口
   - 阅读 `AGENTS.md`、`docs/commands.md`、`docs/testing.md`。
   - 找到 dev server、preview、Storybook、E2E 或组件测试命令。
   - 确认受影响页面、路由、组件和关键状态。

2. 启动或访问目标页面
   - 使用项目推荐命令启动服务。
   - 如果已有服务可用，优先复用。
   - 如果端口冲突，选择可用端口并说明。
   - 不要只打开首页；必须访问实际受影响页面或组件。

3. 桌面验证
   - 页面不是空白。
   - 没有明显 console/runtime 错误。
   - 主要资源加载成功。
   - 布局、间距、滚动、层级、焦点状态合理。
   - 文本没有不合理溢出、截断、遮挡。
   - 关键交互可以完成。

4. 移动端验证
   - 使用合理移动视口。
   - 检查导航、折行、按钮尺寸、输入框、弹窗、滚动、遮挡。
   - 检查是否出现非预期横向滚动。
   - 检查长文本、极端内容和窄屏布局。

5. 状态验证
   - Loading
   - Empty
   - Error
   - Success
   - Disabled
   - Long content
   - Auth / permission state
   - Network failure state
   - Form validation state

6. 可访问性基础检查
   - Keyboard：主要按钮、链接、输入框、菜单、弹窗和表单路径可用键盘到达和操作。
   - Focus：焦点顺序合理，焦点样式可见，弹窗/菜单不会吞掉或丢失焦点。
   - Contrast：正文、按钮、状态提示、禁用态和错误态没有明显低对比度问题。
   - ARIA：图标按钮、dialog、menu、tab、combobox、alert、error message 等语义不缺关键 label / role / state。
   - Reduced motion：动画、Canvas、3D、游戏或滚动效果应尊重 reduced motion；不能依赖动效传达唯一信息。
   - 表单错误可见，且和对应输入有关联。
   - 交互元素尺寸合理，触控目标不会过小。

7. Canvas / 3D / 图表 / 游戏专项检查
   - 确认画面非空。
   - 确认主体对象在视口内且没有被 UI 遮挡。
   - 确认资源、纹理、字体、图片加载成功。
   - 确认动画或交互实际发生。
   - 检查桌面和移动端 framing。
   - 如可行，使用截图或像素检查辅助判断非空渲染。

8. 修复和复测
   - 如果发现问题，先定位根因。
   - 做最小安全修复。
   - 复测同一页面、同一视口、同一状态。
   - 不要只修桌面而忽略移动端。
   - 不要只修 happy path 而忽略错误/空状态。

## 视觉检查清单

- 页面不是空白。
- 无明显 console/runtime 错误。
- 资源加载成功。
- 文本没有溢出、截断或遮挡。
- 元素没有不合理重叠。
- 按钮、输入框、菜单、弹窗可用。
- 响应式布局没有非预期横向滚动。
- loading、empty、error、success 状态合理。
- 交互后状态可见且一致。
- 颜色、字体、间距符合现有系统。
- Canvas/3D/图表不是空画布，主体可见。

## 验证输出

最终回复中说明：

- 验证的页面、路由或组件。
- 使用的命令。
- 使用的视口或设备尺寸。
- 检查过的关键状态。
- 发现并修复的问题。
- 未能验证的内容和原因。
- 残余风险。

## Output Shape

完成 frontend-qa 后，输出保持短但要有证据：

- Target：实际打开的页面、路由、组件或 story。
- Environment：dev server / preview / Storybook / test runner、浏览器工具和视口。
- States：检查过的 loading、empty、error、success、disabled、long content、auth 或 network failure。
- Accessibility：keyboard、focus、contrast、ARIA、reduced motion 的检查结果。
- Findings：发现并修复的问题；没有问题也说明观察证据。
- Gaps：无法浏览器验证、无法截图或未覆盖状态的原因。

## 不要做

- 不要只说“代码看起来没问题”。
- 不要只运行 build 就声称 UI 没问题。
- 不要只打开首页而忽略实际改动页面。
- 不要只验证桌面端。
- 不要忽略 console/runtime 错误。
- 不要忽略 loading、empty、error、long content 等状态。
- 不要为了视觉效果引入无关重构。
- 不要在没有运行证据时声称视觉验证通过。
