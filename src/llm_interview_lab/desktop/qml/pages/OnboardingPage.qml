import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    required property var app
    required property var palette
    color: root.palette.background
    property int step: 0
    property string selectedRole: app.roles.length ? app.roles[3].id : "ai_algorithm_research_engineer"
    property var selectedRoleCard: {
        for (var i = 0; i < app.roles.length; ++i)
            if (app.roles[i].id === selectedRole) return app.roles[i]
        return null
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 900)
        height: Math.min(parent.height - 60, 690)
        spacing: 18

        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                width: 42; height: 42; radius: 11; color: root.palette.accent
                Text { anchors.centerIn: parent; text: "LL"; color: "white"; font.bold: true }
            }
            ColumnLayout {
                spacing: 2
                Text { text: "Set up your local interview workbench"; color: root.palette.text; font.pixelSize: 25; font.bold: true }
                Text { text: "Four focused steps. You can change these choices later."; color: root.palette.muted; font.pixelSize: 14 }
            }
            Item { Layout.fillWidth: true }
            Text { text: (step + 1) + " / 4"; color: root.palette.muted; font.bold: true }
        }

        ProgressBar { Layout.fillWidth: true; value: (step + 1) / 4 }

        LabCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            cardColor: root.palette.surface
            borderColor: root.palette.border

            StackLayout {
                width: parent.width
                height: parent.height
                currentIndex: root.step

                ColumnLayout {
                    spacing: 16
                    Text { text: "Create a Profile"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "Your practice history, answers, interview reports and career materials stay in this local Profile."; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    TextField { id: profileName; Layout.fillWidth: true; placeholderText: "Profile name"; text: "default"; maximumLength: 64; focus: true }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 74; radius: 8; color: root.palette.surfaceAlt
                        Text { anchors.fill: parent; anchors.margins: 14; text: "Privacy default\nworkspace/profiles/<id>/ is ignored by Git. Connecting AI is optional."; color: root.palette.text; wrapMode: Text.Wrap }
                    }
                    Item { Layout.fillHeight: true }
                }

                ColumnLayout {
                    spacing: 12
                    Text { text: "Choose a target role"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "This changes skill weights, recommended Quests and interview Blueprints—not the public curriculum facts."; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        GridLayout {
                            width: parent.width
                            columns: 2
                            columnSpacing: 12; rowSpacing: 12
                            Repeater {
                                model: app.roles
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 104
                                    radius: 10
                                    color: root.selectedRole === modelData.id ? Qt.rgba(0.145, 0.388, 0.922, 0.12) : root.palette.surfaceAlt
                                    border.color: root.selectedRole === modelData.id ? root.palette.accent : root.palette.border
                                    border.width: root.selectedRole === modelData.id ? 2 : 1
                                    Column {
                                        anchors.fill: parent; anchors.margins: 13; spacing: 5
                                        Text { text: modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 15 }
                                        Text { width: parent.width; text: modelData.summary; color: root.palette.muted; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight }
                                    }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.selectedRole = modelData.id }
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    spacing: 16
                    Text { text: "Set a starting level"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "A lightweight self-assessment helps recommendations. It never grants mastery."; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Repeater {
                        id: assessmentRepeater
                        model: root.selectedRoleCard ? root.selectedRoleCard.top_skills : []
                        delegate: RowLayout {
                            required property var modelData
                            property string skillId: modelData.id
                            property int level: Math.round(levelSlider.value)
                            Layout.fillWidth: true
                            Text { text: modelData.title; color: root.palette.text; Layout.preferredWidth: 220; elide: Text.ElideRight }
                            Slider { id: levelSlider; Layout.fillWidth: true; from: 0; to: 4; stepSize: 1; value: 1 }
                            Text { text: "0  ·  1  ·  2  ·  3  ·  4"; color: root.palette.muted; font.pixelSize: 11 }
                        }
                    }
                    CheckBox { id: skipAssessment; text: "Skip and start from foundations"; checked: true }
                    ComboBox { id: seniority; Layout.preferredWidth: 220; model: ["intern", "new_grad", "mid", "senior"]; currentIndex: 1 }
                    Item { Layout.fillHeight: true }
                }

                ColumnLayout {
                    spacing: 16
                    Text { text: "Choose AI connection"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "No AI is the safe default. You can connect Codex or your own API later from Connections."; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    ButtonGroup { id: aiGroup }
                    Repeater {
                        model: [
                            {id:"disabled", title:"Use without AI", detail:"All curriculum, tests, retention and manual interviews remain available."},
                            {id:"provider", title:"Connect an LLM API later", detail:"Preview exactly what will be sent; keys stay in the system keyring."},
                            {id:"codex", title:"Connect Codex later", detail:"Use the official App Server with sandbox and explicit approvals."}
                        ]
                        delegate: RadioButton {
                            required property var modelData
                            required property int index
                            id: aiChoice
                            ButtonGroup.group: aiGroup
                            checked: index === 0
                            text: modelData.title + "\n" + modelData.detail
                            contentItem: Text { text: aiChoice.text; color: root.palette.text; leftPadding: 42; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter }
                            property string aiId: modelData.id
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 8; color: root.palette.surfaceAlt
                        Text { anchors.fill: parent; anchors.margins: 13; text: "Remote AI receives only the items visible in Context Preview. Never upload employer code or the whole Profile."; color: root.palette.text; wrapMode: Text.Wrap }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button { text: "Back"; enabled: root.step > 0; onClicked: root.step-- }
            Item { Layout.fillWidth: true }
            Button {
                text: root.step === 3 ? "Start training" : "Continue"
                highlighted: true
                onClicked: {
                    if (root.step < 3) root.step++
                    else {
                        var selected = "disabled"
                        for (var i = 0; i < aiGroup.buttons.length; ++i)
                            if (aiGroup.buttons[i].checked) selected = aiGroup.buttons[i].aiId
                        var assessment = ({})
                        if (!skipAssessment.checked) {
                            for (var j = 0; j < assessmentRepeater.count; ++j) {
                                var row = assessmentRepeater.itemAt(j)
                                assessment[row.skillId] = row.level
                            }
                        }
                        app.completeOnboarding(profileName.text, root.selectedRole, seniority.currentText, selected, JSON.stringify(assessment))
                    }
                }
            }
        }
    }
}
