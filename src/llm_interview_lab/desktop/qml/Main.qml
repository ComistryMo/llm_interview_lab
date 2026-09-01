import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import "components"
import "pages"

ApplicationWindow {
    id: window
    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 620
    visible: true
    title: "LLM Interview Lab"
    Material.theme: dark ? Material.Dark : Material.Light
    Material.accent: appTheme.accent

    // Material.System is a style selection, not a resolved color scheme.  Use
    // the platform hint as well so custom surfaces follow the system theme
    // instead of silently remaining light on a dark desktop.
    property bool dark: backend.theme === "dark"
                        || (backend.theme === "system"
                            && Qt.application.styleHints
                            && Qt.application.styleHints.colorScheme === Qt.ColorScheme.Dark)
    // Synthetic evidence can override typography and motion without touching
    // Controller settings, Profile data or events.
    property real displayFontScaleOverride: 0.0
    property real displayMotionScaleOverride: -1.0
    readonly property real effectiveFontScale: displayFontScaleOverride > 0
                                               ? displayFontScaleOverride
                                               : backend.fontScale
    readonly property real effectiveMotionScale: displayMotionScaleOverride >= 0
                                                 ? displayMotionScaleOverride : 1.0
    AppTheme {
        id: appTheme
        darkMode: window.dark
        fontScale: window.effectiveFontScale
        motionScale: window.effectiveMotionScale
        uiFontFamily: window.uiFontFamily
    }
    property var colors: appTheme.legacyPalette
    // Prefer the platform's bundled CJK UI face when it is available.  The
    // Keep an installed CJK face explicit on Linux/offscreen builds.  If it is
    // unavailable, Qt falls back to the platform default; the Python entry
    // point makes the same best-effort choice for raw Qt controls.
    property string uiFontFamily: Qt.platform.os === "windows" ? "Microsoft YaHei UI"
                                       : Qt.platform.os === "osx" ? "PingFang SC"
                                       : "Noto Sans SC"
    readonly property string layoutMode: width < 1040 ? "compact"
                                         : width < 1400 ? "standard" : "wide"
    readonly property bool compactShell: layoutMode !== "wide"
    readonly property int sidebarWidth: layoutMode === "wide" ? 224
                                        : layoutMode === "standard" ? 72 : 64
    property string paletteQuery: ""
    property var paletteActions: [
        {id: "home", label: "打开首页", hint: "继续训练或开始模拟面试"},
        {id: "learn", label: "打开刷题训练", hint: "按课程前置选择题目"},
        {id: "exercise", label: "打开答题工作区", hint: "继续当前题目或浏览可练题目"},
        {id: "interview", label: "打开模拟面试", hint: "开始或恢复结构化面试"},
        {id: "coach", label: "打开 AI 辅助（可选）", hint: "仅在需要时请求只读帮助；模拟面试请进入面试"},
        {id: "career", label: "打开求职材料", hint: "管理当前 Profile 的材料"},
        {id: "progress", label: "打开学习进度", hint: "查看当前 Profile 的进度"},
        {id: "connections", label: "打开 AI 连接", hint: "配置或测试普通 LLM"},
        {id: "settings", label: "打开设置", hint: "外观、本地目录与 Codex"},
        {id: "run-tests", label: "运行公开测试", hint: "保存当前编辑器并运行测试", exerciseOnly: true},
        {id: "about", label: "关于 LLM Interview Lab", hint: "查看版本和产品说明"},
        {id: "quit", label: "退出应用", hint: "安全关闭本地工作台"}
    ]
    // A Codex request is owned by the shell, not by an individual page.  The
    // map is intentionally kept here so navigation cannot hide a pending
    // safety decision.
    property var pendingCodexApproval: ({})
    property bool approvalActionInFlight: false

    function approvalFiles(value) {
        var files = value && value.files
        if (!files)
            return ""
        return typeof files.join === "function" ? files.join(", ") : String(files)
    }

    function showApprovalDetails() {
        if (pendingCodexApproval && pendingCodexApproval.request_id)
            approvalDialog.open()
    }

    function resolveApproval(decision) {
        if (approvalActionInFlight || !pendingCodexApproval
                || !pendingCodexApproval.request_id)
            return
        var requestId = String(pendingCodexApproval.request_id)
        approvalActionInFlight = true
        try {
            backend.resolveCodexApproval(requestId, decision)
        } catch (error) {
            approvalActionInFlight = false
            message.text = "审批未发送，请重试；请求仍保持待处理。"
            toastPopup.open()
        }
    }

    function paletteItems() {
        var query = paletteQuery.trim().toLowerCase()
        var result = []
        for (var i = 0; i < paletteActions.length; ++i) {
            var action = paletteActions[i]
            if (action.exerciseOnly
                    && (backend.currentPage !== "exercise" || backend.busy))
                continue
            var haystack = (action.label + " " + action.hint).toLowerCase()
            if (!query || haystack.indexOf(query) >= 0)
                result.push(action)
        }
        return result
    }

    function pageTitle(pageId) {
        var titles = {
            home: backend.uiText("nav.home"),
            learn: backend.uiText("nav.learn"),
            exercise: backend.uiText("page.exercise"),
            interview: backend.uiText("nav.interview"),
            progress: backend.uiText("nav.progress"),
            career: backend.uiText("nav.career"),
            coach: backend.uiText("nav.coach"),
            connections: backend.uiText("nav.connections"),
            settings: backend.uiText("nav.settings")
        }
        return titles[pageId] || "LLM Interview Lab"
    }

    function triggerPaletteAction(actionId) {
        if (actionId === "run-tests") {
            if (backend.currentPage === "exercise" && !backend.busy)
                backend.runTests()
            commandPalette.close()
            return
        }
        if (actionId === "about") {
            commandPalette.close()
            aboutDialog.open()
            return
        }
        if (actionId === "quit") {
            commandPalette.close()
            Qt.quit()
            return
        }
        backend.navigate(actionId)
        commandPalette.close()
    }
    font.pixelSize: appTheme.scaledPx(14)
    // An empty family lets Qt use the platform fallback chain.  Reading
    // Qt.application.font.family on minimal Linux/offscreen setups yields the
    // synthetic “Sans Serif” alias and triggers a needless font lookup.
    font.family: uiFontFamily
    color: appTheme.canvas

    menuBar: MenuBar {
        // Windows/Linux use the in-app command surface; macOS keeps the
        // platform-native application menu semantics.
        visible: Qt.platform.os === "osx"
        height: visible ? implicitHeight : 0
        Menu {
            title: "应用"
            Action { text: "关于 LLM Interview Lab"; onTriggered: aboutDialog.open() }
            MenuSeparator {}
            Action { text: "设置"; shortcut: StandardKey.Preferences; onTriggered: backend.navigate("settings") }
            Action { text: "退出"; shortcut: StandardKey.Quit; onTriggered: Qt.quit() }
        }
        Menu {
            title: "训练"
            Action { text: "继续训练"; onTriggered: backend.navigate("home") }
                    Action { text: "运行公开测试"; enabled: backend.currentPage === "exercise" && !backend.busy; onTriggered: backend.runTests() }
        }
    }

    Shortcut {
        sequence: StandardKey.Preferences
        enabled: !backend.onboardingRequired
        onActivated: backend.navigate("settings")
    }

    Shortcut {
        sequence: StandardKey.Quit
        onActivated: Qt.quit()
    }

    Shortcut {
        sequences: ["Ctrl+Return", "Meta+Return"]
        enabled: backend.currentPage === "exercise" && !backend.busy
        onActivated: backend.runTests()
    }

    // Keep the documented test shortcut available on both Windows/Linux and
    // macOS.  StandardKey.Refresh is platform-dependent and does not map to
    // Ctrl/Command+R in every Qt style, so declare the concrete sequences too.
    Shortcut {
        sequences: ["Ctrl+R", "Meta+R"]
        enabled: backend.currentPage === "exercise" && !backend.busy
        onActivated: backend.runTests()
    }

    // A deliberately small command palette keeps navigation discoverable for
    // keyboard users without introducing a second command/router layer.  All
    // entries map to existing backend actions; unavailable actions are simply
    // omitted from the list.
    Shortcut {
        sequences: ["Ctrl+K", "Meta+K"]
        enabled: !backend.onboardingRequired
        onActivated: {
            commandPalette.open()
            paletteSearch.forceActiveFocus()
            paletteSearch.selectAll()
        }
    }

    onClosing: backend.shutdown()

    RowLayout {
        anchors.fill: parent
        spacing: 0

        LabSurface {
            theme: appTheme
            level: "chrome"
            outlined: false
            padding: 0
            cornerRadius: 0
            Layout.preferredWidth: window.sidebarWidth
            Layout.fillHeight: true

            LabDivider {
                theme: appTheme
                orientation: Qt.Vertical
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: window.layoutMode === "wide" ? 16 : 10
                anchors.rightMargin: window.layoutMode === "wide" ? 16 : 10
                anchors.topMargin: 14
                anchors.bottomMargin: 12
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 12
                    Layout.alignment: window.layoutMode === "wide"
                                      ? Qt.AlignLeft : Qt.AlignHCenter
                    Image {
                        source: Qt.resolvedUrl("../resources/app-icon.png")
                        sourceSize.width: 34
                        sourceSize.height: 34
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        fillMode: Image.PreserveAspectFit
                        Accessible.name: "LLM Interview Lab"
                    }
                    ColumnLayout {
                        visible: window.layoutMode === "wide"
                        spacing: 0
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Text {
                            id: brandTitle
                            text: "LLM Interview Lab"
                            color: window.colors.text
                            font.weight: Font.DemiBold
                            font.pixelSize: appTheme.scaledPx(14)
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                            wrapMode: Text.NoWrap
                            Accessible.name: "LLM Interview Lab"
                            ToolTip.visible: brandHover.containsMouse
                            ToolTip.text: "LLM Interview Lab"
                            ToolTip.delay: 500
                            MouseArea {
                                id: brandHover
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                            }
                        }
                        Text {
                            text: "本地面试训练工作台"
                            color: window.colors.muted
                            font.pixelSize: appTheme.scaledPx(11)
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }
                    }
                }

                // Keep navigation grouped by the user's intent.  The shared
                // delegate preserves one click/keyboard behavior while the
                // small section labels make the shell easier to scan.
                Component {
                    id: navButtonDelegate
                    NavItem {
                        required property var modelData
                        theme: appTheme
                        compact: window.layoutMode !== "wide"
                        label: modelData.label
                        iconSource: Qt.resolvedUrl(modelData.icon)
                        selected: backend.currentPage === modelData.id
                        Layout.fillWidth: window.layoutMode === "wide"
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: window.layoutMode === "wide" ? -1 : 44
                        Layout.preferredHeight: window.layoutMode === "wide" ? 40 : 44
                        onClicked: backend.navigate(modelData.id)
                    }
                }

                LabText {
                    theme: appTheme
                    visible: window.layoutMode === "wide"
                    text: "主要"
                    variant: "caption"
                    tone: "muted"
                    strong: true
                    Layout.topMargin: 2
                }
                Repeater {
                    model: [
                        {id: "home", label: backend.uiText("nav.home"), icon: "../resources/icons/home.svg"},
                        {id: "learn", label: backend.uiText("nav.learn"), icon: "../resources/icons/book-open.svg"},
                        {id: "exercise", label: backend.uiText("page.exercise"), icon: "../resources/icons/code.svg"},
                        {id: "interview", label: backend.uiText("nav.interview"), icon: "../resources/icons/interview.svg"}
                    ]
                    delegate: navButtonDelegate
                }

                LabDivider {
                    theme: appTheme
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    Layout.bottomMargin: 4
                }
                LabText {
                    theme: appTheme
                    visible: window.layoutMode === "wide"
                    text: "复盘与辅助"
                    variant: "caption"
                    tone: "muted"
                    strong: true
                }
                Repeater {
                    model: [
                        {id: "progress", label: backend.uiText("nav.progress"), icon: "../resources/icons/chart.svg"},
                        {id: "career", label: backend.uiText("nav.career"), icon: "../resources/icons/briefcase.svg"},
                        {id: "coach", label: backend.uiText("nav.coach"), icon: "../resources/icons/messages.svg"}
                    ]
                    delegate: navButtonDelegate
                }

                LabDivider {
                    theme: appTheme
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    Layout.bottomMargin: 4
                }
                Repeater {
                    model: [
                        {id: "connections", label: backend.uiText("nav.connections"), icon: "../resources/icons/plug.svg"},
                        {id: "settings", label: backend.uiText("nav.settings"), icon: "../resources/icons/settings.svg"}
                    ]
                    delegate: navButtonDelegate
                }

                LabIconButton {
                    id: moreNavigationButton
                    objectName: "moreNavigationButton"
                    theme: appTheme
                    iconSource: Qt.resolvedUrl("../resources/icons/more.svg")
                    accessibleName: "更多导航和命令"
                    toolTip: "更多导航和命令 · Ctrl/⌘ K"
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: {
                        commandPalette.open()
                        paletteSearch.forceActiveFocus()
                        paletteSearch.selectAll()
                    }
                }

                Item { Layout.fillHeight: true }
                LabSurface {
                    objectName: "sidebarProfileSwitcher"
                    theme: appTheme
                    visible: window.layoutMode === "wide"
                    level: "sunken"
                    outlined: false
                    padding: 0
                    interactive: true
                    accessibleName: "切换学习档案"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 70
                    onActivated: backend.navigate("settings")
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 3
                        LabText { theme: appTheme; text: "学习档案"; variant: "caption"; tone: "muted"; strong: true }
                        LabText { theme: appTheme; text: backend.profileDisplayName || backend.profileId; strong: true; elide: Text.ElideRight; Layout.fillWidth: true }
                        LabText { theme: appTheme; text: "数据保存在本机"; variant: "caption"; tone: "muted"; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }
                LabIconButton {
                    visible: window.layoutMode !== "wide"
                    theme: appTheme
                    iconSource: Qt.resolvedUrl("../resources/icons/user.svg")
                    accessibleName: backend.profileDisplayName || backend.profileId || "学习档案"
                    toolTip: (backend.profileDisplayName || backend.profileId || "学习档案")
                             + " · 数据保存在本机"
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: backend.navigate("settings")
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            LabSurface {
                theme: appTheme
                level: "surface"
                outlined: false
                padding: 0
                cornerRadius: 0
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                LabDivider {
                    theme: appTheme
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: window.layoutMode === "compact" ? 14 : 20
                    anchors.rightMargin: window.layoutMode === "compact" ? 14 : 20
                    spacing: 10
                    LabText {
                        objectName: "shellRouteTitle"
                        theme: appTheme
                        text: window.pageTitle(backend.currentPage)
                        strong: true
                        elide: Text.ElideRight
                        Layout.maximumWidth: window.layoutMode === "compact" ? 156 : 190
                    }
                    LabButton {
                        visible: window.layoutMode !== "compact"
                        theme: appTheme
                        variant: "secondary"
                        compact: true
                        text: Qt.platform.os === "osx"
                              ? "搜索或执行命令  ⌘ K"
                              : "搜索或执行命令  Ctrl K"
                        iconSource: Qt.resolvedUrl("../resources/icons/search.svg")
                        toolTip: "打开 Command Palette"
                        onClicked: {
                            commandPalette.open()
                            paletteSearch.forceActiveFocus()
                            paletteSearch.selectAll()
                        }
                    }
                    LabIconButton {
                        visible: window.layoutMode === "compact"
                        theme: appTheme
                        highlighted: true
                        iconSource: Qt.resolvedUrl("../resources/icons/search.svg")
                        accessibleName: "搜索或执行命令"
                        toolTip: "搜索或执行命令 · Ctrl/⌘ K"
                        onClicked: {
                            commandPalette.open()
                            paletteSearch.forceActiveFocus()
                            paletteSearch.selectAll()
                        }
                    }
                    Item { Layout.fillWidth: true }
                    StatusPill {
                        theme: appTheme
                        compact: window.layoutMode === "compact"
                        text: backend.aiStatusVariant === "connected" ? "AI 已连接"
                              : backend.aiStatusVariant === "connecting" ? "AI 连接中"
                              : "No-AI 可用"
                        tone: backend.aiStatusVariant === "connected" ? appTheme.success
                              : backend.aiStatusVariant === "connecting" ? appTheme.warning
                              : appTheme.muted
                    }
                    LabBusyIndicator {
                        theme: appTheme
                        running: backend.busy
                        visible: running
                        implicitWidth: 24
                        implicitHeight: 24
                    }
                }
            }

            // Safety prompts stay visible while the user moves between pages.
            // In the normal state this item has zero layout cost; when a
            // request arrives it reserves space above page content instead of
            // covering a page CTA.
            LabSurface {
                id: codexApprovalBanner
                objectName: "codexApprovalBanner"
                theme: appTheme
                level: "raised"
                outlined: true
                padding: 0
                cornerRadius: 0
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 82 : 0
                Layout.minimumHeight: 0
                visible: !!(window.pendingCodexApproval
                            && window.pendingCodexApproval.request_id)
                z: 30
                border.color: window.colors.warning
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 22
                    anchors.rightMargin: 22
                    spacing: 14
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        LabText {
                            theme: appTheme
                            text: "Codex 请求等待审批"
                            tone: "warning"
                            strong: true
                            variant: "bodyLarge"
                        }
                        LabText {
                            theme: appTheme
                            Layout.fillWidth: true
                            text: (window.pendingCodexApproval
                                   && window.pendingCodexApproval.action || "操作")
                                  + " · " + (window.pendingCodexApproval
                                              && window.pendingCodexApproval.scope
                                              || "当前仓库")
                            elide: Text.ElideRight
                        }
                    }
                    LabButton {
                        objectName: "codexApprovalViewButton"
                        theme: appTheme
                        variant: "secondary"
                        text: "查看并审批"
                        enabled: !window.approvalActionInFlight
                        onClicked: window.showApprovalDetails()
                    }
                }
            }

            StackLayout {
                id: pages
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: ({home:0, career:1, learn:2, exercise:3, interview:4, coach:5, progress:6, connections:7, settings:8})[backend.currentPage] || 0
                HomePage {
                    app: backend
                    palette: window.colors
                    theme: appTheme
                    layoutMode: window.layoutMode
                }
                CareerPage { app: backend; palette: window.colors }
                LearnPage {
                    app: backend
                    palette: window.colors
                    theme: appTheme
                    layoutMode: window.layoutMode
                }
                ExercisePage { app: backend; palette: window.colors }
                InterviewPage { app: backend; palette: window.colors }
                CoachPage { app: backend; palette: window.colors; theme: appTheme }
                ProgressPage { app: backend; palette: window.colors }
                ConnectionsPage { app: backend; palette: window.colors }
                SettingsPage { app: backend; palette: window.colors }
            }
        }
    }

    OnboardingPage {
        anchors.fill: parent
        z: 20
        visible: backend.onboardingRequired
        app: backend
        palette: window.colors
        theme: appTheme
        layoutMode: window.layoutMode
    }

    Popup {
        id: commandPalette
        objectName: "commandPalette"
        // The first-run flow is intentionally focused and has no navigation
        // actions behind it.  Keep the popup closed if onboarding becomes
        // required again; `enabled` avoids binding Popup.visible to its
        // internal open/close state (which would otherwise show it at launch).
        enabled: !backend.onboardingRequired
        x: Math.max(24, Math.round((window.width - width) / 2))
        y: 76
        width: Math.min(560, window.width - 48)
        height: Math.min(410, window.height - 112)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        onOpened: {
            if (backend.onboardingRequired) {
                commandPalette.close()
                return
            }
            paletteList.currentIndex = paletteList.count > 0 ? 0 : -1
            paletteSearch.forceActiveFocus()
            paletteSearch.selectAll()
        }
        onClosed: {
            window.paletteQuery = ""
            paletteSearch.text = ""
        }
        background: LabSurface {
            theme: appTheme
            level: "raised"
            padding: 0
            cornerRadius: appTheme.radiusLarge
        }
        contentItem: ColumnLayout {
            spacing: 8
            LabText {
                theme: appTheme
                text: "快速操作"
                variant: "section"
                strong: true
                Layout.fillWidth: true
            }
            LabTextField {
                id: paletteSearch
                objectName: "commandPaletteSearch"
                theme: appTheme
                accessibleLabel: placeholderText
                Layout.fillWidth: true
                placeholderText: "搜索页面或动作…"
                selectByMouse: true
                onTextChanged: window.paletteQuery = text
                onAccepted: {
                    var items = window.paletteItems()
                    if (items.length > 0)
                        window.triggerPaletteAction(items[0].id)
                }
                Keys.onDownPressed: {
                    if (paletteList.count > 0) {
                        paletteList.forceActiveFocus()
                        paletteList.currentIndex = Math.max(0, paletteList.currentIndex)
                    }
                }
            }
            ListView {
                id: paletteList
                objectName: "commandPaletteList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 3
                model: window.paletteItems()
                onCountChanged: {
                    // Filtering can shrink the model below the previously
                    // selected index. Always leave Enter on a real first
                    // result (or no result), never on an invisible row.
                    currentIndex = count > 0
                                   ? Math.min(Math.max(currentIndex, 0), count - 1)
                                   : -1
                }
                Keys.onReturnPressed: {
                    if (currentIndex >= 0 && currentIndex < count)
                        window.triggerPaletteAction(window.paletteItems()[currentIndex].id)
                }
                delegate: LabButton {
                    id: paletteActionButton
                    required property var modelData
                    required property int index
                    property bool selected: index === paletteList.currentIndex
                    theme: appTheme
                    variant: "ghost"
                    width: paletteList.width
                    height: 48
                    focusPolicy: Qt.StrongFocus
                    onClicked: window.triggerPaletteAction(modelData.id)
                    background: Rectangle {
                        radius: appTheme.radiusMedium
                        color: paletteActionButton.selected
                               || paletteActionButton.hovered
                               || paletteActionButton.activeFocus
                               ? appTheme.surfaceHover
                               : "transparent"
                        border.color: paletteActionButton.activeFocus
                                      ? appTheme.focusRing : "transparent"
                        border.width: paletteActionButton.activeFocus ? 2 : 0
                    }
                    contentItem: RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10
                        LabText {
                            theme: appTheme
                            text: paletteActionButton.modelData.label
                            strong: true
                            Layout.preferredWidth: 142
                        }
                        LabText {
                            theme: appTheme
                            text: paletteActionButton.modelData.hint
                            tone: "muted"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
                LabText {
                    theme: appTheme
                    anchors.centerIn: parent
                    visible: paletteList.count === 0
                    text: "没有匹配的操作"
                    tone: "muted"
                }
            }
            LabText {
                theme: appTheme
                text: "Enter 执行 · Esc 关闭 · Ctrl/⌘ K 打开"
                tone: "muted"
                variant: "caption"
                Layout.fillWidth: true
            }
        }
    }

    Popup {
        id: toastPopup
        objectName: "globalToast"
        x: window.width - width - 30
        // Keep transient feedback away from the onboarding CTA and from the
        // persistent Codex approval banner when one is visible.
        y: codexApprovalBanner.visible
           ? codexApprovalBanner.y + codexApprovalBanner.height + 10
           : 82
        width: Math.min(440, message.implicitWidth + 40)
        height: 52
        modal: false
        closePolicy: Popup.NoAutoClose
        background: Rectangle {
            color: appTheme.toastBackground
            radius: appTheme.radiusMedium
            border.color: appTheme.borderStrong
            border.width: 1
        }
        contentItem: Text {
            id: message
            color: appTheme.toastForeground
            font.pixelSize: appTheme.fontBody
            wrapMode: Text.Wrap
            verticalAlignment: Text.AlignVCenter
            anchors.fill: parent
            anchors.margins: 14
        }
        Timer { id: toastTimer; interval: 3600; onTriggered: toastPopup.close() }
    }
    Connections {
        target: backend
        function onToast(text) { message.text = text; toastPopup.open(); toastTimer.restart() }
    }
    Connections {
        target: backend
        function onCodexApproval(value) {
            if (!value || !value.request_id)
                return
            window.pendingCodexApproval = value
            window.approvalActionInFlight = false
        }
    }
    Connections {
        target: backend
        function onCodexApprovalResolved(requestId) {
            if (!window.pendingCodexApproval
                    || String(window.pendingCodexApproval.request_id) !== String(requestId))
                return
            window.pendingCodexApproval = ({})
            window.approvalActionInFlight = false
            approvalDialog.close()
        }
        function onCodexApprovalFailed(value) {
            if (!value || !window.pendingCodexApproval
                    || String(window.pendingCodexApproval.request_id) !== String(value.request_id))
                return
            window.approvalActionInFlight = false
            message.text = String(value.error || "审批未发送，请重试；请求仍保持待处理。")
            toastPopup.open()
            toastTimer.restart()
        }
    }
    Connections {
        target: backend
        function onStateChanged() {
            if (backend.onboardingRequired && commandPalette.opened)
                commandPalette.close()
        }
    }

    Dialog {
        id: approvalDialog
        objectName: "codexApprovalDetails"
        title: "检查 Codex 操作"
        header: null
        modal: true
        closePolicy: Popup.NoAutoClose
        standardButtons: Dialog.NoButton
        anchors.centerIn: parent
        width: Math.min(window.width - 48, 720)
        height: Math.min(window.height - 64, 600)
        background: Rectangle {
            color: appTheme.surfaceRaised
            radius: appTheme.radiusLarge
            border.color: appTheme.borderDefault
        }

        contentItem: ColumnLayout {
            spacing: 12
            LabText {
                theme: appTheme
                text: approvalDialog.title
                variant: "section"
                strong: true
                Layout.fillWidth: true
            }
            LabDivider { theme: appTheme; Layout.fillWidth: true }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: width
                contentHeight: approvalDetailsColumn.implicitHeight
                ScrollBar.vertical: LabScrollBar {
                    theme: appTheme
                    policy: ScrollBar.AsNeeded
                }
                ColumnLayout {
                    id: approvalDetailsColumn
                    width: parent.width
                    spacing: 9
                    LabText {
                        theme: appTheme
                        Layout.fillWidth: true
                        text: "请求 ID：" + (window.pendingCodexApproval
                                               && window.pendingCodexApproval.request_id || "")
                        tone: "muted"
                        variant: "caption"
                        elide: Text.ElideMiddle
                    }
                    LabText {
                        theme: appTheme
                        Layout.fillWidth: true
                        text: "操作：" + (window.pendingCodexApproval
                                           && window.pendingCodexApproval.action || "")
                              + "\n范围：" + (window.pendingCodexApproval
                                              && window.pendingCodexApproval.scope || "")
                              + "\n文件：" + window.approvalFiles(window.pendingCodexApproval)
                              + "\n命令：" + (window.pendingCodexApproval
                                             && window.pendingCodexApproval.command || "")
                              + "\n原因：" + (window.pendingCodexApproval
                                             && window.pendingCodexApproval.reason || "")
                              + "\n风险：" + (window.pendingCodexApproval
                                             && window.pendingCodexApproval.risk || "")
                        wrapMode: Text.WordWrap
                    }
                    LabText {
                        theme: appTheme
                        visible: !!(window.pendingCodexApproval
                                    && window.pendingCodexApproval.diff)
                        text: "Diff"
                        tone: "muted"
                        strong: true
                    }
                    TextArea {
                        visible: !!(window.pendingCodexApproval
                                    && window.pendingCodexApproval.diff)
                        Layout.fillWidth: true
                        Layout.preferredHeight: 230
                        text: (window.pendingCodexApproval
                               && window.pendingCodexApproval.diff || "")
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.NoWrap
                        font.family: "Cascadia Mono, Consolas, monospace"
                        color: window.colors.text
                        background: Rectangle {
                            color: window.colors.surfaceAlt
                            radius: 6
                            border.color: window.colors.border
                        }
                        Accessible.name: "Codex 提议的 Diff"
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                LabButton {
                    objectName: "codexApprovalClose"
                    theme: appTheme
                    variant: "ghost"
                    text: "稍后处理"
                    enabled: !window.approvalActionInFlight
                    onClicked: approvalDialog.close()
                }
                Item { Layout.fillWidth: true }
                LabButton {
                    objectName: "codexApprovalDecline"
                    theme: appTheme
                    variant: "danger"
                    text: "拒绝"
                    enabled: !window.approvalActionInFlight
                    onClicked: window.resolveApproval("decline")
                }
                LabButton {
                    objectName: "codexApprovalApprove"
                    theme: appTheme
                    variant: "primary"
                    text: window.approvalActionInFlight ? "处理中…" : "仅批准本次"
                    enabled: !window.approvalActionInFlight
                    onClicked: window.resolveApproval("accept")
                }
            }
        }
    }

    LabDialog {
        id: aboutDialog
        objectName: "aboutDialog"
        theme: appTheme
        title: "关于 LLM Interview Lab"
        anchors.centerIn: parent
        width: 440
        message: "LLM Interview Lab " + Qt.application.version
        detailText: "本地优先、岗位感知、AI 辅助的面试训练工作台。\n无需连接 AI 也可完整使用固定课程与手动模拟面试。"
        primaryText: "知道了"
        showSecondary: false
    }
}
