import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    contentWidth: width; contentHeight: content.implicitHeight + 50; clip: true

    ColumnLayout {
        id: content
        x: 28; y: 26; width: parent.width - 56; spacing: 16
        Text { text: "Evidence, not activity streaks"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
        Text { text: "Practice mastery, retention, and interview evidence remain separate and inspectable."; color: root.palette.muted }
        RowLayout {
            Layout.fillWidth: true; spacing: 14
            Repeater {
                model: [
                    {label:"Mastered problems", value: app.dashboard.mastered_count || 0},
                    {label:"Retention due", value: app.dashboard.due_retention ? app.dashboard.due_retention.length : 0},
                    {label:"Reviews due", value: app.dashboard.due_review ? app.dashboard.due_review.length : 0}
                ]
                delegate: LabCard {
                    required property var modelData
                    Layout.fillWidth: true; Layout.preferredHeight: 132; cardColor: root.palette.surface; borderColor: root.palette.border
                    Text { text: modelData.label; color: root.palette.muted }
                    Text { text: modelData.value; color: root.palette.text; font.pixelSize: 32; font.bold: true }
                }
            }
        }
        LabCard {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(260, (app.dashboard.role_readiness ? app.dashboard.role_readiness.length : 0) * 58 + 92)
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "Role readiness by skill domain"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            Text { text: "Self-assessment is shown separately from verified evidence."; color: root.palette.muted; font.pixelSize: 12 }
            Repeater {
                model: app.dashboard.role_readiness || []
                delegate: RowLayout {
                    required property var modelData
                    width: parent.width
                    Text { text: modelData.label; color: root.palette.text; Layout.preferredWidth: 170 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Text { text: "Verified"; color: root.palette.muted; font.pixelSize: 10; Layout.preferredWidth: 70 }
                            ProgressBar { Layout.fillWidth: true; value: modelData.verified }
                            Text { text: Math.round(modelData.verified * 100) + "%"; color: root.palette.muted; Layout.preferredWidth: 42 }
                        }
                        RowLayout {
                            Text { text: "Self-report"; color: root.palette.muted; font.pixelSize: 10; Layout.preferredWidth: 70 }
                            ProgressBar { Layout.fillWidth: true; value: modelData.self_reported }
                            Text { text: Math.round(modelData.self_reported * 100) + "%"; color: root.palette.muted; Layout.preferredWidth: 42 }
                        }
                    }
                }
            }
            Text { visible: !app.dashboard.role_readiness || app.dashboard.role_readiness.length === 0; text: "Choose a Role during onboarding to build this local view."; color: root.palette.muted }
        }
        LabCard {
            Layout.fillWidth: true; Layout.preferredHeight: 140; cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "Interpretation"; color: root.palette.text; font.bold: true }
            Text { width: parent.width; text: "Role readiness is a local planning indicator built from available evidence. It is not an offer probability, hiring decision, or substitute for real interviews."; color: root.palette.muted; wrapMode: Text.Wrap }
        }
    }
}
