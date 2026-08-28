import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
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
        x: 28
        y: 24
        width: parent.width - 56
        spacing: 16

        Text { text: "Private career evidence"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
        Text {
            Layout.fillWidth: true
            text: "Keep resumes, role intent, projects, papers, competitions, past interview questions and job descriptions in this Git-ignored Profile. Files are never read merely because they exist."
            color: root.palette.muted
            wrapMode: Text.Wrap
        }

        LabCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 238
            cardColor: root.palette.surface
            borderColor: root.palette.border
            Text { text: "Add one explicit file"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: 12
                rowSpacing: 10
                ComboBox {
                    id: materialKind
                    Layout.fillWidth: true
                    model: ["resume", "career_intent", "internship", "project", "paper", "competition", "interview_question", "job_description", "portfolio", "other"]
                }
                TextField { id: materialTitle; Layout.fillWidth: true; placeholderText: "Title (optional)" }
                TextField { id: selectedPath; Layout.fillWidth: true; readOnly: true; placeholderText: "Choose .md, .txt, .json, .yaml, .pdf or .docx" }
                Button { text: "Choose file"; onClicked: filePicker.open() }
            }
            CheckBox {
                id: aiAccess
                text: "Allow this UTF-8 text file to be selected for AI context"
            }
            RowLayout {
                width: parent.width
                Text {
                    Layout.fillWidth: true
                    text: "PDF/DOCX remain opaque and cannot be sent to AI. Consent is requested again for each interview."
                    color: root.palette.muted
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
                Button {
                    text: "Copy into Profile"
                    highlighted: true
                    enabled: selectedPath.text.length > 0
                    onClicked: {
                        app.addMaterial(filePicker.selectedFile.toString(), materialKind.currentText, materialTitle.text, aiAccess.checked)
                        materialTitle.text = ""
                        selectedPath.text = ""
                        aiAccess.checked = false
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "Material manifest"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            Item { Layout.fillWidth: true }
            Text { text: app.materials.length + " local records"; color: root.palette.muted }
        }

        LabCard {
            visible: app.materials.length === 0
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            cardColor: root.palette.surface
            borderColor: root.palette.border
            Text { text: "No material has been added to this Profile."; color: root.palette.text; font.bold: true }
            Text { text: "You can still use every fixed course and catalog-only interview."; color: root.palette.muted }
        }

        Repeater {
            model: app.materials
            delegate: LabCard {
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: 136
                cardColor: root.palette.surface
                borderColor: root.palette.border
                RowLayout {
                    width: parent.width
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 16 }
                        Text { text: modelData.id + " · " + modelData.kind; color: root.palette.accent }
                    }
                    StatusPill {
                        text: modelData.ai_access ? "AI eligible" : "Local only"
                        tone: modelData.ai_access ? root.palette.warning : root.palette.muted
                    }
                }
                Text {
                    width: parent.width
                    text: "SHA-256  " + modelData.sha256
                    color: root.palette.muted
                    font.family: "Cascadia Mono"
                    font.pixelSize: 11
                    wrapMode: Text.WrapAnywhere
                }
                Text { text: "Content is not previewed or uploaded automatically."; color: root.palette.muted; font.pixelSize: 12 }
            }
        }
    }

    FileDialog {
        id: filePicker
        title: "Choose one career material"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Supported files (*.md *.txt *.json *.yaml *.yml *.pdf *.docx)"]
        onAccepted: selectedPath.text = selectedFile.toString()
    }
}
