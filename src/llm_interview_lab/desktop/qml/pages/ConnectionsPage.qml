import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    contentWidth: width; contentHeight: content.implicitHeight + 60; clip: true
    property var pendingApproval: ({})
    property bool advanced: false

    function approvalFiles() {
        var value = root.pendingApproval.files
        if (!value) return ""
        return typeof value.join === "function" ? value.join(", ") : String(value)
    }

    ColumnLayout {
        id: content
        x: 28; y: 24; width: parent.width - 56; spacing: 16

        Text { text: "AI 连接（可选）"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
        Text { text: "不连接 AI 也能完成固定课程、公开测试、间隔复测和手动模拟面试。远程请求只发送你在上下文预览中确认的内容。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }

        RowLayout {
            Layout.fillWidth: true; spacing: 14
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 190
                cardColor: root.palette.surface; borderColor: root.palette.border
                RowLayout {
                    width: parent.width
                    Text { text: "无需 AI"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                    Item { Layout.fillWidth: true }
                    StatusPill { text: "始终可用"; tone: root.palette.success }
                }
                Text { width: parent.width; text: "默认模式。课程、Grader、审查、复测和手动面试都在本机运行。"; color: root.palette.muted; wrapMode: Text.Wrap }
                Text { width: parent.width; text: "AI 当前不可用时，你仍然可以继续本地训练和手动模拟面试。"; color: root.palette.text; wrapMode: Text.Wrap; font.bold: true }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 190
                cardColor: root.palette.surface; borderColor: root.palette.border
                RowLayout {
                    width: parent.width
                    Text { text: "Codex"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                    Item { Layout.fillWidth: true }
                    StatusPill { text: app.codexAvailable ? "可用" : "未检测到"; tone: app.codexAvailable ? root.palette.success : root.palette.warning }
                }
                Text { width: parent.width; text: "通过官方 App Server 使用 Thread、流式事件、Diff、取消和显式审批；不会解析交互式终端输出。"; color: root.palette.muted; wrapMode: Text.Wrap }
                RowLayout {
                    Button { text: "教练模式"; enabled: app.codexAvailable; onClicked: app.connectCodex("coach") }
                    Button { text: "仓库代理模式"; enabled: app.codexAvailable; onClicked: app.connectCodex("repository_agent") }
                    Button { text: "查找设置"; visible: !app.codexAvailable; onClicked: app.navigate("settings") }
                }
            }
        }

        LabCard {
            Layout.fillWidth: true
            Layout.preferredHeight: root.advanced ? 390 : 315
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "连接普通 LLM API"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            GridLayout {
                width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 10
                Text { text: "服务"; color: root.palette.muted }
                ComboBox { id: provider; Layout.fillWidth: true; model: app.providerOptions }
                Text { text: "模型"; color: root.palette.muted }
                TextField { id: model; Layout.fillWidth: true; placeholderText: "例如 gpt-5、claude 或本地模型 ID" }
                Text { text: provider.currentText === "ollama" ? "本地地址" : "API Key"; color: root.palette.muted }
                TextField {
                    id: secretOrEndpoint; Layout.fillWidth: true
                    placeholderText: provider.currentText === "ollama" ? "http://127.0.0.1:11434" : "仅保存到系统密钥环"
                    echoMode: provider.currentText === "ollama" ? TextInput.Normal : TextInput.Password
                }
            }
            ToolButton { text: root.advanced ? "收起高级设置" : "展开高级设置"; onClicked: root.advanced = !root.advanced }
            GridLayout {
                visible: root.advanced
                width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 10
                TextField { id: connectionId; Layout.fillWidth: true; text: provider.currentText + "-main"; placeholderText: "连接 ID" }
                TextField { id: displayName; Layout.fillWidth: true; text: provider.currentText === "ollama" ? "本地 Ollama" : provider.currentText; placeholderText: "显示名称" }
                TextField { id: endpoint; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: "自定义 Endpoint（OpenAI-compatible 可选）" }
            }
            RowLayout {
                width: parent.width
                Text { text: "Key 不会写入学习档案、事件或日志。"; color: root.palette.muted; font.pixelSize: 12; Layout.fillWidth: true }
                Button {
                    text: "保存连接"; highlighted: true
                    enabled: model.text.length > 0
                    onClicked: {
                        var isOllama = provider.currentText === "ollama"
                        app.saveConnection(connectionId.text, provider.currentText, model.text,
                                           displayName.text, isOllama ? secretOrEndpoint.text : endpoint.text,
                                           isOllama ? "" : secretOrEndpoint.text)
                        if (!isOllama) secretOrEndpoint.text = ""
                    }
                }
            }
        }

        Text { text: "已保存的连接"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
        Text { visible: app.connections.length === 0; text: "尚未配置。你可以直接使用无需 AI 的本地模式。"; color: root.palette.muted }
        Repeater {
            model: app.connections
            delegate: LabCard {
                required property var modelData
                Layout.fillWidth: true; Layout.preferredHeight: 100
                cardColor: root.palette.surface; borderColor: root.palette.border
                RowLayout {
                    width: parent.width; height: parent.height
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.display_name; color: root.palette.text; font.bold: true }
                        Text { text: modelData.provider_id + " · " + modelData.model; color: root.palette.muted }
                    }
                    StatusPill { text: modelData.status || "已保存，尚未测试"; tone: (modelData.status || "").indexOf("已连接") >= 0 ? root.palette.success : root.palette.muted }
                    Button { text: "测试连接"; flat: true; onClicked: app.testConnection(modelData.connection_id) }
                    Button { text: "删除"; flat: true; onClicked: app.deleteConnection(modelData.connection_id) }
                }
            }
        }

        LabCard {
            visible: !!root.pendingApproval.request_id
            Layout.fillWidth: true; Layout.preferredHeight: root.pendingApproval.diff ? 400 : 275
            cardColor: root.palette.surface; borderColor: root.palette.warning
            Text { text: "Codex 请求操作审批"; color: root.palette.warning; font.pixelSize: 18; font.bold: true }
            Text {
                width: parent.width
                text: "操作：" + (root.pendingApproval.action || "") + "\n范围：" + (root.pendingApproval.scope || "") + "\n文件：" + root.approvalFiles() + "\n命令：" + (root.pendingApproval.command || "") + "\n原因：" + (root.pendingApproval.reason || "") + "\n风险：" + (root.pendingApproval.risk || "")
                color: root.palette.text; wrapMode: Text.Wrap
            }
            ScrollView {
                visible: !!root.pendingApproval.diff; width: parent.width; Layout.fillHeight: true; clip: true
                TextArea {
                    text: root.pendingApproval.diff || ""; readOnly: true; selectByMouse: true
                    wrapMode: TextEdit.NoWrap; font.family: "Cascadia Mono, Consolas, monospace"
                    color: root.palette.text
                    background: Rectangle { color: root.palette.surfaceAlt; radius: 6; border.color: root.palette.border }
                    Accessible.name: "Codex 提议的 Diff"
                }
            }
            RowLayout {
                Button { text: "拒绝"; onClicked: { app.resolveCodexApproval(root.pendingApproval.request_id, "decline"); root.pendingApproval = ({}) } }
                Button { text: "仅批准本次"; highlighted: true; onClicked: { app.resolveCodexApproval(root.pendingApproval.request_id, "accept"); root.pendingApproval = ({}) } }
            }
        }
    }

    Connections { target: app; function onCodexApproval(value) { root.pendingApproval = value } }
}
