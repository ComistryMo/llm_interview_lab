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
    Material.theme: backend.theme === "dark" ? Material.Dark
                    : backend.theme === "light" ? Material.Light
                    : Material.System
    // Keep native Material controls aligned with the shell palette.
    Material.accent: backend.theme === "dark" ? "#91adff" : "#3159d9"

    // Material.System is a style selection, not a resolved color scheme.  Use
    // the platform hint as well so custom surfaces follow the system theme
    // instead of silently remaining light on a dark desktop.
    property bool dark: backend.theme === "dark"
                        || (backend.theme === "system"
                            && Qt.application.styleHints
                            && Qt.application.styleHints.colorScheme === Qt.ColorScheme.Dark)
    property var colors: ({
        // A quiet neutral canvas keeps the single accent colour reserved for
        // actions and progress.  This is deliberately a palette adjustment,
        // not a second theme system, so every existing page keeps its data
        // and interaction behaviour.
        "background": dark ? "#0e141f" : "#f4f7fb",
        "surface": dark ? "#161e2b" : "#ffffff",
        "surfaceAlt": dark ? "#1d2939" : "#edf2f8",
        "border": dark ? "#2d3a4d" : "#d7e0ec",
        "text": dark ? "#f0f4fa" : "#172033",
        "muted": dark ? "#a8b5c8" : "#66738a",
        "accent": dark ? "#91adff" : "#3159d9",
        "success": dark ? "#6ddbb1" : "#087a55",
        "warning": dark ? "#f2bf79" : "#8a4b08",
        "danger": dark ? "#ff91a1" : "#b4233a"
    })
    // Prefer the platform's bundled CJK UI face when it is available.  The
    // empty Linux value deliberately keeps Qt's normal fallback chain intact;
    // forcing a font that is not installed is what turns Chinese copy into
    // tofu on minimal CI images.
    property string uiFontFamily: Qt.platform.os === "windows" ? "Microsoft YaHei UI"
                                       : Qt.platform.os === "osx" ? "PingFang SC" : ""
    // The shell gets a small responsive breakpoint of its own.  Keeping the
    // decision here lets pages use their full content width while the
    // navigation/header remain legible at the 900px minimum window.
    property bool compactShell: width < 1040
    property string paletteQuery: ""
    property var paletteActions: [
        {id: "home", label: "打开首页", hint: "继续训练或开始模拟面试"},
        {id: "learn", label: "打开刷题训练", hint: "按课程前置选择题目"},
        {id: "interview", label: "打开模拟面试", hint: "开始或恢复结构化面试"},
        {id: "coach", label: "打开 AI 教练", hint: "查看上下文并请求只读帮助"},
        {id: "career", label: "打开求职材料", hint: "管理当前 Profile 的材料"},
        {id: "progress", label: "打开学习进度", hint: "查看当前 Profile 的进度"},
        {id: "connections", label: "打开 AI 连接", hint: "配置或测试普通 LLM"},
        {id: "settings", label: "打开设置", hint: "外观、本地目录与 Codex"},
        {id: "run-tests", label: "运行公开测试", hint: "保存当前编辑器并运行测试", exerciseOnly: true}
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

    function triggerPaletteAction(actionId) {
        if (actionId === "run-tests") {
            if (backend.currentPage === "exercise" && !backend.busy)
                backend.runTests()
            commandPalette.close()
            return
        }
        backend.navigate(actionId)
        commandPalette.close()
    }

    function compactAiStatus(value) {
        var status = String(value || "")
        if (status.indexOf("已连接") >= 0 || status.indexOf("就绪") >= 0)
            return "AI 已连接"
        if (status.indexOf("失败") >= 0 || status.indexOf("不可用") >= 0
                || status.indexOf("错误") >= 0)
            return "AI 连接失败"
        if (status.indexOf("检测") >= 0 || status.indexOf("连接中") >= 0
                || status.indexOf("处理中") >= 0)
            return "检测中"
        return "No-AI 可用"
    }
    font.pixelSize: Math.round(14 * backend.fontScale)
    // An empty family lets Qt use the platform fallback chain.  Reading
    // Qt.application.font.family on minimal Linux/offscreen setups yields the
    // synthetic “Sans Serif” alias and triggers a needless font lookup.
    font.family: uiFontFamily
    color: colors.background

    menuBar: MenuBar {
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

        Rectangle {
            Layout.preferredWidth: window.compactShell ? 184 : 216
            Layout.fillHeight: true
            color: window.dark ? "#121a27" : "#fbfcfe"
            border.color: window.colors.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 5

                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: window.compactShell ? 14 : 20
                    Rectangle {
                        width: 36; height: 36; radius: 10
                        color: window.colors.accent
                        border.color: Qt.rgba(1, 1, 1, window.dark ? 0.16 : 0.24)
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "LL"
                            color: "white"
                            font.bold: true
                            font.pixelSize: 13
                            font.letterSpacing: 0.4
                        }
                    }
                    ColumnLayout {
                        spacing: 0
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Text {
                            id: brandTitle
                            // Keep the compact lockup intentional instead of
                            // letting the product name wrap at an arbitrary word.
                            text: window.compactShell ? "LLM\nInterview Lab" : "LLM Interview Lab"
                            color: window.colors.text
                            font.bold: true
                            font.pixelSize: window.compactShell ? 14 : 15
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: window.width < 1160 ? 2 : 1
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
                            text: "本地 AI 面试训练工作台"
                            color: window.colors.muted
                            font.pixelSize: 11
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
                    Button {
                        id: navButton
                        required property var modelData
                        Layout.fillWidth: true
                        // Compact, 38px targets keep the high-frequency loop
                        // comfortably keyboard/mouse accessible.
                        Layout.preferredHeight: 38
                        // Keep the compact shell focused on the daily loop;
                        // the remaining destinations are exposed by the real
                        // command palette and the explicit “更多入口…” action.
                        visible: !window.compactShell || modelData.id === "home"
                                 || modelData.id === "learn"
                                 || modelData.id === "interview"
                                 || modelData.id === "coach"
                        text: modelData.label
                        flat: true
                        font.weight: backend.currentPage === modelData.id ? Font.DemiBold : Font.Normal
                        onClicked: backend.navigate(modelData.id)
                        background: Rectangle {
                            radius: 10
                            color: backend.currentPage === modelData.id
                                   ? Qt.rgba(0.192, 0.349, 0.851, 0.13)
                                   : navButton.hovered
                                     ? Qt.rgba(0.192, 0.349, 0.851, 0.06)
                                     : "transparent"
                            border.color: navButton.activeFocus ? window.colors.accent : "transparent"
                            border.width: navButton.activeFocus ? 2 : 0
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Rectangle {
                                visible: backend.currentPage === modelData.id
                                width: 3
                                height: 20
                                radius: 2
                                anchors.left: parent.left
                                anchors.leftMargin: 2
                                anchors.verticalCenter: parent.verticalCenter
                                color: window.colors.accent
                            }
                        }
                        contentItem: Text {
                            text: navButton.text
                            color: backend.currentPage === modelData.id ? window.colors.accent : window.colors.text
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 14
                            font.pixelSize: 13
                        }
                    }
                }

                Text {
                    text: "主要"
                    color: window.colors.muted
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.6
                    Layout.topMargin: 2
                }
                Repeater {
                    model: [
                        {id: "home", label: backend.uiText("nav.home")},
                        {id: "learn", label: backend.uiText("nav.learn")},
                        {id: "interview", label: backend.uiText("nav.interview")}
                    ]
                    delegate: navButtonDelegate
                }

                Text {
                    visible: !window.compactShell
                    text: "个人"
                    color: window.colors.muted
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.6
                    Layout.topMargin: 8
                }
                Repeater {
                    model: [
                        {id: "career", label: backend.uiText("nav.career")},
                        {id: "coach", label: backend.uiText("nav.coach")},
                        {id: "progress", label: backend.uiText("nav.progress")}
                    ]
                    delegate: navButtonDelegate
                }

                Text {
                    visible: !window.compactShell
                    text: "配置"
                    color: window.colors.muted
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.6
                    Layout.topMargin: 8
                }
                Repeater {
                    model: [
                        {id: "connections", label: backend.uiText("nav.connections")},
                        {id: "settings", label: backend.uiText("nav.settings")}
                    ]
                    delegate: navButtonDelegate
                }

                // Secondary destinations remain real and keyboard reachable
                // through the palette.  At the minimum window width the
                // sidebar presents only the high-frequency loop, with an
                // explicit affordance so newcomers do not have to know the
                // Ctrl/⌘K shortcut in advance.
                Button {
                    id: moreNavigationButton
                    objectName: "moreNavigationButton"
                    visible: window.compactShell
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    text: "更多入口…"
                    flat: true
                    onClicked: {
                        commandPalette.open()
                        paletteSearch.forceActiveFocus()
                        paletteSearch.selectAll()
                    }
                    contentItem: Text {
                        text: moreNavigationButton.text
                        color: window.colors.muted
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignLeft
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 14
                    }
                }

                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 70
                    radius: 10
                    color: window.colors.surfaceAlt
                    border.color: window.colors.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 3
                        Text { text: "学习档案"; color: window.colors.muted; font.pixelSize: 11; font.weight: Font.DemiBold }
                        Text { text: backend.profileDisplayName || backend.profileId; color: window.colors.text; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: "Alpha · 数据默认保存在本机"; color: window.colors.muted; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 68
                color: window.colors.surface
                border.color: window.colors.border
                Rectangle {
                    // A small anchor line gives the shell a quiet brand cue
                    // without competing with page actions.
                    width: 32
                    height: 3
                    radius: 1.5
                    anchors.left: parent.left
                    anchors.leftMargin: 30
                    anchors.bottom: parent.bottom
                    color: window.colors.accent
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 30
                    anchors.rightMargin: 30
                    Text {
                        Layout.fillWidth: true
                        text: ({home:"首页", career:"求职材料", learn:"刷题训练", exercise:"答题工作区", interview:"模拟面试", coach:"AI 教练", progress:"学习进度", connections:"AI 连接", settings:"设置"})[backend.currentPage] || "LLM Interview Lab"
                        color: window.colors.text
                        font.pixelSize: window.compactShell ? 19 : 21
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    Item { Layout.fillWidth: true; visible: !window.compactShell }
                    Rectangle {
                        visible: (!!backend.profileDisplayName || !!backend.profileId) && !window.compactShell
                        property int profileChipMaxWidth: window.width < 1100 ? 150 : 230
                        Layout.preferredHeight: 30
                        Layout.maximumWidth: profileChipMaxWidth
                        Layout.minimumWidth: 48
                        Layout.preferredWidth: Math.min(profileChipMaxWidth,
                                                        Math.max(48, profileNameLabel.implicitWidth + 24))
                        radius: 8
                        color: window.colors.surfaceAlt
                        border.color: window.colors.border
                        Text {
                            id: profileNameLabel
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            text: backend.profileDisplayName || backend.profileId || ""
                            color: window.colors.muted
                            font.pixelSize: 12
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                    }
                    StatusPill {
                        visible: true
                        text: window.compactShell ? window.compactAiStatus(backend.aiStatus) : backend.aiStatus
                        tone: backend.aiStatus.indexOf("已连接") >= 0 || backend.aiStatus.indexOf("就绪") >= 0
                              ? window.colors.success
                              : backend.aiStatus.indexOf("失败") >= 0 || backend.aiStatus.indexOf("不可用") >= 0
                                ? window.colors.danger : window.colors.muted
                    }
                    BusyIndicator { running: backend.busy; visible: running; implicitWidth: 28; implicitHeight: 28 }
                }
            }

            // Safety prompts stay visible while the user moves between pages.
            // In the normal state this item has zero layout cost; when a
            // request arrives it reserves space above page content instead of
            // covering a page CTA.
            Rectangle {
                id: codexApprovalBanner
                objectName: "codexApprovalBanner"
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 82 : 0
                Layout.minimumHeight: 0
                visible: !!(window.pendingCodexApproval
                            && window.pendingCodexApproval.request_id)
                z: 30
                color: window.dark ? "#3b2f1a" : "#fff7df"
                border.color: window.colors.warning
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 22
                    anchors.rightMargin: 22
                    spacing: 14
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Codex 请求等待审批"
                            color: window.colors.warning
                            font.bold: true
                            font.pixelSize: 15
                        }
                        Text {
                            Layout.fillWidth: true
                            text: (window.pendingCodexApproval
                                   && window.pendingCodexApproval.action || "操作")
                                  + " · " + (window.pendingCodexApproval
                                              && window.pendingCodexApproval.scope
                                              || "当前仓库")
                            color: window.colors.text
                            elide: Text.ElideRight
                        }
                    }
                    Button {
                        objectName: "codexApprovalViewButton"
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
                HomePage { app: backend; palette: window.colors }
                CareerPage { app: backend; palette: window.colors }
                LearnPage { app: backend; palette: window.colors }
                ExercisePage { app: backend; palette: window.colors }
                InterviewPage { app: backend; palette: window.colors }
                CoachPage { app: backend; palette: window.colors }
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
        background: Rectangle {
            color: window.colors.surface
            radius: 12
            border.color: window.colors.border
            border.width: 1
        }
        contentItem: ColumnLayout {
            spacing: 8
            Text {
                text: "快速操作"
                color: window.colors.text
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }
            TextField {
                id: paletteSearch
                objectName: "commandPaletteSearch"
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
                background: Rectangle {
                    color: window.colors.surfaceAlt
                    radius: 8
                    border.color: paletteSearch.activeFocus ? window.colors.accent : window.colors.border
                    border.width: paletteSearch.activeFocus ? 2 : 1
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
                delegate: Button {
                    required property var modelData
                    required property int index
                    property bool selected: index === paletteList.currentIndex
                    width: paletteList.width
                    height: 48
                    flat: true
                    focusPolicy: Qt.StrongFocus
                    onClicked: window.triggerPaletteAction(modelData.id)
                    background: Rectangle {
                        radius: 8
                        color: parent.selected || parent.hovered || parent.activeFocus
                               ? window.colors.surfaceAlt
                               : "transparent"
                    }
                    contentItem: RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10
                        Text {
                            text: modelData.label
                            color: window.colors.text
                            font.bold: true
                            Layout.preferredWidth: 142
                        }
                        Text {
                            text: modelData.hint
                            color: window.colors.muted
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: paletteList.count === 0
                    text: "没有匹配的操作"
                    color: window.colors.muted
                }
            }
            Text {
                text: "Enter 执行 · Esc 关闭 · Ctrl/⌘ K 打开"
                color: window.colors.muted
                font.pixelSize: 11
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
            color: window.dark ? "#222d3d" : "#172033"
            radius: 10
            border.color: window.dark
                          ? Qt.rgba(0.569, 0.678, 1.0, 0.5)
                          : Qt.rgba(0.192, 0.349, 0.851, 0.5)
            border.width: 1
        }
        contentItem: Text {
            id: message
            color: "white"
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
        modal: true
        closePolicy: Popup.NoAutoClose
        standardButtons: Dialog.NoButton
        anchors.centerIn: parent
        width: Math.min(window.width - 48, 720)
        height: Math.min(window.height - 64, 600)

        contentItem: ColumnLayout {
            spacing: 12
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: width
                contentHeight: approvalDetailsColumn.implicitHeight
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }
                ColumnLayout {
                    id: approvalDetailsColumn
                    width: parent.width
                    spacing: 9
                    Text {
                        Layout.fillWidth: true
                        text: "请求 ID：" + (window.pendingCodexApproval
                                               && window.pendingCodexApproval.request_id || "")
                        color: window.colors.muted
                        font.pixelSize: 12
                        elide: Text.ElideMiddle
                    }
                    Text {
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
                        color: window.colors.text
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        visible: !!(window.pendingCodexApproval
                                    && window.pendingCodexApproval.diff)
                        text: "Diff"
                        color: window.colors.muted
                        font.bold: true
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
                Button {
                    objectName: "codexApprovalClose"
                    text: "稍后处理"
                    enabled: !window.approvalActionInFlight
                    onClicked: approvalDialog.close()
                }
                Item { Layout.fillWidth: true }
                Button {
                    objectName: "codexApprovalDecline"
                    text: "拒绝"
                    enabled: !window.approvalActionInFlight
                    onClicked: window.resolveApproval("decline")
                }
                Button {
                    objectName: "codexApprovalApprove"
                    text: window.approvalActionInFlight ? "处理中…" : "仅批准本次"
                    highlighted: true
                    enabled: !window.approvalActionInFlight
                    onClicked: window.resolveApproval("accept")
                }
            }
        }
    }

    Dialog {
        id: aboutDialog
        title: "关于 LLM Interview Lab"
        modal: true
        standardButtons: Dialog.Ok
        anchors.centerIn: parent
        width: 440
        contentItem: Text {
            width: 400
            text: "LLM Interview Lab " + Qt.application.version + "\n\n本地优先、岗位感知、AI 辅助的面试训练工作台。\n无需连接 AI 也可完整使用固定课程与手动模拟面试。"
            color: window.colors.text
            wrapMode: Text.Wrap
            lineHeight: 1.35
        }
    }
}
