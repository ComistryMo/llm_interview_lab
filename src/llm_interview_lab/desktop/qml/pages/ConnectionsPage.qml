import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var colors
    required property var theme
    signal codexSettingsRequested()
    contentWidth: width; contentHeight: content.implicitHeight + 60; clip: true
    property bool advanced: false
    // Editing stays local to this form. The key itself is never read back
    // from the keyring; an empty key field means "keep existing".
    property string editingConnectionId: ""
    property bool composingConnection: false
    readonly property bool hasSavedKey: {
        var values = app.connections || []
        for (var i = 0; i < values.length; ++i) {
            if (values[i].connection_id === connectionId.text && values[i].provider_id === provider.currentText)
                return !!values[i].key_reference
        }
        return false
    }
    property string formError: ""
    property bool saving: false
    readonly property bool deepSeek: provider.currentText === "deepseek"
    // Keep the first configuration fields in view on compact desktop windows.
    // The full explanations remain available at a taller viewport without
    // changing the connection model or its actions.
    // `height` is the page viewport below the shell header.  A 1440×900
    // window should retain the explanatory Codex copy; compact copy is only
    // needed for the short 620/680px targets.
    property bool compactOverview: height < 680
    property bool compactForm: width < 760
    property string pendingDeleteConnectionId: ""
    property string pendingDeleteConnectionName: ""
    function revealEditingForm() {
        root.cancelFlick()
        root.contentY = Math.max(0, Math.min(content.y + connectionForm.y - 12, contentHeight - height))
    }
    onContentHeightChanged: {
        if (editingConnectionId.length > 0 && (modelField.activeFocus || deepseekModel.activeFocus))
            Qt.callLater(root.revealEditingForm)
    }

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
        modelField.text = String(item.model || "")
        deepseekModel.currentIndex = deepseekModel.find(modelField.text)
        if (deepseekModel.currentIndex < 0) deepseekModel.currentIndex = 2
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
        Qt.callLater(function() {
            if (modelField.visible) {
                modelField.forceActiveFocus()
                modelField.selectAll()
            } else deepseekModel.forceActiveFocus()
            root.revealEditingForm()
        })
    }

    function cancelEditConnection() {
        root.composingConnection = false
        root.editingConnectionId = ""
        root.clearFormError()
        root.advanced = false
        provider.currentIndex = 0
        deepseekModel.currentIndex = 0
        modelField.text = root.deepSeek ? "deepseek-v4-flash" : ""
        reasoningEffort.currentIndex = 0
        secretOrEndpoint.text = ""
        endpoint.text = ""
        connectionId.text = provider.currentText + "-main"
        displayName.text = provider.currentText
    }

    function newConnectionId() {
        var base = provider.currentText + "-main"
        var ids = []
        for (var i = 0; i < app.connections.length; ++i)
            ids.push(app.connections[i].connection_id)
        var candidate = base
        for (var suffix = 2; ids.indexOf(candidate) >= 0; ++suffix)
            candidate = base + "-" + suffix
        return candidate
    }
    ScrollBar.vertical: ScrollBar {
        width: 6
        policy: ScrollBar.AlwaysOn
        visible: root.contentHeight > root.height
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 3
            color: root.colors.muted
            opacity: 0.45
        }
    }

    ColumnLayout {
        id: content
        x: (root.width - width) / 2
        y: root.compactOverview ? 12 : 24
        width: Math.min(root.theme.formWidth, root.width - (root.compactForm ? 36 : 56))
        spacing: root.compactOverview ? 8 : 16

        // Main.qml owns the route title; use this smaller line for the
        // actionable context and keep the optional nature visible.
        LabText { theme: root.theme;
            objectName: "connectionsRouteContext"
            visible: !root.compactOverview || app.connections.length === 0
            text: "本地优先，按需连接 AI"
            color: root.colors.text
            font.pixelSize: root.theme.scaledPx(18)
            strong: true
        }
        LabText { theme: root.theme;
            text: root.compactOverview
                  ? "不连接 AI 也能训练；远程请求仅发送你确认的内容。"
                  : "不连接 AI 也能完成固定课程、测试和复测。个性化模拟面试需要 AI；远程请求只发送你确认的上下文。"
            color: root.colors.muted
            wrapMode: Text.Wrap
            // Security guidance must not disappear behind an ellipsis.  The
            // compact copy is short enough for one line on the target window,
            // and may naturally wrap to a second line on narrower screens.
            maximumLineCount: 2
            elide: Text.ElideNone
            Layout.fillWidth: true
        }


        RowLayout {
            Layout.fillWidth: true
            visible: app.connections.length > 0
            LabText { theme: root.theme; text: "已保存的连接"; color: root.colors.text; font.pixelSize: root.theme.scaledPx(18); strong: true; Layout.fillWidth: true }
            LabButton {
                objectName: "newConnection"
                theme: root.theme; text: "新增连接"
                visible: app.connections.length > 0 && !root.composingConnection
                enabled: !app.busy
                onClicked: {
                    root.cancelEditConnection()
                    connectionId.text = root.newConnectionId()
                    root.composingConnection = true
                }
            }
        }
        LabText { theme: root.theme; visible: app.connections.length === 0; text: "尚未配置。你可以直接使用无需 AI 的本地模式。"; color: root.colors.muted }
        Repeater {
            model: app.connections
            delegate: LabCard {
                required property var modelData
                objectName: "savedConnectionCard"
                // The old single-row delegate pushed three action buttons
                // beyond the viewport at 900px.  A metadata row plus a
                // wrapping action row keeps every action reachable without
                // shrinking labels to unreadable glyphs.
                Layout.fillWidth: true
                theme: root.theme; padding: root.compactOverview ? 12 : 16
                cardColor: root.theme.canvas; borderColor: root.theme.borderSubtle
                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            LabText { theme: root.theme; text: modelData.display_name || modelData.connection_id; color: root.colors.text; font.pixelSize: root.theme.scaledPx(18); strong: true; elide: Text.ElideRight; Layout.fillWidth: true }
                            LabText { theme: root.theme;
                                text: modelData.provider_id + " · " + modelData.model
                                      + (modelData.reasoning_effort
                                         ? " · 推理 " + modelData.reasoning_effort : "")
                                color: root.colors.muted
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                                font.pixelSize: root.theme.scaledPx(12)
                            }
                            LabText { theme: root.theme;
                                objectName: "savedConnectionKeyStatus"
                                text: modelData.key_reference ? "Key 已保存 · 重启后自动复用" : "本地服务 · 无需 API Key"
                                color: root.colors.muted
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                font.pixelSize: root.theme.scaledPx(12)
                            }
                        }
                        StatusPill { theme: root.theme;
                            objectName: "savedConnectionStatus"
                            text: modelData.status || "已保存，尚未测试"
                            tone: modelData.ready === true ? root.colors.success
                                  : modelData.status === "连接失败" ? root.colors.danger : root.colors.muted
                            Layout.alignment: Qt.AlignTop
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 6
                        layoutDirection: Qt.LeftToRight
                        LabButton {
                            objectName: "editConnection"
                            theme: root.theme; compact: true; variant: "ghost"
                            text: "修改模型 / Key"
                            enabled: !root.saving && !app.busy
                            onClicked: root.beginEditConnection(modelData)
                        }
                        LabButton {
                            objectName: "testSavedConnection"
                            theme: root.theme; compact: true; variant: "ghost"
                            text: modelData.status === "测试中" ? "测试中…" : "测试连接"
                            enabled: !app.busy
                            onClicked: app.testConnection(modelData.connection_id)
                        }
                        LabButton {
                            objectName: "deleteSavedConnection"
                            theme: root.theme; compact: true; variant: "ghost"
                            text: "删除连接与 Key"
                            enabled: !root.saving && !app.busy
                            onClicked: root.requestDeleteConnection(modelData)
                        }
                    }
                }
            }
        }

        LabText { theme: root.theme;
            objectName: "savedConnectionError"
            visible: !connectionForm.visible && (app.connectionError || "").length > 0
            text: app.connectionError || ""
            color: root.colors.danger
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }

        LabCard {
            id: connectionForm
            objectName: "connectionForm"
            visible: root.composingConnection || root.editingConnectionId.length > 0 || app.connections.length === 0
            Layout.fillWidth: true
            // Let LabCard's implicit height follow the visible form rows.  A
            // fixed height used to let the privacy note spill into the next
            // section after the primary action was moved to the header.
            theme: root.theme; padding: 16
            cardColor: root.theme.canvas; borderColor: root.theme.borderSubtle
            LabText { theme: root.theme;
                text: root.editingConnectionId.length > 0 ? "编辑 AI 连接" : root.deepSeek ? "连接 DeepSeek" : "连接普通 LLM API"
                color: root.colors.text
                font.pixelSize: root.theme.scaledPx(18)
                strong: true
            }
            // Keep the primary action adjacent to the form heading so it remains
            // discoverable in the initial viewport on compact desktop windows.
            RowLayout {
                visible: root.editingConnectionId.length > 0
                width: parent.width
                spacing: 8
                StatusPill { theme: root.theme; text: "正在编辑"; tone: root.colors.accent }
                LabText { theme: root.theme;
                    text: root.editingConnectionId
                    color: root.colors.muted
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
                LabButton { theme: root.theme;
                    text: "取消编辑"
                    flat: true
                    onClicked: root.cancelEditConnection()
                }
            }
            RowLayout {
                width: parent.width
                spacing: 12
                LabButton {
                    objectName: "saveAndTestConnection"
                    theme: root.theme
                    variant: "primary"
                    // Static contract: text: "保存并测试"
                    text: root.saving ? "正在保存并测试…" : "保存并测试"
                    enabled: modelField.text.trim().length > 0 && !root.saving && !app.busy
                    onClicked: {
                        root.saving = true
                        var isOllama = provider.currentText === "ollama"
                        var saved = app.saveConnection(connectionId.text, provider.currentText, modelField.text,
                                                       displayName.text, isOllama ? secretOrEndpoint.text : root.deepSeek ? "" : endpoint.text,
                                                       isOllama ? "" : secretOrEndpoint.text,
                                                       reasoningEffort.currentValue)
                        if (saved) {
                            root.formError = ""
                            app.testConnection(connectionId.text)
                            if (!isOllama) secretOrEndpoint.text = ""
                            root.editingConnectionId = connectionId.text
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
                LabText { theme: root.theme;
                    text: root.hasSavedKey ? "已保存 Key，留空即可复用；输入新 Key 可替换。"
                          : root.deepSeek ? "官方地址已填好；首次连接时填写 Key。" : "填写模型与凭证，保存后自动测试。"
                    color: root.colors.muted
                    font.pixelSize: root.theme.scaledPx(12)
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }
            GridLayout {
                width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 10
                LabText { theme: root.theme; text: "服务"; color: root.colors.muted }
                LabComboBox { theme: root.theme;
                    id: provider
                    objectName: "connectionProviderChoice"
                    Layout.fillWidth: true
                    model: app.providerOptions
                    enabled: root.editingConnectionId.length === 0
                    onActivated: {
                        root.clearFormError()
                        reasoningEffort.currentIndex = 0
                        deepseekModel.currentIndex = 0
                        modelField.text = root.deepSeek ? "deepseek-v4-flash" : ""
                        connectionId.text = root.newConnectionId()
                        displayName.text = root.deepSeek ? "DeepSeek" : provider.currentText
                        secretOrEndpoint.text = ""
                        endpoint.text = ""
                    }
                }
                LabText { theme: root.theme; text: "模型"; color: root.colors.muted }
                LabComboBox { theme: root.theme;
                    id: deepseekModel
                    objectName: "deepseekModelChoice"
                    visible: root.deepSeek
                    Layout.fillWidth: true
                    model: ["deepseek-v4-flash", "deepseek-v4-pro", "自定义模型 ID"]
                    onActivated: {
                        modelField.text = currentIndex < 2 ? currentText : ""
                        root.clearFormError()
                    }
                }
                LabText { theme: root.theme; visible: root.deepSeek && deepseekModel.currentIndex === 2; text: "模型 ID"; color: root.colors.muted }
                LabTextField {
                    id: modelField
                    objectName: "connectionModelField"
                    theme: root.theme
                    Layout.fillWidth: true
                    visible: !root.deepSeek || deepseekModel.currentIndex === 2
                    text: root.deepSeek ? "deepseek-v4-flash" : ""
                    placeholderText: "例如 gpt-5、claude 或本地模型 ID"
                    onTextEdited: root.clearFormError()
                }
                LabText { theme: root.theme; text: "推理强度"; color: root.colors.muted }
                LabComboBox { theme: root.theme;
                    id: reasoningEffort
                    objectName: "providerReasoningEffort"
                    Layout.fillWidth: true
                    textRole: "label"
                    valueRole: "value"
                    model: root.deepSeek ? [
                        {value: "none", label: "关闭思考 · 更快回复"},
                        {value: "low", label: "低 · 轻量思考"},
                        {value: "high", label: "高 · 深入思考"},
                        {value: "max", label: "最高 · 等待更久"},
                        {value: "", label: "服务默认（当前为高）"}
                    ] : [
                        {value: "", label: "使用服务默认值"},
                        {value: "low", label: "低"},
                        {value: "medium", label: "中"},
                        {value: "high", label: "高"},
                        {value: "xhigh", label: "极高"}
                    ]
                    onActivated: root.clearFormError()
                }
                LabText { theme: root.theme;
                    text: root.deepSeek ? "官方地址：https://api.deepseek.com\n思考越深入通常等待越久；不会把思考片段当作回答。"
                                       : "仅在所选模型支持时生效；不确定时保留默认值。"
                    color: root.colors.muted
                    font.pixelSize: root.theme.scaledPx(12)
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                LabText { theme: root.theme;
                    visible: modelField.text.trim().length === 0
                    text: "请输入模型 ID 后才能保存并测试。"
                    color: root.colors.warning
                    font.pixelSize: root.theme.scaledPx(12)
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                LabText { theme: root.theme; text: provider.currentText === "ollama" ? "本地地址" : "API Key"; color: root.colors.muted }
                LabTextField {
                    id: secretOrEndpoint; Layout.fillWidth: true
                    objectName: "connectionSecretField"
                    theme: root.theme
                    placeholderText: provider.currentText === "ollama" ? "http://127.0.0.1:11434"
                                     : root.hasSavedKey ? "已保存，留空保留原 Key" : "首次填写，仅保存到系统密钥环"
                    echoMode: provider.currentText === "ollama" ? TextInput.Normal : TextInput.Password
                    onTextEdited: root.clearFormError()
                }
                LabText { theme: root.theme;
                    objectName: "savedApiKeyNotice"
                    visible: provider.currentText !== "ollama" && root.hasSavedKey
                    text: "Key 已保存在系统密钥环，重启后仍可使用。此处不回显密钥；只改模型或推理强度时无需重填。"
                    color: root.colors.muted
                    font.pixelSize: root.theme.scaledPx(12)
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
                LabText { theme: root.theme;
                    visible: provider.currentText === "ollama"
                    text: "Ollama 使用本机地址，不需要 API Key。"
                    color: root.colors.muted
                    font.pixelSize: root.theme.scaledPx(12)
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                }
            }
            LabButton { theme: root.theme; variant: "ghost"; text: root.advanced ? "收起高级设置" : "展开高级设置"; onClicked: root.advanced = !root.advanced }
            LabText { theme: root.theme;
                objectName: "connectionFormError"
                visible: root.formError.length > 0 || (app.connectionError || "").length > 0
                text: app.connectionError || root.formError
                color: root.colors.danger
                font.pixelSize: root.theme.scaledPx(12)
                wrapMode: Text.Wrap
                width: parent.width
            }
            GridLayout {
                visible: root.advanced
                width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 10
                LabText { theme: root.theme; text: "连接 ID"; variant: "caption"; tone: "muted" }
                LabText { theme: root.theme; text: "显示名称"; variant: "caption"; tone: "muted" }
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
                    text: provider.currentText === "ollama" ? "本地 Ollama" : root.deepSeek ? "DeepSeek" : provider.currentText
                    placeholderText: "显示名称"
                    onTextEdited: root.clearFormError()
                }
                LabText { theme: root.theme; text: "自定义 Endpoint（可选）"; variant: "caption"; tone: "muted"; Layout.columnSpan: 2; visible: !root.deepSeek }
                LabTextField {
                    id: endpoint
                    visible: !root.deepSeek
                    theme: root.theme
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    placeholderText: "自定义 Endpoint（OpenAI-compatible 可选）"
                    onTextEdited: root.clearFormError()
                }
            }
            LabText { theme: root.theme;
                text: "Key 不会写入学习档案、事件或日志。"
                color: root.colors.muted
                font.pixelSize: root.theme.scaledPx(12)
                width: parent.width
                wrapMode: Text.Wrap
            }
        }

        LabCard {
            id: codexCard
            objectName: "codexConnectionCard"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            cardColor: root.colors.surface
            borderColor: root.colors.border
            theme: root.theme
            padding: root.compactOverview ? 12 : 16
            RowLayout {
                width: parent.width
                LabText { theme: root.theme; text: "Codex"; color: root.colors.text; font.pixelSize: root.theme.scaledPx(18); strong: true }
                Item { Layout.fillWidth: true }
                StatusPill { theme: root.theme;
                    text: app.aiStatusVariant === "connected" ? "已连接"
                          : app.aiStatusVariant === "connecting" ? "连接中"
                          : app.codexAvailable ? "已发现 · 未连接" : "未检测到"
                    tone: app.aiStatusVariant === "connected" ? root.colors.success
                          : app.aiStatusVariant === "connecting" ? root.colors.warning
                          : app.codexAvailable ? root.colors.accent : root.colors.muted
                }
            }
            Column {
                width: parent.width
                spacing: 4
                LabText { theme: root.theme;
                    width: parent.width
                    text: !app.codexAvailable
                          ? "未找到 Codex。可在设置中选择程序路径；普通 LLM API 不受影响。"
                          : app.aiStatusVariant === "connected"
                            ? "已连接，可在模拟面试中选择 Codex。"
                            : "已找到程序。登录后连接，即可用于模拟面试。"
                    color: root.colors.muted
                    font.pixelSize: root.theme.scaledPx(12)
                    wrapMode: Text.Wrap
                }
                LabText { theme: root.theme;
                    objectName: "codexModelEffortSummary"
                    width: parent.width
                    text: "模型：" + (app.codexModel || "默认")
                          + " · 推理强度：" + (app.codexReasoningEffort || "默认")
                    color: root.colors.muted
                    font.pixelSize: root.theme.scaledPx(12)
                    wrapMode: Text.Wrap
                }
            }
            Flow {
                width: parent.width
                spacing: 8
                LabButton {
                    objectName: "connectCodexInterviewer"
                    theme: root.theme; compact: true
                    text: app.aiStatusVariant === "connected" ? "进入模拟面试" : "连接 Codex"
                    visible: app.codexAvailable
                    enabled: app.aiStatusVariant !== "connecting"
                    onClicked: app.aiStatusVariant === "connected" ? app.navigate("interview") : app.connectCodex("interviewer")
                }
                LabButton {
                    objectName: "openCodexModelSettings"
                    theme: root.theme; compact: true; variant: "ghost"
                    text: app.codexAvailable ? "模型与推理强度" : "安装 / 路径设置"
                    onClicked: root.codexSettingsRequested()
                }
                LabButton {
                    objectName: "refreshCodexConnection"
                    theme: root.theme; compact: true; variant: "ghost"
                    text: "重新检测"
                    onClicked: app.refreshCodexAvailability()
                }
            }
        }
        RowLayout {
            objectName: "localTrainingNotice"
            Layout.fillWidth: true
            Layout.topMargin: 4
            spacing: 10
            StatusPill { theme: root.theme; text: "本地模式"; tone: root.colors.success }
            LabText { theme: root.theme;
                Layout.fillWidth: true
                text: "无需 AI 连接，刷题、测试与复测始终可用。"
                color: root.colors.muted
                font.pixelSize: root.theme.scaledPx(12)
                wrapMode: Text.Wrap
            }
        }
    }

    LabStandardDialog { theme: root.theme;
        id: deleteConnectionDialog
        objectName: "deleteConnectionDialog"
        modal: true
        anchors.centerIn: parent
        title: "删除这个连接？"
        width: Math.min(440, root.width - 48)
        implicitHeight: deleteConnectionCopy.contentHeight + header.implicitHeight + footer.implicitHeight + padding * 2 + spacing * 2
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            if (root.pendingDeleteConnectionId.length > 0
                    && app.deleteConnection(root.pendingDeleteConnectionId)
                    && root.editingConnectionId === root.pendingDeleteConnectionId)
                root.cancelEditConnection()
            root.pendingDeleteConnectionId = ""
            root.pendingDeleteConnectionName = ""
        }
        onRejected: {
            root.pendingDeleteConnectionId = ""
            root.pendingDeleteConnectionName = ""
        }
        contentItem: LabText { theme: root.theme;
            id: deleteConnectionCopy
            // Give Dialog a stable content size; binding width to the Dialog
            // implicit size creates a loop in Qt 6 when the Chinese copy
            // wraps at the minimum window.
            width: deleteConnectionDialog.availableWidth
            text: "将删除“" + root.pendingDeleteConnectionName
                  + "”的本地连接配置及系统密钥环中的 Key。不会删除档案、材料或面试记录；使用这个服务时需重新填写 Key。"
            color: root.colors.text
            wrapMode: Text.Wrap
        }
    }
}
