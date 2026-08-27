import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    contentWidth: width
    contentHeight: content.implicitHeight + 56
    clip: true

    ColumnLayout {
        id: content
        x: 30; y: 28; width: parent.width - 60
        spacing: 18

        Text { text: "Continue where you left off"; color: root.palette.text; font.pixelSize: 25; font.bold: true }
        Text { text: "One current task, due reviews, and the next verified step."; color: root.palette.muted; font.pixelSize: 14 }

        LabCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 174
            cardColor: root.palette.surface
            borderColor: root.palette.border
            RowLayout {
                width: parent.width
                height: parent.height
                spacing: 20
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: app.dashboard.current ? "CURRENT TASK" : "NEXT TASK"; color: root.palette.accent; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.1 }
                    Text { text: app.dashboard.current ? app.dashboard.current.problem_id + "  " + app.dashboard.current.title : (app.dashboard.unlocks && app.dashboard.unlocks.length ? app.dashboard.unlocks[0].problem_id + "  " + app.dashboard.unlocks[0].title : "No task available"); color: root.palette.text; font.pixelSize: 23; font.bold: true }
                    Text { text: app.dashboard.current ? "Status: " + app.dashboard.current.status : "A validated exercise is ready to start."; color: root.palette.muted }
                    Item { Layout.fillHeight: true }
                    Text { text: "Public tests passed ≠ mastered"; color: root.palette.warning; font.pixelSize: 12; font.bold: true }
                }
                Button {
                    text: app.dashboard.current ? "Continue" : "Start"
                    highlighted: true
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 46
                    enabled: app.dashboard.current || (app.dashboard.unlocks && app.dashboard.unlocks.length)
                    onClicked: app.openProblem(app.dashboard.current ? app.dashboard.current.problem_id : app.dashboard.unlocks[0].problem_id)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 150; cardColor: root.palette.surface; borderColor: root.palette.border
                Text { text: "Target role"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.role ? (app.dashboard.role.title || app.dashboard.role.primary_role.replace(/_/g, " ")) : "Choose during onboarding"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                Text { text: app.dashboard.role ? app.dashboard.role.seniority : "new_grad"; color: root.palette.accent }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 150; cardColor: root.palette.surface; borderColor: root.palette.border
                Text { text: "Mastered"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.mastered_count || 0; color: root.palette.text; font.pixelSize: 32; font.bold: true }
                Text { text: "Verified nodes"; color: root.palette.muted }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 150; cardColor: root.palette.surface; borderColor: root.palette.border
                Text { text: "Retention due"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.due_retention ? app.dashboard.due_retention.length : 0; color: root.palette.text; font.pixelSize: 32; font.bold: true }
                Text { text: "D+2 / D+7 rewrites"; color: root.palette.muted }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "Recommended Quests"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            Item { Layout.fillWidth: true }
            Button { text: "View path"; flat: true; onClicked: app.navigate("learn") }
        }
        Repeater {
            model: app.dashboard.recommended_quests || []
            delegate: LabCard {
                required property var modelData
                Layout.fillWidth: true; Layout.preferredHeight: 82; cardColor: root.palette.surface; borderColor: root.palette.border
                RowLayout {
                    width: parent.width
                    Text { text: modelData.title; color: root.palette.text; font.bold: true; Layout.fillWidth: true }
                    Text { text: modelData.id; color: root.palette.muted; font.family: "monospace" }
                }
            }
        }
    }
}
