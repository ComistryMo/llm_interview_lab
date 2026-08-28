import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Text { text: "Recommended role path"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
                Text { text: "Quest order is guidance; prerequisites are the hard DAG."; color: root.palette.muted }
            }
            Item { Layout.fillWidth: true }
            ComboBox { model: ["Recommended", "All ready", "Advanced graph"] }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10
            clip: true
            model: app.problems
            delegate: LabCard {
                required property var modelData
                width: list.width
                height: 104
                cardColor: root.palette.surface
                borderColor: root.palette.border
                RowLayout {
                    width: parent.width; height: parent.height; spacing: 16
                    Rectangle {
                        width: 38; height: 38; radius: 19
                        color: modelData.status === "mastered" ? Qt.rgba(0.09,0.52,0.36,0.15) : root.palette.surfaceAlt
                        Text { anchors.centerIn: parent; text: modelData.status === "mastered" ? "✓" : (index + 1); color: modelData.status === "mastered" ? root.palette.success : root.palette.muted; font.bold: true }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Text { text: modelData.problem_id + "  " + modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 16 }
                        Text { text: modelData.prerequisites && modelData.prerequisites.length ? "Requires " + modelData.prerequisites.join(", ") : "Foundation node"; color: root.palette.muted; font.pixelSize: 12 }
                        RowLayout {
                            StatusPill { text: modelData.validation; tone: modelData.validation === "oracle" ? root.palette.success : root.palette.warning }
                            StatusPill { text: modelData.retention ? "D+2 / D+7" : "No retention"; tone: modelData.retention ? root.palette.accent : root.palette.muted }
                        }
                    }
                    Button { text: modelData.locked ? "Locked" : (modelData.status === "in_progress" ? "Continue" : "Open"); enabled: !modelData.locked && modelData.asset_status !== "planned"; onClicked: app.openProblem(modelData.problem_id) }
                }
            }
        }
    }
}
