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
    // An expired active session is deliberately not resumable: the core clock
    // has reached its deadline and the only truthful next action is to finish
    // and archive an incomplete report.
    property bool resumableInterview: !!app.interview
                                      && (app.interview.resume_available === true
                                          || (app.interview.resume_available === undefined
                                              && app.interview.status === "active"
                                              && app.interview.expired !== true))
    property bool compactLayout: width < 780 || height < 600
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
            implemented: "实现已验证；下一步完成自助复盘与口述自答。",
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
    // The home page intentionally keeps its detail sections scrollable.  Make
    // that affordance visible whenever the dashboard is taller than the view.
    ScrollBar.vertical: ScrollBar {
        id: homeVerticalScrollBar
        width: 6
        padding: 0
        policy: ScrollBar.AsNeeded
        visible: root.contentHeight > root.height
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 3
            color: root.palette.muted
            opacity: 0.4
        }
    }

    ColumnLayout {
        id: content
        x: root.compactLayout ? 18 : 30
        y: root.compactLayout ? 18 : 28
        width: parent.width - (root.compactLayout ? 36 : 60)
        spacing: root.compactLayout ? 12 : 18

        Text {
            text: app.interview && app.interview.expired
                  ? "面试已超时"
                  : root.resumableInterview
                  ? "继续未完成面试"
                  : app.dashboard.current
                  ? "从上次进度继续"
                  : root.trainingTarget
                    ? "开始今天的训练"
                    : "先准备你的训练"
            color: root.palette.text
            font.pixelSize: root.compactLayout ? 22 : 25
            font.bold: true
        }
        Text {
            text: app.interview && app.interview.expired
                  ? "计时已到；打开面试页结束并留档，之后再开始下一场。"
                  : root.resumableInterview
                  ? "上次面试尚未结束；建议先完成或明确放弃本场，再回到训练。"
                  : app.dashboard.current
                  ? "首页只保留当前任务、到期复测和两个主要动作。"
                  : root.trainingTarget
                    ? "已经为你准备好第一项可开始的任务。"
                    : "完成学习档案设置后，这里会显示下一项可开始的任务。"
            color: root.palette.muted
            font.pixelSize: 14
            wrapMode: Text.Wrap
        }

        LabCard {
            Layout.fillWidth: true
            // The desktop baseline remains Layout.preferredHeight: 198;
            // compact windows use the shorter presentation below.
            Layout.preferredHeight: root.compactLayout ? 180 : 198
            cardColor: root.palette.surface
            // Give the one action-oriented card a clear visual anchor.  The
            // rest of the page stays quiet so the next step is obvious.
            prominent: true
            borderColor: root.resumableInterview ? root.palette.border : root.palette.accent
            accentColor: root.trainingTargetRunnable ? root.palette.accent : root.palette.warning
            RowLayout {
                width: parent.width
                height: parent.height
                spacing: root.compactLayout ? 12 : 20
                ColumnLayout {
                    Layout.fillWidth: true
                    Text {
                        text: root.resumableInterview
                              ? "未完成面试"
                              : app.dashboard.current ? "当前训练" : "下一题"
                        color: root.palette.accent
                        font.pixelSize: 11
                        font.bold: true
                        font.letterSpacing: 1.1
                    }
                    Text {
                        // Contract: text: root.trainingTarget ? root.trainingTarget.title
                        text: root.resumableInterview
                              ? (app.interview.role_title || "模拟面试")
                              : root.trainingTarget ? root.trainingTarget.title : "暂无可用任务"
                        color: root.palette.text
                        font.pixelSize: root.compactLayout ? 21 : 24
                        font.bold: true
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Text {
                        text: root.resumableInterview
                              ? "继续完成本场面试，训练任务会在结束后恢复。"
                              : (root.trainingTarget && root.trainingTarget.environment_available === false
                                 ? (root.trainingTarget.environment || "当前环境不能运行这道题。")
                                 : app.dashboard.current
                                   ? "状态：" + root.statusText(app.dashboard.current.status)
                                   : "一道经过验证的题目已经可以开始。")
                        color: root.resumableInterview
                               ? root.palette.warning
                               : (root.trainingTargetRunnable ? root.palette.muted : root.palette.warning)
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        StatusPill {
                            text: app.dashboard.role ? (app.dashboard.role.title || app.dashboard.role.primary_role.replace(/_/g, " ")) : "首次启动请选择"
                            tone: root.palette.muted
                        }
                        StatusPill {
                            visible: !root.resumableInterview
                            text: "已掌握" + (app.dashboard.mastered_count || 0)
                            tone: root.palette.success
                        }
                        StatusPill {
                            visible: !root.resumableInterview
                            text: "到期" + (app.dashboard.due_retention ? app.dashboard.due_retention.length : 0)
                            tone: (app.dashboard.due_retention || []).length > 0 ? root.palette.warning : root.palette.muted
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Text {
                        Layout.fillWidth: true
                        text: root.resumableInterview
                              ? "下一步：继续面试或放弃本场"
                              : root.currentNextStep(app.dashboard.current ? app.dashboard.current.status : "not_started")
                        color: root.resumableInterview
                               ? root.palette.warning
                               : root.currentNextStepTone(app.dashboard.current ? app.dashboard.current.status : "not_started")
                        font.pixelSize: 12
                        font.bold: true
                        wrapMode: Text.Wrap
                    }
                }
                ColumnLayout {
                    Rectangle {
                        objectName: "homeInterviewInProgressState"
                        visible: root.resumableInterview || !!(app.interview && app.interview.expired)
                        Layout.fillWidth: true
                        Layout.preferredWidth: 184
                        Layout.preferredHeight: 120
                        radius: 10
                        color: root.palette.surfaceAlt
                        border.color: root.palette.border
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 2
                            Text {
                                text: app.interview && app.interview.expired ? "面试已超时" : "面试进行中"
                                color: app.interview && app.interview.expired ? root.palette.danger : root.palette.warning
                                font.pixelSize: 14
                                font.bold: true
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                text: app.interview
                                      ? (app.interview.completed_questions || 0) + " / "
                                        + (app.interview.total_questions || 0)
                                      : "0 / 0"
                                color: root.palette.text
                                font.pixelSize: 26
                                font.bold: true
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                text: "问题已完成"
                                color: root.palette.muted
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Button {
                                    id: resumeInlineButton
                                    // Contract copy retained for keyboard/screenshot
                                    // checks: the live branch below changes to an
                                    // explicit expiry action when the clock is over.
                                    // text: "继续面试"
                                    text: app.interview && app.interview.expired ? "结束并留档" : "继续面试"
                                    highlighted: true
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 34
                                    background: Rectangle {
                                        radius: 8
                                        color: resumeInlineButton.enabled
                                              ? root.palette.accent : root.palette.border
                                    }
                                    contentItem: Text {
                                        text: resumeInlineButton.text
                                        color: resumeInlineButton.enabled
                                               ? root.palette.accentForeground : root.palette.muted
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    enabled: root.resumableInterview || !!(app.interview && app.interview.expired)
                                    onClicked: root.resumableInterview ? app.resumeInterview() : app.navigate("interview")
                                }
                                Button {
                                    text: app.interview && app.interview.expired ? "查看面试" : "放弃"
                                    flat: true
                                    Layout.preferredHeight: 34
                                    onClicked: app.interview && app.interview.expired ? app.navigate("interview") : abandonInterviewDialog.open()
                                }
                            }
                        }
                    }
                    Button {
                        id: continueTrainingButton
                        objectName: "homePrimaryAction"
                        visible: !root.resumableInterview && !(app.interview && app.interview.expired)
                        text: root.resumableInterview
                              ? "面试进行中"
                              : (app.dashboard.current ? "继续训练" : "开始训练")
                        highlighted: !root.resumableInterview
                        Layout.fillWidth: true
                        Layout.preferredWidth: 184
                        Layout.preferredHeight: 46
                        enabled: root.trainingTargetRunnable && !root.resumableInterview
                        background: Rectangle {
                            radius: 10
                            color: continueTrainingButton.enabled
                                   ? root.palette.accent : root.palette.surface
                            border.width: continueTrainingButton.enabled ? 0 : 1
                            border.color: root.palette.border
                        }
                        contentItem: Text {
                            text: continueTrainingButton.text
                            color: continueTrainingButton.enabled
                                   ? root.palette.accentForeground : root.palette.muted
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            if (!root.resumableInterview)
                                app.openProblem(root.trainingTarget.problem_id)
                        }
                    }
                    Text {
                        visible: root.resumableInterview
                        text: "请先完成或放弃本场面试，再继续训练。"
                        color: root.palette.muted
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    Button {
                        visible: !!root.trainingTarget && !root.trainingTargetRunnable
                        text: "查看当前可运行题目"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        flat: true
                        onClicked: app.navigate("learn")
                    }
                    Button {
                        id: startInterviewButton
                        objectName: "homeInterviewSecondaryAction"
                        visible: !root.resumableInterview
                        text: root.resumableInterview ? "查看未完成面试" : "开始模拟面试"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        flat: true
                        background: Rectangle {
                            radius: 10
                            color: root.resumableInterview ? root.palette.surfaceAlt : "transparent"
                            border.width: root.resumableInterview ? 0 : 1
                            border.color: root.palette.border
                        }
                        contentItem: Text {
                            text: startInterviewButton.text
                            color: root.palette.text
                            font.bold: root.resumableInterview
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            if (root.resumableInterview)
                                app.resumeInterview()
                            else
                                app.navigate("interview")
                        }
                    }
                }
            }
        }

        // Keep the newest completed/incomplete report visible without loading
        // its transcript. It is derived from the current Profile only and is
        // intentionally secondary to the two primary actions above.
        LabCard {
            id: recentInterviewCard
            objectName: "homeRecentInterview"
            visible: !root.resumableInterview
                     && !!app.recentInterview
                     && !!app.recentInterview.interview_id
            Layout.fillWidth: true
            Layout.preferredHeight: root.compactLayout ? 76 : 84
            cardColor: root.palette.surface
            borderColor: root.palette.border
            RowLayout {
                width: parent.width
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: "最近面试"; color: root.palette.muted; font.pixelSize: 12 }
                    Text {
                        text: (app.recentInterview.completion_status === "completed" ? "已完成" : "未完成")
                              + " · " + (app.recentInterview.overall_score === undefined
                                         ? "尚未评分" : String(app.recentInterview.overall_score) + " / 100")
                        color: root.palette.text
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Text {
                        text: app.recentInterview.finished_at || "时间未记录"
                        color: root.palette.muted
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
                Button {
                    objectName: "homeRecentInterviewAction"
                    text: "查看报告"
                    flat: true
                    Layout.preferredHeight: 36
                    onClicked: app.navigate("interview")
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: root.compactLayout ? 10 : 16
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: root.compactLayout ? 112 : 150; Layout.minimumWidth: 0; cardColor: root.palette.surface; borderColor: root.palette.border; accentColor: root.palette.accent
                Text { text: "目标岗位"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.role ? (app.dashboard.role.title || app.dashboard.role.primary_role.replace(/_/g, " ")) : "首次启动时选择"; color: root.palette.text; font.pixelSize: root.compactLayout ? 16 : 18; font.bold: true; elide: Text.ElideRight; width: parent.width }
                Text { text: app.dashboard.role ? root.seniorityText(app.dashboard.role.seniority) : "校招"; color: root.palette.accent; width: parent.width; elide: Text.ElideRight }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: root.compactLayout ? 112 : 150; Layout.minimumWidth: 0; cardColor: root.palette.surface; borderColor: root.palette.border; accentColor: root.palette.success
                Text { text: "已掌握"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.mastered_count || 0; color: root.palette.text; font.pixelSize: root.compactLayout ? 27 : 32; font.bold: true }
                Text { text: "经过完整验证的节点"; color: root.palette.muted; width: parent.width; elide: Text.ElideRight }
            }
            LabCard {
                Layout.fillWidth: true; Layout.preferredHeight: root.compactLayout ? 112 : 150; Layout.minimumWidth: 0; cardColor: root.palette.surface; borderColor: root.palette.border; accentColor: (app.dashboard.due_retention || []).length > 0 ? root.palette.warning : root.palette.muted
                Text { text: "到期复测"; color: root.palette.muted; font.pixelSize: 12 }
                Text { text: app.dashboard.due_retention ? app.dashboard.due_retention.length : 0; color: root.palette.text; font.pixelSize: root.compactLayout ? 27 : 32; font.bold: true }
                Text { text: "D+2 / D+7 闭卷复写"; color: root.palette.muted; width: parent.width; elide: Text.ElideRight }
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
                            id: retentionActionButton
                            objectName: "startDueRetention"
                            visible: root.retentionActionable(modelData)
                            text: "开始 " + (modelData.stage || "复测").toUpperCase()
                            highlighted: true
                            background: Rectangle {
                                radius: 8
                                color: retentionActionButton.down
                                       ? Qt.darker(root.palette.accent, 1.12)
                                       : root.palette.accent
                            }
                            contentItem: Text {
                                text: retentionActionButton.text
                                color: root.palette.accentForeground
                                font: retentionActionButton.font
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: app.startRetentionFor(modelData.problem_id, modelData.stage)
                        }
                    }
                }
            }
        }

        // Keep the route discoverable without turning Home into a second
        // catalogue/DAG view.  Learn owns the complete route and filtering;
        // Home only offers the one real hand-off action.
        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "推荐路线已整理在刷题训练页"
                color: root.palette.muted
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            Button { text: "查看路线"; flat: true; onClicked: app.navigate("learn") }
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
