import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property bool coachOpen: true

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Rectangle {
            SplitView.preferredWidth: 330
            SplitView.minimumWidth: 260
            color: root.palette.surface
            border.color: root.palette.border
            ScrollView {
                id: detailsScroll
                anchors.fill: parent; anchors.margins: 20; clip: true
                Column {
                    id: detailsColumn
                    width: detailsScroll.availableWidth; spacing: 12
                    Text { width: parent.width; text: app.currentTask.problem_id || "No active task"; color: root.palette.accent; font.bold: true; font.pixelSize: 12 }
                    Text { width: parent.width; text: app.currentTask.title || "Choose an exercise"; color: root.palette.text; font.pixelSize: 21; font.bold: true; wrapMode: Text.Wrap }
                    StatusPill { text: app.currentTask.validation || "not started"; tone: root.palette.success }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { width: parent.width; text: app.currentTask.task || "Open an unlocked problem from Learn."; color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; lineHeight: 1.25 }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { text: "Lifecycle"; color: root.palette.text; font.bold: true }
                    Button { width: detailsColumn.width; text: "Contract + oral review"; onClicked: reviewDialog.open() }
                    Row {
                        width: detailsColumn.width; spacing: 8
                        Button { width: (parent.width - 8) / 2; text: "D+2"; onClicked: app.startRetentionStage("d2") }
                        Button { width: (parent.width - 8) / 2; text: "D+7"; onClicked: app.startRetentionStage("d7") }
                    }
                }
            }
        }

        Rectangle {
            SplitView.fillWidth: true
            SplitView.minimumWidth: 420
            color: root.palette.background
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "submission.py"; color: root.palette.text; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Button { text: "Save"; flat: true; onClicked: app.saveSubmission(editor.text) }
                    Button { text: "Test"; highlighted: true; enabled: !app.busy; onClicked: { app.saveSubmission(editor.text); app.runTests() } }
                    Button { text: "Submit"; enabled: !app.busy; onClicked: app.submitCurrent() }
                }
                TextArea {
                    id: editor
                    Layout.fillWidth: true; Layout.fillHeight: true
                    text: app.submissionText
                    color: root.palette.text
                    selectionColor: root.palette.accent
                    font.family: "Cascadia Mono, Consolas, monospace"
                    font.pixelSize: 14
                    wrapMode: TextEdit.NoWrap
                    tabStopDistance: 32
                    padding: 12
                    clip: true
                    background: Rectangle { color: root.palette.surface; radius: 9; border.color: root.palette.border }
                    Accessible.name: "Submission editor"
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 154; radius: 9
                    color: root.palette.surface; border.color: root.palette.border
                    ScrollView {
                        anchors.fill: parent; anchors.margins: 12; clip: true
                        Text { width: parent.width; text: app.testOutput || "Test output appears here."; color: root.palette.text; font.family: "Cascadia Mono, Consolas, monospace"; font.pixelSize: 12; wrapMode: Text.Wrap }
                    }
                }
                Text { text: "Public tests passing is implementation evidence—not mastery."; color: root.palette.warning; font.pixelSize: 12; font.bold: true }
            }
        }

        Rectangle {
            visible: root.coachOpen
            SplitView.preferredWidth: root.coachOpen ? 310 : 0
            SplitView.minimumWidth: root.coachOpen ? 270 : 0
            color: root.palette.surface
            border.color: root.palette.border
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "AI Coach"; color: root.palette.text; font.bold: true; font.pixelSize: 17 }
                    Item { Layout.fillWidth: true }
                    Button { text: "×"; flat: true; onClicked: root.coachOpen = false }
                }
                Text { text: "H0–H5 boundaries apply. The coach cannot silently edit this submission."; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; font.pixelSize: 12 }
                ComboBox { id: helpLevel; Layout.fillWidth: true; model: ["H1 · syntax/docs", "H2 · concept", "H3 · steps"] }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: root.palette.surfaceAlt; radius: 8
                    ScrollView { anchors.fill: parent; anchors.margins: 10; Text { id: coachTranscript; width: parent.width; color: root.palette.text; wrapMode: Text.Wrap; text: "Ask for a bounded hint or code review.\n" } }
                }
                TextArea { id: coachInput; Layout.fillWidth: true; Layout.preferredHeight: 76; placeholderText: "Ask about the current task…"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.background; radius: 8; border.color: root.palette.border } }
                CheckBox { id: shareSubmission; text: "Share submission in preview" }
                Button { text: "Preview context"; Layout.fillWidth: true; onClicked: app.navigate("coach") }
            }
        }
    }

    Button {
        visible: !root.coachOpen
        anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14
        text: "AI Coach"
        onClicked: root.coachOpen = true
    }

    Dialog {
        id: reviewDialog
        title: "Contract and oral review"
        modal: true
        anchors.centerIn: parent
        width: Math.min(620, parent.width - 48)
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: app.reviewCurrent(
            explanation.text,
            complexity.text,
            boundaries.text,
            contractPassed.checked,
            oralPassed.checked
        )
        ColumnLayout {
            width: parent.width; spacing: 10
            Text { text: "Review records evidence. It cannot skip D+2/D+7 or directly grant mastery."; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            TextArea { id: explanation; Layout.fillWidth: true; Layout.preferredHeight: 80; placeholderText: "Explain the implementation and invariants"; wrapMode: Text.Wrap }
            TextField { id: complexity; Layout.fillWidth: true; placeholderText: "Time and space complexity" }
            TextArea { id: boundaries; Layout.fillWidth: true; Layout.preferredHeight: 70; placeholderText: "Boundary cases, errors, and non-mutation"; wrapMode: Text.Wrap }
            RowLayout {
                CheckBox { id: contractPassed; text: "Contract review passed" }
                CheckBox { id: oralPassed; text: "Oral defense passed" }
            }
        }
    }
}
