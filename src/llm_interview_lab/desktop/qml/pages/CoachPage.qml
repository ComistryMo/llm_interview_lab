import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property var preview: ({"parts": [], "estimated_tokens": 0})
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
            Text { text: "上下文预览"; color: root.palette.text; font.pixelSize: 19; font.bold: true }
            Text { width: parent.width; text: "只有勾选且可见的内容会发送给远程 AI；应用不会自动附加整个个人工作区。"; color: root.palette.muted; wrapMode: Text.Wrap }
            ComboBox {
                id: mode; width: parent.width
                model: [{id:"coach", label:"教练"}, {id:"teacher", label:"讲解"}, {id:"reviewer", label:"审查"}]
                textRole: "label"; valueRole: "id"; onCurrentValueChanged: root.refreshPreview()
            }
            ComboBox { id: helpLevel; width: parent.width; visible: mode.currentValue === "teacher"; model: ["H1", "H2", "H3"]; currentIndex: 1; onCurrentTextChanged: root.refreshPreview() }
            CheckBox { id: includeSubmission; text: "包含当前答案"; onCheckedChanged: root.refreshPreview() }
            CheckBox { id: includeTestOutput; text: "包含最近一次公开测试摘要"; checked: true; onCheckedChanged: root.refreshPreview() }
            Button { width: parent.width; text: "刷新预览"; onClicked: root.refreshPreview() }
            Repeater {
                model: root.preview.parts || []
                delegate: RowLayout {
                    required property var modelData
                    width: parent.width
                    CheckBox { checked: modelData.selected; enabled: false }
                    Text { text: modelData.label; color: root.palette.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    StatusPill { visible: modelData.sensitive; text: "敏感内容"; tone: root.palette.warning }
                }
            }
            Text { text: "预计上下文：" + (root.preview.estimated_tokens || 0) + " tokens"; color: root.palette.muted; font.pixelSize: 12 }
            Item { Layout.fillHeight: true }
            Text { width: parent.width; text: "AI 是教练和审查者，不是掌握状态的最终裁决者。"; color: root.palette.warning; wrapMode: Text.Wrap; font.bold: true }
        }

        LabCard {
            Layout.fillWidth: true; Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            RowLayout {
                width: parent.width
                Text { text: "使用你自己的 AI"; color: root.palette.text; font.pixelSize: 19; font.bold: true }
                Item { Layout.fillWidth: true }
                StatusPill { text: app.aiStatus; tone: root.palette.muted }
            }
            Rectangle {
                width: parent.width; Layout.fillHeight: true; radius: 8; color: root.palette.surfaceAlt
                ScrollView { anchors.fill: parent; anchors.margins: 14; Text { id: transcript; width: parent.width; text: "请选择一个已保存的 AI 服务，或连接 Codex。刷题训练不要求连接 AI。\n\n"; color: root.palette.text; wrapMode: Text.Wrap } }
            }
            TextArea { id: prompt; width: parent.width; height: 92; placeholderText: "请求限定范围的解释、分级提示或代码审查……"; wrapMode: Text.Wrap; background: Rectangle { color: root.palette.background; radius: 8; border.color: root.palette.border } }
            RowLayout {
                width: parent.width
                ComboBox { id: connection; Layout.fillWidth: true; textRole: "display_name"; valueRole: "connection_id"; model: app.connections }
                Button {
                    text: "发送预览内容"
                    enabled: connection.count > 0 && prompt.text.trim().length > 0 && !app.busy
                    onClicked: app.sendProviderPracticeMessage(
                        connection.currentValue, prompt.text, mode.currentValue,
                        mode.currentValue === "teacher" ? helpLevel.currentText : "",
                        includeSubmission.checked, includeTestOutput.checked
                    )
                }
                Button { text: "连接 Codex"; enabled: app.codexAvailable; onClicked: app.connectCodex(mode.currentValue === "reviewer" ? "reviewer" : "coach") }
                Button {
                    text: "发送给 Codex"
                    enabled: (app.aiStatus.indexOf("已连接") >= 0 || app.aiStatus.indexOf("就绪") >= 0) && prompt.text.trim().length > 0
                    onClicked: app.sendCodexPracticeMessage(
                        prompt.text, mode.currentValue,
                        mode.currentValue === "teacher" ? helpLevel.currentText : "",
                        includeSubmission.checked, includeTestOutput.checked
                    )
                }
            }
        }
    }

    Connections { target: app; function onAiDelta(text) { transcript.text += text } }
    Component.onCompleted: root.refreshPreview()
}
