import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property var activeQuestion: app.interview.question || null
    property var rubricScores: ({})
    property var aiPreview: ({"parts": [], "estimated_tokens": 0})
    property string pendingAIAction: ""
    property string pendingConnection: ""
    onActiveQuestionChanged: rubricScores = ({})

    function previewAI(action, connectionId) {
        root.aiPreview = app.interviewContextPreview(
            answer.text, includeInterviewMaterials.checked
        )
        if ((root.aiPreview.parts || []).length === 0)
            return
        root.pendingAIAction = action
        root.pendingConnection = connectionId || ""
        contextDialog.open()
    }

    RowLayout {
        anchors.fill: parent; anchors.margins: 26; spacing: 16

        LabCard {
            id: leftPanel
            Layout.preferredWidth: 280
            Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            property bool setupVisible: !app.interview.interview_id || app.interview.status === "completed" || app.interview.status === "incomplete"
            Text { text: leftPanel.setupVisible ? "Interview setup" : "Active session"; color: root.palette.text; font.pixelSize: 19; font.bold: true }
            Text { visible: leftPanel.setupVisible; text: "Role"; color: root.palette.muted; font.pixelSize: 12 }
            ComboBox { visible: leftPanel.setupVisible; id: role; width: parent.width; textRole: "title"; valueRole: "id"; model: app.roles; currentIndex: Math.max(0, app.roles.findIndex ? app.roles.findIndex(function(x){return x.id === "applied_ai_engineer"}) : 1) }
            Text { visible: leftPanel.setupVisible; text: "Seniority"; color: root.palette.muted; font.pixelSize: 12 }
            ComboBox { visible: leftPanel.setupVisible; id: seniority; width: parent.width; model: ["intern", "new_grad", "mid"]; currentIndex: 1 }
            Text { visible: leftPanel.setupVisible; text: "Difficulty"; color: root.palette.muted; font.pixelSize: 12 }
            ComboBox { visible: leftPanel.setupVisible; id: difficulty; width: parent.width; model: ["easy", "medium", "hard"]; currentIndex: 1 }
            Text { visible: leftPanel.setupVisible; text: "Interviewer"; color: root.palette.muted; font.pixelSize: 12 }
            ComboBox { visible: leftPanel.setupVisible; id: aiMode; width: parent.width; model: ["disabled", "provider", "codex"] }
            CheckBox {
                id: useMaterial
                width: parent.width
                visible: leftPanel.setupVisible
                enabled: aiMode.currentText !== "disabled" && app.materials.length > 0
                text: "Use one consented career material"
            }
            ComboBox {
                id: material
                width: parent.width
                visible: leftPanel.setupVisible && useMaterial.checked
                model: app.materials
                textRole: "title"
                valueRole: "id"
            }
            Text {
                width: parent.width
                visible: leftPanel.setupVisible && useMaterial.checked && material.currentIndex >= 0
                text: material.currentIndex >= 0 ? "Material: " + app.materials[material.currentIndex].id + "\nPurpose: role_interview\nSHA-256: " + app.materials[material.currentIndex].sha256 : ""
                color: root.palette.muted
                font.pixelSize: 10
                wrapMode: Text.WrapAnywhere
            }
            CheckBox {
                id: consent
                width: parent.width
                visible: leftPanel.setupVisible && useMaterial.checked
                text: "I consent to this exact ID/SHA for this interview"
            }
            Button {
                width: parent.width
                visible: leftPanel.setupVisible
                text: "Start interview"
                highlighted: true
                enabled: !useMaterial.checked || (material.currentIndex >= 0 && app.materials[material.currentIndex].ai_access && consent.checked)
                onClicked: {
                    if (useMaterial.checked)
                        app.createTailoredInterview(role.currentValue || "applied_ai_engineer", seniority.currentText, difficulty.currentText, material.currentValue, consent.checked, aiMode.currentText)
                    else
                        app.createConfiguredInterview(role.currentValue || "applied_ai_engineer", seniority.currentText, difficulty.currentText, aiMode.currentText)
                }
            }
            Rectangle { width: parent.width; height: 1; color: root.palette.border }
            Text { text: "Session facts"; color: root.palette.text; font.bold: true }
            Text { width: parent.width; text: app.interview.interview_id ? "ID  " + app.interview.interview_id + "\nStatus  " + app.interview.status + "\nRole  " + (app.interview.role_title || app.interview.role_id) + "\nLevel  " + app.interview.seniority : "No active session"; color: root.palette.muted; wrapMode: Text.Wrap; lineHeight: 1.5 }
            Item { height: 6 }
            Text { width: parent.width; text: "Interview scores never change Practice mastery."; color: root.palette.warning; wrapMode: Text.Wrap; font.pixelSize: 12; font.bold: true }
            Item { Layout.fillHeight: true }
        }

        LabCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            RowLayout {
                width: parent.width
                ColumnLayout {
                    Text { text: activeQuestion ? activeQuestion.kind.replace(/_/g, " ").toUpperCase() : "INTERVIEW ROOM"; color: root.palette.accent; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1 }
                    Text { text: activeQuestion ? activeQuestion.title : "Start a Role Blueprint"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                }
                Item { Layout.fillWidth: true }
                StatusPill { text: app.interview.remaining_seconds ? Math.floor(app.interview.remaining_seconds / 60) + " min remaining" : "Not started"; tone: root.palette.warning }
            }
            Rectangle { width: parent.width; height: 1; color: root.palette.border }
            ScrollView {
                width: parent.width; Layout.fillHeight: true; clip: true
                Column {
                    width: parent.width; spacing: 16
                    Text { width: parent.width; text: activeQuestion ? activeQuestion.prompt : "Choose a role, seniority and difficulty. The engine freezes a public Blueprint, presents one question at a time, and separates objective code evidence from rubric judgment."; color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; lineHeight: 1.25 }
                    TextArea { id: answer; width: parent.width; height: 180; visible: !!activeQuestion && activeQuestion.kind !== "coding"; placeholderText: "Your answer…"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.palette.border } }
                    Column {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                        width: parent.width
                        spacing: 6
                        Text { text: "Manual rubric (1–5 per dimension)"; color: root.palette.muted; font.bold: true }
                        Repeater {
                            model: activeQuestion ? Object.keys(activeQuestion.rubric.dimensions) : []
                            delegate: RowLayout {
                                required property string modelData
                                width: parent.width
                                Text { text: modelData.replace(/_/g, " "); color: root.palette.text; Layout.preferredWidth: 190 }
                                Slider {
                                    id: dimensionScore
                                    from: 1; to: 5; stepSize: 1; value: 3
                                    Layout.fillWidth: true
                                    onValueChanged: root.rubricScores[modelData] = Math.round(value)
                                    Component.onCompleted: root.rubricScores[modelData] = 3
                                }
                                Text { text: Math.round(dimensionScore.value) + " / 5"; color: root.palette.text; font.bold: true; Layout.preferredWidth: 42 }
                            }
                        }
                    }
                    TextArea { id: evidence; width: parent.width; height: 86; visible: !!activeQuestion && activeQuestion.kind !== "coding"; placeholderText: "Evidence for this score (required)"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.palette.border } }
                    ComboBox {
                        id: providerConnection
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && app.interview.ai_mode === "provider"
                        width: parent.width
                        model: app.connections
                        textRole: "display_name"
                        valueRole: "connection_id"
                    }
                    CheckBox {
                        id: includeInterviewMaterials
                        visible: !!activeQuestion
                                 && activeQuestion.kind !== "coding"
                                 && app.interview.ai_mode !== "disabled"
                                 && (app.interview.material_refs || []).length > 0
                        checked: true
                        text: "Include the consented material in this AI request"
                    }
                    RowLayout {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                        width: parent.width
                        Button {
                            text: "Record manual assessment"
                            onClicked: app.answerInterviewDetailed(answer.text, JSON.stringify(root.rubricScores), evidence.text)
                        }
                        Button {
                            visible: app.interview.ai_mode === "provider"
                            enabled: providerConnection.currentIndex >= 0 && !app.busy
                            text: "Preview AI assessment"
                            highlighted: true
                            onClicked: root.previewAI("provider", providerConnection.currentValue)
                        }
                        Button {
                            visible: app.interview.ai_mode === "codex"
                            text: "Connect Codex interviewer"
                            highlighted: true
                            onClicked: app.connectCodex("interviewer")
                        }
                        Button {
                            visible: app.interview.ai_mode === "codex" && app.aiStatus.indexOf("connected") >= 0
                            text: "Preview Codex assessment"
                            onClicked: root.previewAI("codex", "")
                        }
                    }
                    LabCard {
                        visible: !!app.interview.pending_followup
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.accent
                        Text { width: parent.width; text: "Adaptive follow-up\n" + (app.interview.pending_followup || ""); color: root.palette.text; wrapMode: Text.Wrap; font.bold: true }
                        TextArea { id: followupAnswer; width: parent.width; height: 100; placeholderText: "Answer the follow-up"; wrapMode: Text.Wrap; padding: 12; clip: true }
                        Button { text: "Record follow-up and AI scorecard"; highlighted: true; onClicked: app.answerAIFollowup(followupAnswer.text) }
                    }
                    ColumnLayout {
                        visible: !!activeQuestion && activeQuestion.kind === "coding"
                        width: parent.width; spacing: 10
                        Text { text: "Frozen session submission"; color: root.palette.text; font.bold: true }
                        TextArea {
                            id: codingEditor
                            Layout.fillWidth: true; Layout.preferredHeight: 260
                            text: app.interview.coding_text || ""
                            color: root.palette.text
                            font.family: "Cascadia Mono, Consolas, monospace"
                            font.pixelSize: 13
                            wrapMode: TextEdit.NoWrap
                            padding: 12
                            clip: true
                            background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.palette.border }
                            Accessible.name: "Timed interview code editor"
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Button { text: "Save"; onClicked: app.saveInterviewCoding(codingEditor.text) }
                            Button { text: "Run grader"; highlighted: true; enabled: !app.busy; onClicked: app.runInterviewCoding(codingEditor.text) }
                            Button { text: "Record round and continue"; enabled: !app.busy; onClicked: app.recordInterviewCodingRound() }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 110; radius: 8
                            color: root.palette.surfaceAlt; border.color: root.palette.border
                            ScrollView {
                                anchors.fill: parent; anchors.margins: 10
                                Text { width: parent.width; text: app.testOutput || "The local grader is authoritative for coding evidence."; color: root.palette.text; wrapMode: Text.Wrap; font.family: "Cascadia Mono, Consolas, monospace"; font.pixelSize: 11 }
                            }
                        }
                        Text { text: "No teaching hints are exposed during an active interview."; color: root.palette.warning; font.pixelSize: 12; font.bold: true }
                    }
                }
            }
            RowLayout {
                width: parent.width
                Text { text: activeQuestion ? "Question " + activeQuestion.question_id : ""; color: root.palette.muted }
                Item { Layout.fillWidth: true }
                Button { text: "Finish / archive"; enabled: !!app.interview.interview_id; onClicked: app.finishInterview() }
            }
        }
    }

    Dialog {
        id: contextDialog
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, root.width - 64)
        height: Math.min(520, root.height - 64)
        title: "Context Preview"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.pendingAIAction === "provider")
                app.assessInterviewWithProvider(
                    answer.text,
                    root.pendingConnection,
                    includeInterviewMaterials.checked
                )
            else if (root.pendingAIAction === "codex")
                app.sendCodexInterviewAnswer(
                    answer.text,
                    includeInterviewMaterials.checked
                )
            root.pendingAIAction = ""
            root.pendingConnection = ""
        }
        onRejected: {
            root.pendingAIAction = ""
            root.pendingConnection = ""
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "Only the visible items below will be sent. Cancel to send nothing."
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                Column {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: root.aiPreview.parts || []
                        delegate: RowLayout {
                            required property var modelData
                            width: parent.width
                            CheckBox { checked: modelData.selected; enabled: false }
                            Text {
                                text: modelData.label
                                color: root.palette.text
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            StatusPill {
                                visible: modelData.sensitive
                                text: "private"
                                tone: root.palette.warning
                            }
                        }
                    }
                }
            }
            Text {
                text: "Estimated context: " + (root.aiPreview.estimated_tokens || 0) + " tokens"
                color: root.palette.muted
                font.pixelSize: 12
            }
        }
    }
}
