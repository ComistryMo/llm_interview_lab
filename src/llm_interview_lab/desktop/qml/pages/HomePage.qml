import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    property var trainingTarget: app.dashboard.current
                                 || ((app.dashboard.unlocks || []).length > 0 ? app.dashboard.unlocks[0] : null)
    property bool trainingTargetRunnable: !!trainingTarget && trainingTarget.environment_available !== false
    function statusText(value) {
        return ({not_started: "未开始", in_progress: "进行中", implemented: "已实现",
                 reviewed: "已审查", retained_d2: "已完成 D+2", retained_d7: "已完成 D+7",
                 mastered: "已掌握"})[value] || value || "未开始"
    }
    function seniorityText(value) {
        return ({intern: "实习", new_grad: "校招", mid: "有经验", senior: "高级"})[value] || value || "未设置"
    }
    function currentNextStep(status) {
        return ({
            not_started: "尚未开始；打开题目后先完成一次独立实现。",
            in_progress: "答案仍在编辑；下一步运行公开测试并修复失败。",
            implemented: "实现已验证；下一步完成契约审查与口述答辩。",
            reviewed: "审查已完成；等待到期的间隔复测。",
            retained_d2: "D+2 已完成；等待 D+7 迁移复测。",
            retained_d7: "D+7 已完成；掌握状态仍由固定规则计算。",
            mastered: "该节点已掌握；可以继续下一项已解锁任务。"
        })[status] || "继续当前任务，完成页面显示的下一项证据。"
    }
    function currentNextStepTone(status) {
        return ["implemented", "reviewed", "retained_d2", "retained_d7", "mastered"].indexOf(status) >= 0
               ? root.palette.success : root.palette.muted
    }
    function retentionActionable(item) {
        return !!item && item.actionable !== false && !(item.blocked_reason || "")
    }
    function retentionLabel(item) {
        var stage = (item.stage || "").toUpperCase()
        return (item.title || item.problem_id || "间隔复测") + (stage ? " · " + stage : "")
    }
    contentWidth: width
    contentHeight: content.implicitHeight + 56
    clip: true

    ColumnLayout {
        id: content
        x: 30; y: 28; width: parent.width - 60
        spacing: 18

        Text { text: "从上次进度继续"; color: root.palette.text; font.pixelSize: 25; font.bold: true }
        Text { text: "首页只保留当前任务、到期复测和两个主要动作。"; color: root.palette.muted; font.pixelSize: 14 }

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
                    Text { text: app.dashboard.current ? "当前训练" : "下一题"; color: root.palette.accent; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.1 }
                    Text { text: root.trainingTarget ? root.trainingTarget.problem_id + "  " + root.trainingTarget.title : "暂无可用任务"; color: root.palette.text; font.pixelSize: 23; font.bold: true }
                    Text {
                        text: root.trainingTarget && root.trainingTarget.environment_available === false
                              ? (root.trainingTarget.environment || "当前环境不能运行这道题。")
                              : app.dashboard.current
                                ? "状态：" + root.statusText(app.dashboard.current.status)
                                : "一道经过验证的题目已经可以开始。"
                        color: root.trainingTargetRunnable ? root.palette.muted : root.palette.warning
                    }
                    Item { Layout.fillHeight: true }
                    Text {
                        Layout.fillWidth: true
                        text: root.currentNextStep(app.dashboard.current ? app.dashboard.current.status : "not_started")
                        color: root.currentNextStepTone(app.dashboard.current ? app.dashboard.current.status : "not_started")
                        font.pixelSize: 12
                        font.bold: true
                        wrapMode: Text.Wrap
                    }
                }
                ColumnLayout {
                    Button {
                        id: continueTrainingButton
                        text: app.dashboard.current ? "继续训练" : "开始训练"
                        highlighted: true
                        Layout.preferredWidth: 160
                        Layout.preferredHeight: 44
                        enabled: root.trainingTargetRunnable
                        background: Rectangle {
                            radius: 8
                            color: continueTrainingButton.enabled ? root.palette.accent : root.palette.border
                        }
                        contentItem: Text {
                            text: continueTrainingButton.text
                            color: continueTrainingButton.enabled ? "white" : root.palette.muted
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: app.openProblem(root.trainingTarget.problem_id)
                    }
                    Button {
                        visible: !!root.trainingTarget && !root.trainingTargetRunnable
                        text: "查看当前可运行题目"
                        Layout.preferredWidth: 160
                        Layout.preferredHeight: 42
                        onClicked: app.navigate("learn")
                    }
                    Button {
                        id: startInterviewButton
                        text: "开始模拟面试"
                        Layout.preferredWidth: 160
                        Layout.preferredHeight: 42
                        background: Rectangle {
                            radius: 8
                            color: "transparent"
                            border.width: 1
                            border.color: root.palette.accent
                        }
                        contentItem: Text {
                            text: startInterviewButton.text
                            color: root.palette.accent
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: app.navigate("interview")
                    }
                }
            }
        }

        LabCard {
            objectName: "resumableInterviewCard"
            visible: app.interview && app.interview.status === "active"
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 112 : 0
            cardColor: root.palette.surface
            borderColor: root.palette.accent
            RowLayout {
                width: parent.width; height: parent.height; spacing: 16
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "检测到未完成面试"; color: root.palette.text; font.pixelSize: 17; font.bold: true }
                    Text {
                        text: (app.interview.role_title || app.interview.role_id || "模拟面试")
                              + " · 已完成 " + (app.interview.completed_questions || 0)
                              + " / " + (app.interview.total_questions || 0)
                        color: root.palette.muted
                    }
                }
                Button {
                    id: resumeInterviewButton
                    text: "继续面试"
                    highlighted: true
                    Layout.preferredWidth: 112
                    Layout.preferredHeight: 40
                    background: Rectangle { radius: 8; color: root.palette.accent }
                    contentItem: Text {
                        text: resumeInterviewButton.text
                        color: "white"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: app.resumeInterview()
                }
                Button { text: "放弃本场"; onClicked: abandonInterviewDialog.open() }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 150; cardColor: root.palette.surface; borderColor: root.palette.border
                Text { text: "目标岗位"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.role ? (app.dashboard.role.title || app.dashboard.role.primary_role.replace(/_/g, " ")) : "首次启动时选择"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                Text { text: app.dashboard.role ? root.seniorityText(app.dashboard.role.seniority) : "校招"; color: root.palette.accent }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 150; cardColor: root.palette.surface; borderColor: root.palette.border
                Text { text: "已掌握"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.mastered_count || 0; color: root.palette.text; font.pixelSize: 32; font.bold: true }
                Text { text: "经过完整验证的节点"; color: root.palette.muted }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: 150; cardColor: root.palette.surface; borderColor: root.palette.border
                Text { text: "到期复测"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.due_retention ? app.dashboard.due_retention.length : 0; color: root.palette.text; font.pixelSize: 32; font.bold: true }
                Text { text: "D+2 / D+7 闭卷复写"; color: root.palette.muted }
            }
        }

        ColumnLayout {
            objectName: "dueRetentionList"
            Layout.fillWidth: true
            visible: (app.dashboard.due_retention || []).length > 0
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Text { text: "今天到期"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                Item { Layout.fillWidth: true }
                Text {
                    text: (app.dashboard.due_retention || []).length + " 项间隔复测"
                    color: root.palette.muted
                    font.pixelSize: 12
                }
            }

            Repeater {
                model: app.dashboard.due_retention || []
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 54
                    radius: 8
                    color: root.palette.surface
                    border.color: root.palette.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 12
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                Layout.fillWidth: true
                                text: root.retentionLabel(modelData)
                                color: root.palette.text
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.blocked_reason || (modelData.due_at ? "到期：" + modelData.due_at : "现在可以开始闭卷复测")
                                color: modelData.blocked_reason ? root.palette.warning : root.palette.muted
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }
                        }
                        StatusPill {
                            visible: !root.retentionActionable(modelData)
                            text: "暂不可开始"
                            tone: root.palette.warning
                        }
                        Button {
                            objectName: "startDueRetention"
                            visible: root.retentionActionable(modelData)
                            text: "开始 " + (modelData.stage || "复测").toUpperCase()
                            highlighted: true
                            onClicked: app.startRetentionFor(modelData.problem_id, modelData.stage)
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "推荐闯关路线"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            Item { Layout.fillWidth: true }
            Button { text: "查看路线"; flat: true; onClicked: app.navigate("learn") }
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

    Dialog {
        id: abandonInterviewDialog
        modal: true
        anchors.centerIn: parent
        title: "放弃本场面试？"
        width: Math.min(440, root.width - 48)
        height: 170
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: app.finishInterview()
        contentItem: Text {
            width: 360
            text: "本场会以“未完成”留档，已锁定的回答和已有评分不会丢失。"
            color: root.palette.text
            wrapMode: Text.Wrap
        }
    }
}
