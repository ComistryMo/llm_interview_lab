import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    required property var theme
    contentWidth: width; contentHeight: content.implicitHeight + 60; clip: true
    property bool advanced: false
    // Editing stays local to this form. The key itself is never read back
    // from the keyring; an empty key field means "keep existing".
    property string editingConnectionId: ""
    property string formError: ""
    property bool saving: false
    // Keep the first configuration fields in view on compact desktop windows.
    // The full explanations remain available at a taller viewport without
    // changing the connection model or its actions.
    // `height` is the page viewport below the shell header.  A 1440×900
    // window should retain the explanatory Codex copy; compact copy is only
    // needed for the short 620/680px targets.
    property bool compactOverview: height < 680
    property bool compactForm: width < 760
    // Keep the two status cards on one visual baseline.  A shared minimum is
    // less distracting than letting each card size itself from a different
    // amount of copy, especially beside the first configuration fields.
    property int overviewCardMinHeight: compactOverview ? 96 : 150

    function connectionStatusTone(value) {
        var status = String(value || "").toLowerCase()
        if (status.indexOf("失败") >= 0 || status.indexOf("error") >= 0)
            return root.palette.danger
        if (status.indexOf("连接") >= 0 || status.indexOf("就绪") >= 0
                || status === "connected" || status === "ready")
            return root.palette.success
        if (status.indexOf("测试") >= 0 || status.indexOf("验证") >= 0)
            return root.palette.warning
        return root.palette.muted
    }

    property string pendingDeleteConnectionId: ""
    property string pendingDeleteConnectionName: ""

    function requestDeleteConnection(item) {
        if (!item)
            return
        root.pendingDeleteConnectionId = String(item.connection_id || "")
        root.pendingDeleteConnectionName = String(item.display_name || item.connection_id || "此连接")
        deleteConnectionDialog.open()
    }

    function clearFormError() {
        root.formError = ""
        if (typeof app.clearConnectionError === "function")
            app.clearConnectionError()
    }

    function beginEditConnection(item) {
        if (!item)
            return
        root.editingConnectionId = String(item.connection_id || "")
        root.clearFormError()
        root.advanced = true
        var providers = app.providerOptions || []
        var providerIndex = -1
        for (var i = 0; i < providers.length; ++i) {
            if (String(providers[i]) === String(item.provider_id || "")) {
                providerIndex = i
                break
            }
        }
        if (providerIndex < 0) {
            root.formError = "该连接使用了当前版本不支持的服务，无法安全编辑；请保留原配置或新建受支持的连接。"
            return
        }
        provider.currentIndex = providerIndex
        // Keep the stable storage id tied to the record being edited.  The
        // id is not silently regenerated or changed when a user edits the
        // display fields.
        connectionId.text = root.editingConnectionId
        model.text = String(item.model || "")
        var effortValue = String(item.reasoning_effort || "")
        for (var j = 0; j < reasoningEffort.count; ++j) {
            if (String(reasoningEffort.model[j].value) === effortValue) {
                reasoningEffort.currentIndex = j
                break
            }
        }
        displayName.text = String(item.display_name || "")
        endpoint.text = String(item.base_url || "")
        // Remote credentials are write-only. Keep this blank so saveConnection
        // preserves the existing key_reference.
        secretOrEndpoint.text = item.provider_id === "ollama"
                                ? String(item.base_url || "") : ""
    }

    function cancelEditConnection() {
        root.editingConnectionId = ""
        root.clearFormError()
        root.advanced = false
        provider.currentIndex = 0
        model.text = ""
        reasoningEffort.currentIndex = 0
        secretOrEndpoint.text = ""
        endpoint.text = ""
        connectionId.text = provider.currentText + "-main"
        displayName.text = provider.currentText
    }
    ScrollBar.vertical: ScrollBar {
        width: 6
        policy: ScrollBar.AlwaysOn
        visible: root.contentHeight > root.height
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 3
            color: root.palette.muted
            opacity: 0.45
        }
    }

    ColumnLayout {
        id: content
        x: root.compactForm ? 18 : 28
        y: root.compactForm ? 18 : 24
        width: parent.width - (root.compactForm ? 36 : 56)
        spacing: root.compactForm ? 10 : 12

        // Main.qml owns the route title; use this smaller line for the
        // actionable context and keep the optional nature visible.
        Text {
            objectName: "connectionsRouteContext"
            text: "本地优先，按需连接 AI"
            color: root.palette.text
            font.pixelSize: 16
            font.bold: true
        }
        Text {
            text: root.compactOverview
                  ? "不连接 AI 也能训练；远程请求仅发送你确认的内容。"
                  : "不连接 AI 也能完成固定课程、测试、复测和手动面试。远程请求只发送你确认的上下文。"
            color: root.palette.muted
            wrapMode: Text.Wrap
            // Security guidance must not disappear behind an ellipsis.  The
            // compact copy is short enough for one line on the target window,
            // and may naturally wrap to a second line on narrower screens.
            maximumLineCount: 2
            elide: Text.ElideNone
            Layout.fillWidth: true
        }

        GridLayout {
            id: connectionOverview
            Layout.fillWidth: true
            columns: content.width < 820 ? 1 : 2
            columnSpacing: 14
            rowSpacing: root.compactOverview ? 8 : 14
            LabCard {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: connectionOverview.columns === 2
                                       ? (connectionOverview.width
                                          - connectionOverview.columnSpacing) / 2
                                       : connectionOverview.width
                Layout.preferredHeight: Math.max(root.overviewCardMinHeight, implicitHeight)
                Layout.alignment: Qt.AlignTop
                cardColor: root.palette.surface; borderColor: root.palette.border
                accentColor: root.palette.success
                padding: root.compactOverview ? 10 : 14
                RowLayout {
                    width: parent.width
                    Text { text: "无需 AI"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                    Item { Layout.fillWidth: true }
                    StatusPill { text: "始终可用"; tone: root.palette.success }
                }
                Text {
                    width: parent.width
                    text: root.compactOverview
                          ? "无需配置，训练可直接进行。"
                          : "课程、测试、审查、复测和手动面试都在本机运行。"
                    color: root.compactOverview ? root.palette.text : root.palette.muted
                    wrapMode: Text.Wrap
                    maximumLineCount: root.compactOverview ? 1 : 2
                    elide: Text.ElideRight
                    font.bold: root.compactOverview
                }
                Text {
                    // The compact sentence above already communicates the
                    // No-AI guarantee.  Keep this reinforcing sentence for
                    // the taller layout only so the card does not repeat
                    // itself at 900x620/1080x680.
                    visible: !root.compactOverview
                    width: parent.width
                    text: "AI 不可用时仍可继续训练。"
                    color: root.palette.text
                    wrapMode: Text.Wrap
                    font.bold: true
                }
            }
            LabCard {
                id: codexCard
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: connectionOverview.columns === 2
                                       ? (connectionOverview.width
                                          - connectionOverview.columnSpacing) / 2
                                       : connectionOverview.width
                Layout.alignment: Qt.AlignTop
                // At the minimum supported window width the four actions do
                // not fit in one row. Let the card use two predictable rows
                // instead of silently pushing the settings action off-screen.
                Layout.preferredHeight: Math.max(root.overviewCardMinHeight, implicitHeight)
                cardColor: root.palette.surface; borderColor: root.palette.border
                accentColor: root.palette.accent
                padding: root.compactOverview ? 10 : 14
                RowLayout {
                    width: parent.width
                    Text { text: "Codex"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                    Item { Layout.fillWidth: true }
                    StatusPill {
                        text: app.aiStatusVariant === "connected" ? "已连接"
                              : app.aiStatusVariant === "connecting" ? "连接中"
                              : app.codexAvailable ? "已发现（未连接）" : "未检测到"
                        tone: app.aiStatusVariant === "connected" ? root.palette.success
                              : app.aiStatusVariant === "connecting" ? root.palette.warning
                              : app.codexAvailable ? root.palette.accent : root.palette.warning
                    }
                }
                Text {
                    width: parent.width
                    text: !app.codexAvailable
                          ? "未检测到 Codex，可在设置中选择路径或继续使用 No-AI。"
                          : app.aiStatusVariant === "connected"
                            ? "Codex 已连接，可使用只读教练或经审批的仓库代理。"
                            : "已找到 Codex，但还没有建立连接；请确认已登录后再点击连接。"
                    color: root.palette.muted
                    wrapMode: Text.Wrap
                    maximumLineCount: root.compactOverview ? 1 : 3
                    elide: Text.ElideRight
                    visible: true
                }
                RowLayout {
                    width: parent.width
                    spacing: 8
                    Text {
                        objectName: "codexModelEffortSummary"
                        Layout.fillWidth: true
                        text: "模型：" + (app.codexModel || "默认")
                              + " · 推理强度：" + (app.codexReasoningEffort || "默认")
                        color: root.palette.muted
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                    Button {
                        objectName: "openCodexModelSettings"
                        text: "模型与推理强度"
                        flat: true
                        onClicked: app.navigate("settings")
                    }
                }
                GridLayout {
                    id: codexActions
                    width: parent.width
                    columns: root.compactOverview || codexCard.width < 500 ? 2 : 4
                    columnSpacing: 8
                    rowSpacing: root.compactOverview ? 4 : 6
                    Button { visible: app.codexAvailable; enabled: app.aiStatusVariant !== "connecting"; Layout.fillWidth: true; Layout.preferredHeight: root.compactOverview ? 32 : 34; text: "教练模式"; flat: true; onClicked: app.connectCodex("coach") }
                    Button { visible: app.codexAvailable; enabled: app.aiStatusVariant !== "connecting"; Layout.fillWidth: true; Layout.preferredHeight: root.compactOverview ? 32 : 34; text: "仓库代理模式"; flat: true; onClicked: app.connectCodex("repository_agent") }
                    Button { Layout.fillWidth: true; Layout.preferredHeight: root.compactOverview ? 32 : 34; text: "重新检测"; flat: true; onClicked: app.refreshCodexAvailability() }
                    Button { Layout.fillWidth: true; Layout.preferredHeight: root.compactOverview ? 32 : 34; text: "查找设置"; flat: true; visible: !app.codexAvailable; onClicked: app.navigate("settings") }
                }
            }
        }

        LabCard {
            Layout.fillWidth: true
            // Let LabCard's implicit height follow the visible form rows.  A
            // fixed height used to let the privacy note spill into the next
            // section after the primary action was moved to the header.
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text {
                text: root.editingConnectionId.length > 0 ? "编辑 AI 连接" : "连接普通 LLM API"
                color: root.palette.text
                font.pixelSize: 18
                font.bold: true
            }
            // Keep the primary action adjacent to the form heading so it remains
            // discoverable in the initial viewport on compact desktop windows.
            RowLayout {
                visible: root.editingConnectionId.length > 0
                width: parent.width
                spacing: 8
                StatusPill { text: "正在编辑"; tone: root.palette.accent }
                Text {
                    text: root.editingConnectionId
                    color: root.palette.muted
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
                Button {
                    text: "取消编辑"
                    flat: true
                    onClicked: root.cancelEditConnection()
                }
            }
            RowLayout {
                width: parent.width
                spacing: 12
                Button {
                    objectName: "saveAndTestConnection"
                    // Static contract: text: "保存并测试"
                    text: root.saving ? "正在保存并测试…" : "保存并测试"
                    highlighted: true
                    enabled: model.text.trim().length > 0 && !root.saving && !app.busy
                    onClicked: {
                        root.saving = true
                        var isOllama = provider.currentText === "ollama"
                        var saved = app.saveConnection(connectionId.text, provider.currentText, model.text,
                                                       displayName.text, isOllama ? secretOrEndpoint.text : endpoint.text,
                                                       isOllama ? "" : secretOrEndpoint.text,
                                                       reasoningEffort.currentValue)
                        if (saved) {
                            root.formError = ""
                            app.testConnection(connectionId.text)
                            if (!isOllama) secretOrEndpoint.text = ""
                            root.editingConnectionId = ""
                        } else {
                            root.formError = "保存失败。请检查连接 ID、模型和地址；远程服务的 API Key 必须可由系统密钥环保存。"
                        }
                        // saveConnection is synchronous; testConnection owns
                        // the asynchronous busy state. Release this local guard
                        // after the one save call so a failed save can be fixed
                        // immediately, while app.busy blocks duplicate tests.
                        root.saving = false
                    }
                }
                Text {
                    text: "填写模型并向下补充地址或密钥；保存后会自动测试连接。"
                    color: root.palette.muted
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
            GridLayout {
                width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 10
                Text { text: "服务"; color: root.palette.muted }
                ComboBox {
                    id: provider
                    Layout.fillWidth: true
                    model: app.providerOptions
                    enabled: root.editingConnectionId.length === 0
                    onActivated: root.clearFormError()
                }
                Text { text: "模型"; color: root.palette.muted }
                LabTextField {
                    id: model
                    theme: root.theme
                    Layout.fillWidth: true
                    placeholderText: "例如 gpt-5、claude 或本地模型 ID"
                    onTextEdited: root.clearFormError()
                }
                Text { text: "推理强度"; color: root.palette.muted }
                ComboBox {
                    id: reasoningEffort
                    objectName: "providerReasoningEffort"
                    Layout.fillWidth: true
                    textRole: "label"
                    valueRole: "value"
                    model: [
                        {value: "", label: "使用服务默认值"},
                        {value: "low", label: "低"},
                        {value: "medium", label: "中"},
                        {value: "high", label: "高"},
                        {value: "xhigh", label: "极高"}
                    ]
                    onActivated: root.clearFormError()
                }
                Text {
                    text: "仅在所选模型支持时生效；不确定时保留默认值。"
                    color: root.palette.muted
                    font.pixelSize: 12
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                Text {
                    visible: model.text.trim().length === 0
                    text: "请输入模型 ID 后才能保存并测试。"
                    color: root.palette.warning
                    font.pixelSize: 12
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                Text { text: provider.currentText === "ollama" ? "本地地址" : "API Key"; color: root.palette.muted }
                LabTextField {
                    id: secretOrEndpoint; Layout.fillWidth: true
                    theme: root.theme
                    placeholderText: provider.currentText === "ollama" ? "http://127.0.0.1:11434" : "仅保存到系统密钥环"
                    echoMode: provider.currentText === "ollama" ? TextInput.Normal : TextInput.Password
                    onTextEdited: root.clearFormError()
                }
                Text {
                    visible: provider.currentText === "ollama"
                    text: "Ollama 使用本机地址，不需要 API Key。"
                    color: root.palette.muted
                    font.pixelSize: 12
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }
            ToolButton { text: root.advanced ? "收起高级设置" : "展开高级设置"; onClicked: root.advanced = !root.advanced }
            Text {
                objectName: "connectionFormError"
                visible: root.formError.length > 0 || (app.connectionError || "").length > 0
                text: app.connectionError || root.formError
                color: root.palette.danger
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            GridLayout {
                visible: root.advanced
                width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 10
                LabTextField {
                    id: connectionId
                    theme: root.theme
                    Layout.fillWidth: true
                    text: provider.currentText + "-main"
                    readOnly: root.editingConnectionId.length > 0
                    placeholderText: root.editingConnectionId.length > 0
                                     ? "编辑时保持连接 ID 不变" : "连接 ID"
                }
                LabTextField {
                    id: displayName
                    theme: root.theme
                    Layout.fillWidth: true
                    text: provider.currentText === "ollama" ? "本地 Ollama" : provider.currentText
                    placeholderText: "显示名称"
                    onTextEdited: root.clearFormError()
                }
                LabTextField {
                    id: endpoint
                    theme: root.theme
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    placeholderText: "自定义 Endpoint（OpenAI-compatible 可选）"
                    onTextEdited: root.clearFormError()
                }
            }
            Text {
                text: "Key 不会写入学习档案、事件或日志。"
                color: root.palette.muted
                font.pixelSize: 12
                width: parent.width
                wrapMode: Text.Wrap
            }
        }

        Text { text: "已保存的连接"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
        Text { visible: app.connections.length === 0; text: "尚未配置。你可以直接使用无需 AI 的本地模式。"; color: root.palette.muted }
        Repeater {
            model: app.connections
            delegate: LabCard {
                required property var modelData
                // The old single-row delegate pushed three action buttons
                // beyond the viewport at 900px.  A metadata row plus a
                // wrapping action row keeps every action reachable without
                // shrinking labels to unreadable glyphs.
                Layout.fillWidth: true
                Layout.preferredHeight: root.compactForm ? 142 : 116
                cardColor: root.palette.surface; borderColor: root.palette.border
                ColumnLayout {
                    width: parent.width
                    height: parent.height
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: modelData.display_name || modelData.connection_id; color: root.palette.text; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text {
                                text: modelData.provider_id + " · " + modelData.model
                                      + (modelData.reasoning_effort
                                         ? " · 推理 " + modelData.reasoning_effort : "")
                                color: root.palette.muted
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                                font.pixelSize: 12
                            }
                        }
                        StatusPill {
                            text: modelData.status || "已保存，尚未测试"
                            tone: root.connectionStatusTone(modelData.status)
                            Layout.alignment: Qt.AlignTop
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 6
                        layoutDirection: Qt.LeftToRight
                        Button {
                            objectName: "editConnection"
                            text: "编辑"
                            flat: true
                            enabled: !root.saving && !app.busy
                            implicitHeight: 32
                            onClicked: root.beginEditConnection(modelData)
                        }
                        Button {
                            text: app.busy ? "测试中…" : "测试连接"
                            flat: true
                            enabled: !app.busy
                            implicitHeight: 32
                            onClicked: app.testConnection(modelData.connection_id)
                        }
                        Button {
                            text: "删除"
                            flat: true
                            enabled: !root.saving && !app.busy
                            implicitHeight: 32
                            onClicked: root.requestDeleteConnection(modelData)
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteConnectionDialog
        objectName: "deleteConnectionDialog"
        modal: true
        anchors.centerIn: parent
        title: "删除这个连接？"
        width: Math.min(440, root.width - 48)
        implicitHeight: 210
        height: implicitHeight
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            if (root.pendingDeleteConnectionId.length > 0)
                app.deleteConnection(root.pendingDeleteConnectionId)
            root.pendingDeleteConnectionId = ""
            root.pendingDeleteConnectionName = ""
        }
        onRejected: {
            root.pendingDeleteConnectionId = ""
            root.pendingDeleteConnectionName = ""
        }
        contentItem: Text {
            // Give Dialog a stable content size; binding width to the Dialog
            // implicit size creates a loop in Qt 6 when the Chinese copy
            // wraps at the minimum window.
            width: Math.min(360, Math.max(240, root.width - 96))
            text: "将删除“" + root.pendingDeleteConnectionName
                  + "”的本地连接配置。系统密钥环中的 Key 不会被读取或展示；删除后仍可重新配置。"
            color: root.palette.text
            wrapMode: Text.Wrap
        }
    }
}
