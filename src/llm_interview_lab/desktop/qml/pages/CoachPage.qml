import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property var preview: ({"parts": [], "estimated_tokens": 0})
    property bool hasSavedProvider: (app.connections || []).length > 0
    property var readyConnections: root.readyProviderConnections()
    property bool aiAvailable: root.readyConnections.length > 0 || root.codexReady()
    property bool awaitingResponse: false
    property bool inlineError: false
    property string inlineStatus: ""

    function connectionReady(item) {
        var status = String(item && item.status || "")
        return status.indexOf("已连接") >= 0
                || status.indexOf("就绪") >= 0
                || status === "connected"
                || status === "ready"
    }

    function readyProviderConnections() {
        var connections = app.connections || []
        var ready = []
        for (var i = 0; i < connections.length; ++i) {
            if (root.connectionReady(connections[i]))
                ready.push(connections[i])
        }
        return ready
    }

    function codexReady() {
        var status = String(app.aiStatus || "")
        return status.indexOf("已连接") >= 0
                || status.indexOf("就绪") >= 0
                || status === "connected"
                || status === "ready"
    }

    function aiStatusText() {
        if (root.readyConnections.length > 0)
            return "AI 服务已就绪"
        if (root.hasSavedProvider)
            return "AI 尚未验证 · 本地功能可用"
        return app.aiStatus || "AI 未连接 · 本地功能可用"
    }

    function beginMessage() {
        var message = prompt.text.trim()
        if (!message.length || root.awaitingResponse)
            return ""
        transcript.text += "\n你：" + message + "\n\nAI："
        prompt.text = ""
        root.awaitingResponse = true
        root.inlineError = false
        root.inlineStatus = "正在生成回答……"
        return message
    }

    function finishMessage(message, failed) {
        if (!root.awaitingResponse)
            return
        root.awaitingResponse = false
        root.inlineError = failed
        root.inlineStatus = message
    }

    function refreshPreview() {
        var modeId = mode.currentValue || "coach"
        root.preview = app.practiceContextPreview(
            modeId,
            modeId === "teacher" ? helpLevel.currentText : "",
            includeSubmission.checked,
            includeTestOutput.checked
        )
    }

    RowLayout {
        anchors.fill: parent; anchors.margins: 26; spacing: 16
        LabCard {
            Layout.preferredWidth: 330; Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            ScrollView {
                id: contextScroll
                width: parent.width
                height: parent.height
                clip: true
                contentWidth: availableWidth
                ScrollBar.vertical: ScrollBar {
                    width: 6
                    anchors.right: parent.right
                    policy: ScrollBar.AlwaysOn
                    visible: contextScroll.contentHeight > contextScroll.height
                    contentItem: Rectangle {
                        implicitWidth: 5
                        radius: 3
                        color: root.palette.muted
                        opacity: 0.45
                    }
                }
                Column {
                    id: contextColumn
                    width: contextScroll.availableWidth
                    spacing: 10
                    Text { width: parent.width; text: "上下文预览（只读）"; color: root.palette.text; font.pixelSize: 19; font.bold: true }
                    Text { width: parent.width; text: "只有你在上方选择、并在清单中标为“将发送”的内容会发送给远程 AI；应用不会自动附加整个个人工作区。"; color: root.palette.muted; wrapMode: Text.Wrap }
                    ComboBox {
                        id: mode; width: parent.width
                        model: [{id:"coach", label:"教练"}, {id:"teacher", label:"讲解"}, {id:"reviewer", label:"审查"}]
                        textRole: "label"; valueRole: "id"; onCurrentValueChanged: root.refreshPreview()
                    }
                    ComboBox { id: helpLevel; width: parent.width; visible: mode.currentValue === "teacher"; model: ["H1", "H2", "H3"]; currentIndex: 1; onCurrentTextChanged: root.refreshPreview() }
                    CheckBox { id: includeSubmission; width: parent.width; text: "包含当前答案"; onCheckedChanged: root.refreshPreview() }
                    CheckBox { id: includeTestOutput; width: parent.width; text: "包含最近一次公开测试摘要"; checked: true; onCheckedChanged: root.refreshPreview() }
                    Button { width: parent.width; text: "刷新预览"; onClicked: root.refreshPreview() }
                    Rectangle {
                        visible: contextScroll.contentHeight > contextScroll.height
                        width: parent.width
                        height: visible ? 30 : 0
                        radius: 6
                        color: root.palette.surfaceAlt
                        Text {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            text: "上下文清单共 " + (root.preview.parts || []).length + " 项 · 向下滚动查看全部"
                            color: root.palette.muted
                            font.pixelSize: 11
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                    }
                    Repeater {
                        model: root.preview.parts || []
                        delegate: RowLayout {
                            required property var modelData
                            width: contextColumn.width
                            StatusPill {
                                text: modelData.selected ? "将发送" : "不发送"
                                tone: modelData.selected ? root.palette.accent : root.palette.muted
                            }
                            Text { text: modelData.label; color: root.palette.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
                            StatusPill { visible: modelData.sensitive; text: "敏感内容"; tone: root.palette.warning }
                        }
                    }
                    Text { width: parent.width; text: "预计上下文：" + (root.preview.estimated_tokens || 0) + " tokens"; color: root.palette.muted; font.pixelSize: 12 }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { width: parent.width; text: "AI 是教练和审查者，不是掌握状态的最终裁决者。"; color: root.palette.warning; wrapMode: Text.Wrap; font.bold: true }
                    Item { width: parent.width; height: 8 }
                }
            }
        }

        LabCard {
            Layout.fillWidth: true
            // The offline state is a compact call to action, not a transcript
            // canvas.  Let the card size to that state so a disconnected AI
            // does not leave a large empty panel beside the context preview.
            Layout.fillHeight: root.aiAvailable
            Layout.alignment: Qt.AlignTop
            cardColor: root.palette.surface; borderColor: root.palette.border
            RowLayout {
                width: parent.width
                Text { text: "使用你自己的 AI"; color: root.palette.text; font.pixelSize: 19; font.bold: true }
                Item { Layout.fillWidth: true }
                StatusPill {
                    text: root.aiStatusText()
                    tone: root.aiAvailable ? root.palette.success : root.palette.muted
                }
            }
            Rectangle {
                id: transcriptPanel
                width: parent.width
                height: Math.max(120, parent.height - (root.inlineStatus.length ? 214 : 190))
                radius: 8
                color: root.palette.surfaceAlt
                visible: root.aiAvailable
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 14
                    contentWidth: width
                    contentHeight: transcript.implicitHeight
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    Text { id: transcript; width: parent.width; text: "请选择一个已保存的 AI 服务，或连接 Codex。刷题训练不要求连接 AI。\n\n"; color: root.palette.text; wrapMode: Text.Wrap }
                }
            }
            Item {
                id: noAiState
                width: parent.width
                height: root.aiAvailable ? 0 : 218
                visible: !root.aiAvailable
                Rectangle {
                    anchors.fill: parent
                    radius: 8
                    color: root.palette.surfaceAlt
                    border.color: root.palette.border
                }
                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 48, 420)
                    spacing: 8
                    Text {
                        text: root.hasSavedProvider ? "AI 尚未验证" : "当前未连接 AI"
                        color: root.palette.text
                        font.pixelSize: 18
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Text {
                        text: root.hasSavedProvider
                              ? "已保存的 AI 服务尚未通过连接测试。请先前往 AI 连接页完成测试；在此之前，固定课程、公开测试和手动模拟面试仍可离线完成。"
                              : "固定课程、公开测试和手动模拟面试都可以离线完成。连接 AI 后，可在这里请求提示和只读审查。"
                        color: root.palette.muted
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Button {
                        id: openConnectionsButton
                        objectName: "coachOpenConnections"
                        text: "前往 AI 连接"
                        Layout.preferredWidth: 142
                        Layout.preferredHeight: 42
                        Layout.alignment: Qt.AlignLeft
                        background: Rectangle {
                            radius: 8
                            color: root.palette.accent
                        }
                        contentItem: Text {
                            text: openConnectionsButton.text
                            color: "white"
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: app.navigate("connections")
                    }
                }
            }
            TextArea {
                id: prompt
                visible: root.aiAvailable
                width: parent.width
                height: 92
                enabled: !root.awaitingResponse
                placeholderText: root.awaitingResponse ? "正在等待 AI 回答……" : "请求限定范围的解释、分级提示或代码审查……"
                wrapMode: Text.Wrap
                background: Rectangle { color: root.palette.background; radius: 8; border.color: root.palette.border }
            }
            Text {
                visible: root.aiAvailable && root.inlineStatus.length > 0
                width: parent.width
                text: root.inlineStatus
                color: root.inlineError ? root.palette.danger : (root.awaitingResponse ? root.palette.accent : root.palette.muted)
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }
            RowLayout {
                visible: root.aiAvailable
                width: parent.width
                ComboBox {
                    id: connection
                    visible: root.readyConnections.length > 0
                    Layout.fillWidth: visible
                    textRole: "display_name"
                    valueRole: "connection_id"
                    model: root.readyConnections
                }
                Button {
                    visible: root.readyConnections.length > 0
                    text: "发送预览内容"
                    enabled: connection.count > 0 && prompt.text.trim().length > 0 && !app.busy && !root.awaitingResponse
                    onClicked: {
                        var message = root.beginMessage()
                        if (message.length) {
                            app.sendProviderPracticeMessage(
                                connection.currentValue, message, mode.currentValue,
                                mode.currentValue === "teacher" ? helpLevel.currentText : "",
                                includeSubmission.checked, includeTestOutput.checked
                            )
                        }
                    }
                }
                Button {
                    visible: app.codexAvailable && !root.codexReady()
                    text: "连接 Codex"
                    onClicked: app.connectCodex(mode.currentValue === "reviewer" ? "reviewer" : "coach")
                }
                Button {
                    visible: root.codexReady()
                    text: "发送给 Codex"
                    enabled: prompt.text.trim().length > 0 && !root.awaitingResponse
                    onClicked: {
                        var message = root.beginMessage()
                        if (message.length) {
                            app.sendCodexPracticeMessage(
                                message, mode.currentValue,
                                mode.currentValue === "teacher" ? helpLevel.currentText : "",
                                includeSubmission.checked, includeTestOutput.checked
                            )
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: app
        function onAiDelta(text) {
            transcript.text += text
            if (root.awaitingResponse) {
                root.inlineError = false
                root.inlineStatus = "正在接收回答……"
            }
        }
        function onAiStateChanged() {
            if (root.awaitingResponse && root.codexReady())
                root.finishMessage("回答完成。请核对内容后再决定下一步。", false)
        }
        function onToast(message) {
            if (!root.awaitingResponse)
                return
            if (message === "AI 回答完成。")
                root.finishMessage("回答完成。请核对内容后再决定下一步。", false)
            else
                root.finishMessage(message, true)
        }
    }
    Component.onCompleted: root.refreshPreview()
}
