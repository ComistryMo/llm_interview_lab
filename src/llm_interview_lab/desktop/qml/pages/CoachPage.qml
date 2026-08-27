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
        root.preview = app.practiceContextPreview(
            mode.currentText,
            mode.currentText === "teacher" ? helpLevel.currentText : "",
            includeSubmission.checked,
            includeTestOutput.checked
        )
    }

    RowLayout {
        anchors.fill: parent; anchors.margins: 26; spacing: 16
        LabCard {
            Layout.preferredWidth: 320; Layout.fillHeight: true; cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "Context Preview"; color: root.palette.text; font.pixelSize: 19; font.bold: true }
            Text { width: parent.width; text: "Only checked, visible context is sent to a remote provider. The whole Workspace is never attached automatically."; color: root.palette.muted; wrapMode: Text.Wrap }
            ComboBox { id: mode; width: parent.width; model: ["coach", "teacher", "reviewer"]; onCurrentTextChanged: root.refreshPreview() }
            ComboBox { id: helpLevel; width: parent.width; visible: mode.currentText === "teacher"; model: ["H1", "H2", "H3"]; currentIndex: 1; onCurrentTextChanged: root.refreshPreview() }
            CheckBox { id: includeSubmission; text: "Include current submission"; onCheckedChanged: root.refreshPreview() }
            CheckBox { id: includeTestOutput; text: "Include latest public test summary"; checked: true; onCheckedChanged: root.refreshPreview() }
            Button { width: parent.width; text: "Refresh preview"; onClicked: root.refreshPreview() }
            Repeater {
                model: root.preview.parts || []
                delegate: RowLayout {
                    required property var modelData
                    width: parent.width
                    CheckBox { checked: modelData.selected; enabled: false }
                    Text { text: modelData.label; color: root.palette.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    StatusPill { visible: modelData.sensitive; text: "private"; tone: root.palette.warning }
                }
            }
            Text { text: "Estimated context: " + (root.preview.estimated_tokens || 0) + " tokens"; color: root.palette.muted; font.pixelSize: 12 }
            Item { Layout.fillHeight: true }
            Text { width: parent.width; text: "AI is a coach and reviewer—not the final mastery authority."; color: root.palette.warning; wrapMode: Text.Wrap; font.bold: true }
        }

        LabCard {
            Layout.fillWidth: true; Layout.fillHeight: true; cardColor: root.palette.surface; borderColor: root.palette.border
            RowLayout {
                width: parent.width
                Text { text: "Bring Your Own AI"; color: root.palette.text; font.pixelSize: 19; font.bold: true }
                Item { Layout.fillWidth: true }
                StatusPill { text: app.aiStatus; tone: root.palette.muted }
            }
            Rectangle {
                width: parent.width; Layout.fillHeight: true; radius: 8; color: root.palette.surfaceAlt
                ScrollView { anchors.fill: parent; anchors.margins: 14; Text { id: transcript; width: parent.width; text: "Choose a saved provider or connect Codex. No AI is required for Practice.\n\n"; color: root.palette.text; wrapMode: Text.Wrap } }
            }
            TextArea { id: prompt; width: parent.width; height: 92; placeholderText: "Ask for a bounded explanation, hint, or review…"; wrapMode: Text.Wrap; background: Rectangle { color: root.palette.background; radius: 8; border.color: root.palette.border } }
            RowLayout {
                width: parent.width
                ComboBox { id: connection; Layout.fillWidth: true; textRole: "display_name"; valueRole: "connection_id"; model: app.connections }
                Button {
                    text: "Send visible context"
                    enabled: connection.count > 0 && prompt.text.trim().length > 0 && !app.busy
                    onClicked: app.sendProviderPracticeMessage(
                        connection.currentValue,
                        prompt.text,
                        mode.currentText,
                        mode.currentText === "teacher" ? helpLevel.currentText : "",
                        includeSubmission.checked,
                        includeTestOutput.checked
                    )
                }
                Button { text: "Connect Codex"; enabled: app.codexAvailable; onClicked: app.connectCodex(mode.currentText === "reviewer" ? "reviewer" : "coach") }
                Button {
                    text: "Send visible context to Codex"
                    enabled: app.aiStatus.indexOf("connected") >= 0 && prompt.text.trim().length > 0
                    onClicked: app.sendCodexPracticeMessage(
                        prompt.text,
                        mode.currentText,
                        mode.currentText === "teacher" ? helpLevel.currentText : "",
                        includeSubmission.checked,
                        includeTestOutput.checked
                    )
                }
            }
        }
    }

    Connections {
        target: app
        function onAiDelta(text) { transcript.text += text }
    }
    Component.onCompleted: root.refreshPreview()
}
