import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 30; spacing: 16
        Text { text: "Appearance and local behavior"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
        LabCard {
            Layout.fillWidth: true; Layout.preferredHeight: 210; cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "Theme"; color: root.palette.text; font.bold: true }
            RowLayout {
                width: parent.width
                Repeater {
                    model: ["system", "light", "dark"]
                    delegate: Button { required property string modelData; text: modelData; checkable: true; checked: app.theme === modelData; onClicked: app.setTheme(modelData) }
                }
            }
            Text { text: "Text size"; color: root.palette.text; font.bold: true }
            RowLayout {
                width: parent.width
                Slider { from: 0.85; to: 1.4; value: app.fontScale; stepSize: 0.05; Layout.fillWidth: true; onMoved: app.setFontScale(value) }
                Text { text: Math.round(app.fontScale * 100) + "%"; color: root.palette.muted }
            }
        }
        LabCard {
            Layout.fillWidth: true; Layout.preferredHeight: 190; cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "Local-first boundaries"; color: root.palette.text; font.bold: true; font.pixelSize: 18 }
            Text { width: parent.width; text: "Profile and submissions stay under workspace/profiles/<id>/ and are ignored by Git. The app has no telemetry, account system, server, or cloud sync. The local grader executes code you trust; it is not a hostile-code sandbox."; color: root.palette.muted; wrapMode: Text.Wrap }
            Button { text: "Refresh local state"; onClicked: app.refresh() }
        }
        Item { Layout.fillHeight: true }
        Text { text: "LLM Interview Lab · role-aware Windows Desktop Alpha"; color: root.palette.muted; font.pixelSize: 12 }
    }
}
