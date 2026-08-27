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

    ColumnLayout {
        id: content
        x: 28; y: 24; width: parent.width - 56; spacing: 16
        Text { text: "Optional AI connections"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
        Text { text: "Practice and manual interviews work without AI. Remote calls send only the Context Preview."; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }

        RowLayout {
            Layout.fillWidth: true; spacing: 14
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 170; cardColor: root.palette.surface; borderColor: root.palette.border
                RowLayout {
                    width: parent.width
                    Text { text: "Codex"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                    Item { Layout.fillWidth: true }
                    StatusPill { text: app.codexAvailable ? "Available" : "Not found"; tone: app.codexAvailable ? root.palette.success : root.palette.muted }
                }
                Text { width: parent.width; text: "Official App Server integration: threads, streaming events, diff, cancel and explicit command/file approvals."; color: root.palette.muted; wrapMode: Text.Wrap }
                RowLayout {
                    width: parent.width
                    Button { text: "Coach"; enabled: app.codexAvailable; onClicked: app.connectCodex("coach") }
                    Button { text: "Repository Agent"; enabled: app.codexAvailable; onClicked: app.connectCodex("repository_agent") }
                }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 170; cardColor: root.palette.surface; borderColor: root.palette.border
                Text { text: "No AI"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                Text { width: parent.width; text: "The default. Catalog, grader, review, retention and manual interview remain deterministic and local."; color: root.palette.muted; wrapMode: Text.Wrap }
                StatusPill { text: "Always available"; tone: root.palette.success }
            }
        }

        LabCard {
            Layout.fillWidth: true; Layout.preferredHeight: 310; cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "Add or update a provider"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            GridLayout {
                width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 10
                TextField { id: connectionId; Layout.fillWidth: true; placeholderText: "Connection ID (for example openai-main)" }
                ComboBox { id: provider; Layout.fillWidth: true; model: ["openai", "openai-compatible", "anthropic", "gemini", "ollama"] }
                TextField { id: displayName; Layout.fillWidth: true; placeholderText: "Display name" }
                TextField { id: model; Layout.fillWidth: true; placeholderText: "Model ID" }
                TextField { id: endpoint; Layout.fillWidth: true; placeholderText: "Endpoint (compatible / Ollama only)" }
                TextField { id: apiKey; Layout.fillWidth: true; placeholderText: "API key (system keyring)"; echoMode: TextInput.Password }
            }
            RowLayout {
                width: parent.width
                Text { text: "Plaintext keys are never written to Profile files."; color: root.palette.muted; font.pixelSize: 12; Layout.fillWidth: true }
                Button { text: "Save connection"; highlighted: true; onClicked: { app.saveConnection(connectionId.text, provider.currentText, model.text, displayName.text, endpoint.text, apiKey.text); apiKey.text = "" } }
            }
        }

        Text { text: "Saved connections"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
        Repeater {
            model: app.connections
            delegate: LabCard {
                required property var modelData
                Layout.fillWidth: true; Layout.preferredHeight: 94; cardColor: root.palette.surface; borderColor: root.palette.border
                RowLayout {
                    width: parent.width; height: parent.height
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.display_name; color: root.palette.text; font.bold: true }
                        Text { text: modelData.provider_id + " · " + modelData.model; color: root.palette.muted }
                    }
                    StatusPill { text: modelData.status || "Saved"; tone: root.palette.muted }
                    Button { text: "Test"; flat: true; onClicked: app.testConnection(modelData.connection_id) }
                    Button { text: "Delete"; flat: true; onClicked: app.deleteConnection(modelData.connection_id) }
                }
            }
        }

        LabCard {
            visible: !!root.pendingApproval.request_id
            Layout.fillWidth: true; Layout.preferredHeight: root.pendingApproval.diff ? 390 : 260; cardColor: root.palette.surface; borderColor: root.palette.warning
            Text { text: "Codex approval required"; color: root.palette.warning; font.pixelSize: 18; font.bold: true }
            Text { width: parent.width; text: "Action: " + (root.pendingApproval.action || "") + "\nScope: " + (root.pendingApproval.scope || "") + "\nFiles: " + ((root.pendingApproval.files || []).join ? root.pendingApproval.files.join(", ") : root.pendingApproval.files || "") + "\nCommand: " + (root.pendingApproval.command || "") + "\nReason: " + (root.pendingApproval.reason || "") + "\nRisk: " + (root.pendingApproval.risk || ""); color: root.palette.text; wrapMode: Text.Wrap }
            ScrollView {
                visible: !!root.pendingApproval.diff
                width: parent.width; Layout.fillHeight: true; clip: true
                TextArea {
                    text: root.pendingApproval.diff || ""
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.NoWrap
                    font.family: "Cascadia Mono, Consolas, monospace"
                    color: root.palette.text
                    background: Rectangle { color: root.palette.surfaceAlt; radius: 6; border.color: root.palette.border }
                    Accessible.name: "Proposed Codex diff"
                }
            }
            RowLayout {
                Button { text: "Reject"; onClicked: { app.resolveCodexApproval(root.pendingApproval.request_id, "decline"); root.pendingApproval = ({}) } }
                Button { text: "Approve once"; highlighted: true; onClicked: { app.resolveCodexApproval(root.pendingApproval.request_id, "accept"); root.pendingApproval = ({}) } }
            }
        }
    }

    Connections {
        target: app
        function onCodexApproval(value) { root.pendingApproval = value }
    }
}
