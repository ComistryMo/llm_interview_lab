import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette

    property bool compactLayout: width < 980
    property bool wideLayout: width >= 1180
    property var sessions: app.coachSessions || []
    property var activeSession: app.activeCoachSession || ({})
    property var messages: app.coachMessages || []
    property var preview: ({"parts": [], "estimated_tokens": 0})
    property bool syncingDraft: false
    property string syncedSessionId: ""
    property string inlineError: app.coachError || ""
    property string pendingDeleteId: ""
    property string pendingDeleteTitle: ""
    property bool codexSelected: false
    property bool hasSession: !!root.activeSession.session_id
    property bool hasMessages: root.messages.length > 0

    function providerItems() {
        var result = [{connection_id: "none", provider_id: "none",
                       display_name: "No-AI · 本地可用", model: "",
                       status: "本地可用", local: true}]
        var saved = app.connections || []
        for (var i = 0; i < saved.length; ++i)
            result.push(saved[i])
        if (app.codexAvailable || root.activeSession.provider_kind === "codex")
            result.push({connection_id: "codex", provider_id: "codex",
                         display_name: "Codex", model: "",
                         status: app.aiStatus || "未连接", codex: true})
        return result
    }

    function selectedProviderItem() {
        var value = provider.currentValue || "none"
        var items = root.providerItems()
        for (var i = 0; i < items.length; ++i) {
            if (String(items[i].connection_id || "") === String(value))
                return items[i]
        }
        return items[0]
    }

    function selectedProviderReady() {
        var item = root.selectedProviderItem()
        if (!item)
            return false
        if (item.local)
            return true
        if (item.codex)
            return String(app.aiStatus || "").match(/已连接|就绪|connected|ready/) !== null
        var status = String(item.status || "")
        return status === "connected" || status === "ready"
               || status.indexOf("已连接") >= 0 || status.indexOf("就绪") >= 0
    }

    function providerStatusHint() {
        var item = root.selectedProviderItem()
        if (!item)
            return "先新建会话。"
        if (item.local)
            return "No-AI：只在本机保存会话，不请求远程模型。"
        if (item.codex && !root.selectedProviderReady())
            return "Codex 尚未连接；可点击连接，或切换 No-AI。"
        if (!root.selectedProviderReady())
            return "连接尚未测试；请先在 AI 连接页测试，或切换 No-AI。"
        return (item.display_name || item.provider_id || "AI") + " 已就绪。"
    }

    function modeLabel(value) {
        return ({coach: "教练", teacher: "讲解", reviewer: "审查"})[value] || "教练"
    }

    function roleLabel(value) {
        return ({user: "你", assistant: "AI", system: "规则", tool: "工具",
                 approval: "审批", error: "错误"})[value] || value || "消息"
    }

    function statusLabel(value) {
        return ({idle: "已保存", streaming: "生成中", stopped: "已停止", error: "需要重试"})[value]
               || value || "未创建"
    }

    function statusTone(value) {
        return !value ? root.palette.muted
             : value === "streaming" ? root.palette.accent
             : value === "error" ? root.palette.danger
             : value === "stopped" ? root.palette.warning
             : root.palette.success
    }

    function connectionReady(item) {
        var status = String(item && item.status || "")
        return status.indexOf("已连接") >= 0 || status.indexOf("就绪") >= 0
                || status === "connected" || status === "ready"
    }

    function providerLabel() {
        if (root.activeSession.provider_kind === "codex")
            return "Codex"
        if (root.activeSession.provider_id === "none"
                || root.activeSession.provider_kind === "none")
            return "No-AI · 本地"
        if (root.activeSession.model)
            return (root.activeSession.provider_id || "AI") + " · " + root.activeSession.model
        if (root.activeSession.provider_id)
            return root.activeSession.provider_id
        return "未选择 AI"
    }

    function syncSession(force) {
        var id = String(root.activeSession.session_id || "")
        if (!id || force || id !== root.syncedSessionId) {
            root.syncingDraft = true
            prompt.text = String(root.activeSession.draft || "")
            root.syncingDraft = false
            root.syncedSessionId = id
        }
        var modeId = String(root.activeSession.mode || "coach")
        for (var modeIndex = 0; modeIndex < mode.count; ++modeIndex) {
            if (String(mode.model[modeIndex].id || "") === modeId) {
                if (mode.currentIndex !== modeIndex)
                    mode.currentIndex = modeIndex
                break
            }
        }
        var providerId = String(root.activeSession.provider_id
                                || root.activeSession.provider_kind || "none")
        var providerValues = root.providerItems()
        var providerIndex = 0
        for (var providerLoop = 0; providerLoop < providerValues.length; ++providerLoop) {
            if (String(providerValues[providerLoop].connection_id || "") === providerId
                    || (providerId === "codex" && providerValues[providerLoop].codex)) {
                providerIndex = providerLoop
                break
            }
        }
        if (provider.count > 0 && provider.currentIndex !== providerIndex)
            provider.currentIndex = providerIndex
        root.codexSelected = providerValues[providerIndex]
                && providerValues[providerIndex].codex === true
    }

    function refreshPreview() {
        var modeId = mode.currentValue || root.activeSession.mode || "coach"
        root.preview = app.practiceContextPreview(
            modeId,
            modeId === "teacher" ? helpLevel.currentText : "",
            includeSubmission.checked,
            includeTestOutput.checked
        )
    }

    function selectedContextCount() {
        var parts = root.preview.parts || []
        var count = 0
        for (var i = 0; i < parts.length; ++i)
            if (parts[i].selected)
                count += 1
        return count
    }

    function send() {
        var value = prompt.text.trim()
        if (!root.hasSession) {
            root.inlineError = "请先新建一个本地 Coach 会话。"
            return
        }
        if (!value.length || app.coachStreaming)
            return
        if (!root.selectedProviderReady()) {
            root.inlineError = root.providerStatusHint()
            return
        }
        var selectedProvider = root.codexSelected ? "codex" : (provider.currentValue || "none")
        var selectedMode = mode.currentValue || root.activeSession.mode || "coach"
        var accepted = app.sendCoachTurnConfigured(
            value,
            selectedMode,
            selectedMode === "teacher" ? helpLevel.currentText : "",
            selectedProvider,
            includeSubmission.checked,
            includeTestOutput.checked
        )
        if (accepted) {
            root.syncingDraft = true
            prompt.text = ""
            root.syncingDraft = false
        }
    }

    function copyAll() {
        var lines = []
        var values = root.messages || []
        for (var i = 0; i < values.length; ++i) {
            if (values[i].content)
                lines.push(root.roleLabel(values[i].role) + "：" + values[i].content)
        }
        if (lines.length)
            app.copyCoachText(lines.join("\n\n"))
    }

    function requestDelete(item) {
        if (!item) return
        root.pendingDeleteId = String(item.session_id || "")
        root.pendingDeleteTitle = String(item.title || "这个会话")
        deleteDialog.open()
    }

    function createSession() {
        if (app.coachStreaming)
            return
        var accepted = app.createCoachSession(
            mode.currentValue || "coach",
            provider.currentValue || "none",
            app.currentTask && app.currentTask.problem_id ? app.currentTask.problem_id : "",
            ""
        )
        if (accepted) {
            root.syncSession(true)
            root.refreshPreview()
        }
    }

    onActiveSessionChanged: {
        root.syncSession(false)
        root.refreshPreview()
    }
    onVisibleChanged: if (visible) Qt.callLater(root.syncSession)

    RowLayout {
        anchors.fill: parent
        anchors.margins: root.compactLayout ? 12 : 22
        spacing: 12

        LabCard {
            id: sessionRail
            visible: !root.compactLayout
            Layout.preferredWidth: root.wideLayout ? 224 : 204
            Layout.minimumWidth: 190
            Layout.fillHeight: true
            padding: 12
            cardColor: root.palette.surface
            borderColor: root.palette.border
            ColumnLayout {
                // LabCard already places this child inside its padded content
                // column.  Use dimensions instead of anchors so the shared
                // Column does not receive an anchored child (which makes
                // Qt Quick emit a layout warning and can break placement).
                width: parent.width
                height: parent.height
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "会话"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                    Item { Layout.fillWidth: true }
                    ToolButton {
                        objectName: "newCoachSession"
                        text: "+"
                        ToolTip.visible: hovered
                        ToolTip.text: "新建会话"
                        onClicked: root.createSession()
                    }
                }
                Button {
                    text: "新建 Coach 会话"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    highlighted: true
                    enabled: !app.coachStreaming
                    onClicked: root.createSession()
                }
                Text {
                    Layout.fillWidth: true
                    text: root.sessions.length ? "最近会话" : "还没有本地会话"
                    color: root.palette.muted
                    font.pixelSize: 12
                    font.bold: true
                }
                ListView {
                    id: sessionList
                    objectName: "coachSessionList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 5
                    model: root.sessions
                    delegate: Rectangle {
                        required property var modelData
                        width: sessionList.width
                        height: 64
                        radius: 8
                        color: modelData.session_id === root.activeSession.session_id
                               ? Qt.rgba(root.palette.accent.r, root.palette.accent.g, root.palette.accent.b, 0.12)
                               : "transparent"
                        border.color: modelData.session_id === root.activeSession.session_id
                                      ? root.palette.accent : "transparent"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6
                            z: 1
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.title || "未命名会话"
                                    color: root.palette.text
                                    font.bold: modelData.session_id === root.activeSession.session_id
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: root.modeLabel(modelData.mode) + " · " + root.statusLabel(modelData.status)
                                          + (modelData.message_count ? " · " + modelData.message_count : "")
                                    color: root.palette.muted
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
                            }
                            ToolButton {
                                text: "…"
                                padding: 2
                                enabled: !app.coachStreaming
                                Accessible.name: "删除 Coach 会话"
                                onClicked: root.requestDelete(modelData)
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            z: 0
                            enabled: !app.coachStreaming
                            onClicked: app.selectCoachSession(modelData.session_id)
                        }
                    }
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                }
                Text {
                    Layout.fillWidth: true
                    text: "会话只保存在当前 Profile；不计入掌握状态。"
                    color: root.palette.muted
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }
        }

        LabCard {
            id: chatCard
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 0
            padding: root.compactLayout ? 12 : 16
            cardColor: root.palette.surface
            borderColor: root.palette.border
            prominent: true
            ColumnLayout {
                width: parent.width
                height: parent.height
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    ToolButton {
                        visible: root.compactLayout
                        text: "会话"
                        enabled: !app.coachStreaming
                        onClicked: sessionDrawer.open()
                    }
                    Button {
                        visible: root.compactLayout && !root.hasSession
                        text: "新建会话"
                        highlighted: true
                        enabled: !app.coachStreaming
                        onClicked: root.createSession()
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root.activeSession.title || "AI 教练"
                            color: root.palette.text
                            font.pixelSize: 20
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.activeSession.session_id
                                  ? root.modeLabel(root.activeSession.mode) + " · " + root.providerLabel()
                                  : "新建会话后，选择范围再发送问题"
                            color: root.palette.muted
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                    StatusPill {
                        text: root.statusLabel(root.activeSession.status)
                        tone: root.statusTone(root.activeSession.status)
                    }
                    ToolButton {
                        visible: root.wideLayout
                        text: "上下文"
                        onClicked: contextDrawer.open()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.inlineError.length
                                              ? Math.max(58, errorText.implicitHeight + 22) : 0
                    Layout.minimumHeight: 0
                    visible: root.inlineError.length > 0
                    radius: 8
                    color: Qt.rgba(root.palette.danger.r, root.palette.danger.g, root.palette.danger.b, 0.10)
                    border.color: root.palette.danger
                    Text {
                        id: errorText
                        anchors.fill: parent
                        anchors.margins: 10
                        text: root.inlineError + "\n可检查连接后重试；本地课程和手动面试仍可继续。"
                        color: root.palette.danger
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                }

                ListView {
                    id: messageList
                    objectName: "coachMessageList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 120
                    clip: true
                    spacing: 10
                    model: root.messages
                    delegate: Item {
                        required property var modelData
                        width: messageList.width
                        height: bubble.implicitHeight + 4
                        Rectangle {
                            id: bubble
                            width: Math.min(parent.width, parent.width * 0.92)
                            anchors.right: modelData.role === "user" ? parent.right : undefined
                            anchors.left: modelData.role === "user" ? undefined : parent.left
                            implicitHeight: bubbleColumn.implicitHeight + 20
                            radius: 10
                            color: modelData.role === "user"
                                   ? Qt.rgba(root.palette.accent.r, root.palette.accent.g, root.palette.accent.b, 0.12)
                                   : modelData.role === "error"
                                     ? Qt.rgba(root.palette.danger.r, root.palette.danger.g, root.palette.danger.b, 0.10)
                                     : root.palette.surfaceAlt
                            border.color: modelData.role === "error" ? root.palette.danger : root.palette.border
                            ColumnLayout {
                                id: bubbleColumn
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 5
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: root.roleLabel(modelData.role)
                                        color: modelData.role === "error" ? root.palette.danger : root.palette.muted
                                        font.bold: true
                                        font.pixelSize: 11
                                    }
                                    Item { Layout.fillWidth: true }
                                    Button {
                                        visible: !!modelData.content
                                        text: "复制"
                                        flat: true
                                        implicitHeight: 26
                                        onClicked: app.copyCoachText(modelData.content)
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.content || (modelData.role === "assistant" ? "正在生成……" : "")
                                    color: root.palette.text
                                    wrapMode: Text.Wrap
                                    textFormat: Text.PlainText
                                    lineHeight: 1.25
                                }
                            }
                        }
                    }
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    onCountChanged: Qt.callLater(function() { messageList.positionViewAtEnd() })
                    onContentHeightChanged: if (app.coachStreaming) Qt.callLater(function() { messageList.positionViewAtEnd() })
                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 32, 420)
                        height: emptyColumn.implicitHeight + 26
                        visible: messageList.count === 0
                        radius: 10
                        color: root.palette.surfaceAlt
                        border.color: root.palette.border
                        ColumnLayout {
                            id: emptyColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 6
                            Text { text: "从一个具体问题开始"; color: root.palette.text; font.pixelSize: 17; font.bold: true }
                            Text {
                                Layout.fillWidth: true
                                text: "先新建会话，再选择教练、讲解或审查模式；可按需发送当前答案和测试摘要。AI 不会替你改答案。"
                                color: root.palette.muted
                                wrapMode: Text.Wrap
                            }
                            Button {
                                visible: !root.hasSession
                                text: "新建本地会话"
                                highlighted: true
                                Layout.alignment: Qt.AlignLeft
                                enabled: !app.coachStreaming
                                onClicked: root.createSession()
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    ComboBox {
                        id: mode
                        Layout.preferredWidth: 92
                        model: [{id: "coach", label: "教练"}, {id: "teacher", label: "讲解"}, {id: "reviewer", label: "审查"}]
                        textRole: "label"
                        valueRole: "id"
                        enabled: !(root.activeSession.message_count > 0 || root.messages.length > 0)
                        onCurrentValueChanged: {
                            if (!root.activeSession.session_id || root.messages.length === 0)
                                root.refreshPreview()
                        }
                    }
                    ComboBox {
                        id: provider
                        Layout.fillWidth: true
                        model: root.providerItems()
                        textRole: "display_name"
                        valueRole: "connection_id"
                        // Provider/model is part of the saved session context.
                        // Once a transcript exists, use a new session instead
                        // of silently changing the provider for old messages.
                        enabled: !app.coachStreaming && !root.hasMessages
                        onCurrentValueChanged: {
                            var item = root.selectedProviderItem()
                            root.codexSelected = !!(item && item.codex)
                            root.refreshPreview()
                        }
                        Component.onCompleted: root.syncSession(true)
                    }
                    Button {
                        visible: root.codexSelected && app.codexAvailable
                                 && !String(app.aiStatus || "").match(/已连接|就绪|connected|ready/)
                        text: "连接 Codex"
                        enabled: !app.coachStreaming
                        onClicked: app.connectCodex(mode.currentValue === "reviewer" ? "reviewer" : "coach")
                    }
                    ToolButton {
                        visible: root.compactLayout
                        text: "上下文"
                        onClicked: contextDrawer.open()
                    }
                }

                Text {
                    objectName: "coachModelLabel"
                    Layout.fillWidth: true
                    visible: provider.currentIndex >= 0
                    text: {
                        var item = root.selectedProviderItem()
                        var modelName = item && item.model ? String(item.model) : "默认模型"
                        return "模型 · " + modelName
                    }
                    color: root.palette.muted
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                ComboBox {
                    id: helpLevel
                    visible: mode.currentValue === "teacher"
                    Layout.fillWidth: true
                    model: ["H1", "H2", "H3"]
                    currentIndex: 1
                    onCurrentTextChanged: root.refreshPreview()
                }

                    TextArea {
                    id: prompt
                    objectName: "coachPrompt"
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.compactLayout ? 76 : 92
                    enabled: !app.coachStreaming
                    placeholderText: app.coachStreaming ? "正在生成回答……" : "输入问题；Enter 发送，Shift+Enter 换行"
                    wrapMode: Text.Wrap
                    color: root.palette.text
                    padding: 12
                    background: Rectangle {
                        color: root.palette.background
                        radius: 8
                        border.color: prompt.activeFocus ? root.palette.accent : root.palette.border
                        border.width: prompt.activeFocus ? 2 : 1
                    }
                    onTextChanged: if (!root.syncingDraft && root.activeSession.session_id) app.updateCoachDraft(text)
                    Keys.onPressed: function(event) {
                        if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                                && !(event.modifiers & Qt.ShiftModifier)) {
                            event.accepted = true
                            root.send()
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: app.coachStreaming ? "正在接收流式回答 · 可随时停止" : root.providerStatusHint()
                        color: app.coachStreaming ? root.palette.accent : root.palette.muted
                        font.pixelSize: 11
                    }
                    Button {
                        visible: app.coachStreaming
                        text: "停止"
                        objectName: "stopCoachTurn"
                        onClicked: app.stopCoachTurn()
                    }
                    Button {
                        visible: !app.coachStreaming && (root.activeSession.status === "error" || root.activeSession.status === "stopped")
                        text: "重试"
                        objectName: "retryCoachTurn"
                        onClicked: app.retryCoachTurn()
                    }
                    Button {
                        visible: !app.coachStreaming && root.messages.length > 0
                        text: "复制全部"
                        onClicked: root.copyAll()
                    }
                    Button {
                        objectName: "sendCoachTurn"
                        text: "发送"
                        highlighted: true
                        enabled: root.hasSession && prompt.text.trim().length > 0
                                 && !app.coachStreaming && root.selectedProviderReady()
                        onClicked: root.send()
                    }
                }
            }
        }

        LabCard {
            id: contextPanel
            visible: root.wideLayout
            Layout.preferredWidth: 274
            Layout.minimumWidth: 250
            Layout.fillHeight: true
            padding: 12
            cardColor: root.palette.surface
            borderColor: root.palette.border
            ColumnLayout {
                width: parent.width
                height: parent.height
                spacing: 9
                Text { text: "上下文预览"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                Text {
                    Layout.fillWidth: true
                    text: "只发送下方明确选择的当前题面、答案或测试摘要。"
                    color: root.palette.muted
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
                CheckBox { id: includeSubmission; Layout.fillWidth: true; text: "包含当前答案"; onCheckedChanged: root.refreshPreview() }
                CheckBox { id: includeTestOutput; Layout.fillWidth: true; text: "包含测试摘要"; checked: true; onCheckedChanged: root.refreshPreview() }
                Button { Layout.fillWidth: true; text: "刷新预览"; onClicked: root.refreshPreview() }
                Rectangle { Layout.fillWidth: true; height: 1; color: root.palette.border }
                    Text {
                        Layout.fillWidth: true
                        text: "将发送 " + root.selectedContextCount() + " 项 · 约 "
                              + (root.preview.estimated_tokens || 0) + " tokens"
                              color: root.palette.muted
                              font.pixelSize: 11
                        }
                Text {
                    Layout.fillWidth: true
                    visible: root.hasMessages
                    text: "另会带上最近 " + Math.min(8, root.messages.length)
                          + " 条本地对话；如需改变范围，请新建会话。"
                    color: root.palette.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
                ListView {
                    id: contextList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.preview.parts || []
                    delegate: RowLayout {
                        required property var modelData
                        width: contextList.width
                        spacing: 6
                        StatusPill { text: modelData.selected ? "发送" : "不发送"; tone: modelData.selected ? root.palette.accent : root.palette.muted }
                        Text { Layout.fillWidth: true; text: modelData.label; color: root.palette.text; wrapMode: Text.Wrap; font.pixelSize: 11 }
                        StatusPill { visible: modelData.sensitive; text: "敏感"; tone: root.palette.warning }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: "AI 只提供建议；不会修改答案或授予 mastery。"
                    color: root.palette.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                    font.bold: true
                }
            }
        }
    }

    Drawer {
        id: sessionDrawer
        objectName: "coachSessionDrawer"
        edge: Qt.LeftEdge
        width: Math.min(330, root.width * 0.86)
        height: root.height
        modal: true
        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10
            Text { text: "本地 Coach 会话"; color: root.palette.text; font.pixelSize: 20; font.bold: true }
            Button { text: "新建会话"; Layout.fillWidth: true; highlighted: true; onClicked: { root.createSession(); sessionDrawer.close() } }
            ListView {
                id: drawerSessionList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: root.sessions
                delegate: ItemDelegate {
                    required property var modelData
                    width: drawerSessionList.width
                    text: (modelData.title || "未命名会话") + "\n" + root.modeLabel(modelData.mode) + " · " + root.statusLabel(modelData.status)
                    onClicked: { app.selectCoachSession(modelData.session_id); sessionDrawer.close() }
                    ToolButton {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: "×"
                        enabled: !app.coachStreaming
                        Accessible.name: "删除 Coach 会话"
                        onClicked: {
                            sessionDrawer.close()
                            root.requestDelete(modelData)
                        }
                    }
                }
            }
            Text { text: "仅当前 Profile 可见"; color: root.palette.muted; font.pixelSize: 11 }
        }
    }

    Drawer {
        id: contextDrawer
        objectName: "coachContextDrawer"
        edge: Qt.RightEdge
        width: Math.min(340, root.width * 0.88)
        height: root.height
        modal: true
        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10
            Text { text: "上下文预览（只读）"; color: root.palette.text; font.pixelSize: 20; font.bold: true }
            Text { Layout.fillWidth: true; text: "只有标记为发送的内容会离开本机。"; color: root.palette.muted; wrapMode: Text.Wrap }
            CheckBox { id: includeSubmissionDrawer; text: "包含当前答案"; checked: includeSubmission.checked; onCheckedChanged: { includeSubmission.checked = checked; root.refreshPreview() } }
            CheckBox { id: includeTestOutputDrawer; text: "包含测试摘要"; checked: includeTestOutput.checked; onCheckedChanged: { includeTestOutput.checked = checked; root.refreshPreview() } }
            Button { text: "刷新预览"; Layout.fillWidth: true; onClicked: root.refreshPreview() }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.preview.parts || []
                delegate: RowLayout {
                    required property var modelData
                    width: parent.width
                    StatusPill { text: modelData.selected ? "将发送" : "不发送"; tone: modelData.selected ? root.palette.accent : root.palette.muted }
                    Text { Layout.fillWidth: true; text: modelData.label; color: root.palette.text; wrapMode: Text.Wrap; font.pixelSize: 12 }
                }
            }
            Button { text: "关闭"; Layout.fillWidth: true; onClicked: contextDrawer.close() }
        }
    }

    Dialog {
        id: deleteDialog
        objectName: "deleteCoachSessionDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(440, root.width - 48)
        implicitHeight: 190
        height: implicitHeight
        title: "删除本地会话？"
        standardButtons: Dialog.Cancel | Dialog.Ok
        contentItem: Text {
            width: 360
            text: "将删除“" + root.pendingDeleteTitle + "”及其本地消息。此操作不会影响答案、测试或掌握状态。"
            color: root.palette.text
            wrapMode: Text.Wrap
        }
        onAccepted: {
            if (root.pendingDeleteId.length) app.deleteCoachSession(root.pendingDeleteId)
            root.pendingDeleteId = ""
            root.pendingDeleteTitle = ""
        }
        onRejected: { root.pendingDeleteId = ""; root.pendingDeleteTitle = "" }
    }

    Connections {
        target: app
        function onCoachChanged() {
            root.inlineError = app.coachError || ""
            root.syncSession(false)
            if (root.activeSession.session_id)
                root.refreshPreview()
        }
        function onCoachErrorChanged() {
            root.inlineError = app.coachError || ""
        }
    }

    Component.onCompleted: {
        root.syncSession(true)
        root.refreshPreview()
    }
}
