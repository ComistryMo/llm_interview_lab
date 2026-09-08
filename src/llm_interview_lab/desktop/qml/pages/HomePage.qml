import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root

    required property var app
    required property var colors
    property var theme: null
    property string layoutMode: width < 1040 ? "compact"
                               : width < 1400 ? "standard" : "wide"

    readonly property bool compactLayout: layoutMode === "compact" || height < 600
    readonly property bool activeInterview: !!app.interview
                                            && (app.interview.expired === true
                                                || ["active", "paused"].indexOf(app.interview.status) >= 0)
    readonly property bool expiredInterview: !!app.interview && app.interview.expired === true
    readonly property bool resumableInterview: activeInterview && !expiredInterview
                                                && (app.interview.resume_available === true
                                                    || app.interview.resume_available === undefined)
    readonly property var currentPracticeCandidate: app.dashboard.current || null
    readonly property var currentPractice: practiceActionable(currentPracticeCandidate)
                                           ? currentPracticeCandidate : null
    readonly property var dueRetentions: app.dashboard.due_retention || []
    readonly property int dueRetentionCount: app.dashboard.due_retention_count === undefined
                                             ? dueRetentions.length
                                             : app.dashboard.due_retention_count
    readonly property int dueReviewCount: app.dashboard.due_review_count === undefined
                                          ? (app.dashboard.due_review || []).length
                                          : app.dashboard.due_review_count
    readonly property var actionableRetention: firstActionableRetention(dueRetentions)
    readonly property var firstUnlock: (app.dashboard.unlocks || []).length > 0
                                       ? app.dashboard.unlocks[0] : null
    readonly property string focusKind: expiredInterview ? "expired_interview"
                                         : activeInterview ? "interview"
                                         : "new_interview"
    readonly property var focusProblem: focusKind === "practice" ? currentPractice
                                        : focusKind === "unlock" ? firstUnlock : null
    readonly property bool focusProblemRunnable: !!focusProblem
                                                 && focusProblem.environment_available !== false
    readonly property var secondaryRetentions: retentionItemsAfterFocus(dueRetentions)

    readonly property color strongText: theme ? theme.textStrong : colors.text
    readonly property color pageSurface: theme ? theme.surface : colors.surface
    readonly property color quietBorder: theme ? theme.borderSubtle : colors.border
    readonly property color accentColor: theme ? theme.accent : colors.accent
    readonly property color warningColor: theme ? theme.warning : colors.warning
    readonly property color dangerColor: theme ? theme.danger : colors.danger
    readonly property color successColor: theme ? theme.success : colors.success

    function practiceActionable(item) {
        if (!item)
            return false
        return ["not_started", "in_progress", "implemented"].indexOf(item.status) >= 0
    }

    function firstActionableRetention(items) {
        for (var i = 0; i < items.length; ++i) {
            if (retentionActionable(items[i]))
                return items[i]
        }
        return null
    }

    function retentionItemsAfterFocus(items) {
        if (focusKind !== "retention" || !actionableRetention)
            return items
        var remaining = []
        var removed = false
        for (var i = 0; i < items.length; ++i) {
            var item = items[i]
            if (!removed && item.problem_id === actionableRetention.problem_id
                    && item.stage === actionableRetention.stage) {
                removed = true
                continue
            }
            remaining.push(item)
        }
        return remaining
    }

    function statusText(value) {
        return ({not_started: "未开始", in_progress: "进行中", implemented: "已实现",
                 reviewed: "已审查", retained_d2: "已完成 D+2", retained_d7: "已完成 D+7",
                 mastered: "已掌握"})[value] || value || "未开始"
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

    function retentionActionable(item) {
        return !!item && item.actionable !== false && !(item.blocked_reason || "")
    }

    function retentionLabel(item) {
        var stage = (item.stage || "").toUpperCase()
        var title = item.problem_id
                ? app.problemTitle(item.problem_id, item.title || item.problem_id)
                : (item.title || "间隔复测")
        return title + (stage ? " · " + stage : "")
    }

    function focusEyebrow() {
        if (focusKind === "new_interview") return "模拟面试"
        if (focusKind === "expired_interview") return "需要处理"
        if (focusKind === "interview") return "未完成面试"
        if (focusKind === "practice") return "继续训练"
        if (focusKind === "retention") return "到期复测"
        if (focusKind === "unlock") return "下一项训练"
        return "今天"
    }

    function interviewRoleTitle() {
        var roles = app.roles || []
        for (var i = 0; i < roles.length; ++i) {
            if (roles[i].id === app.interview.role_id)
                return roles[i].title
        }
        return app.interview.role_title || "模拟面试"
    }

    function focusTitle() {
        if (focusKind === "new_interview") return "从你的经历开始，逐步深入"
        if (focusKind === "expired_interview" || focusKind === "interview")
            return interviewRoleTitle()
        if (focusKind === "retention")
            return retentionLabel(actionableRetention)
        if (focusProblem)
            return app.problemTitle(focusProblem.problem_id, focusProblem.title || focusProblem.problem_id)
        return "选择一项可练任务"
    }

    function focusDescription() {
        if (focusKind === "new_interview") return "从你的经历出发，逐步讨论项目、岗位原理和代码。回答后接着追问，结束后按证据复盘。"
        // During a task switch, the derived focus updates one binding at a
        // time. Do not dereference its previous task in that loading frame.
        if ((focusKind === "practice" || focusKind === "unlock") && !focusProblem)
            return "正在加载当前任务…"
        if (focusKind === "expired_interview")
            return "本场计时已经结束。请完成留档后再开始新的训练或面试。"
        if (focusKind === "interview")
            return "上次面试尚未结束。继续完成本场，或在面试页明确结束并留档。"
        if (focusKind === "practice" && !focusProblemRunnable)
            return focusProblem.environment || "当前环境不能运行这道题，请查看可运行题目。"
        if (focusKind === "practice")
            return currentNextStep(currentPractice.status)
        if (focusKind === "retention")
            return actionableRetention.due_at
                    ? "已于 " + actionableRetention.due_at + " 到期；本次不会展示旧答案。"
                    : "现在可以开始闭卷复测；本次不会展示旧答案。"
        if (focusKind === "unlock" && !focusProblemRunnable)
            return focusProblem.environment || "这道题需要额外练习环境。"
        if (focusKind === "unlock")
            return "前置条件已经满足，可以开始一次独立实现。"
        return "从可练题目中选择下一项，或先进行一场模拟面试。"
    }

    function primaryLabel() {
        if (focusKind === "new_interview") return "开始面试"
        if (focusKind === "expired_interview") return "完成并留档"
        if (focusKind === "interview") return "继续面试"
        if (focusKind === "practice") return focusProblemRunnable ? "继续训练" : "查看可运行题目"
        if (focusKind === "retention") return "开始 " + (actionableRetention.stage || "复测").toUpperCase()
        if (focusKind === "unlock") return focusProblemRunnable ? "开始训练" : "查看可运行题目"
        return "浏览可练题目"
    }

    function executePrimary() {
        if (focusKind === "new_interview") {
            app.prepareInterview()
            return
        }
        if (focusKind === "expired_interview") {
            app.finishInterview()
            return
        }
        if (focusKind === "interview") {
            if (resumableInterview)
                app.resumeInterview()
            else
                app.navigate("interview")
            return
        }
        if (focusKind === "retention") {
            app.startRetentionFor(actionableRetention.problem_id, actionableRetention.stage)
            return
        }
        if (focusProblem && focusProblemRunnable) {
            app.openProblem(focusProblem.problem_id)
            return
        }
        app.navigate("learn")
    }

    contentWidth: width
    contentHeight: content.y + content.implicitHeight + 28
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: LabScrollBar { visible: root.contentHeight > root.height }

    ColumnLayout {
        id: content
        x: (root.width - width) / 2
        y: root.compactLayout ? 20 : 32
        width: Math.min(1000, root.width - (root.compactLayout ? 36 : 64))
        spacing: 24

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            LabText {
                theme: root.theme
                Layout.fillWidth: true
                text: "今天，准备好下一场面试"
                variant: "title"
                strong: true
                wrapMode: Text.Wrap
            }
            LabText {
                theme: root.theme
                Layout.fillWidth: true
                text: app.dashboard.role
                      ? (app.dashboard.role.title || "目标岗位")
                      : "练习、面试、复盘，都从真实问题出发。"
                tone: "muted"
                wrapMode: Text.Wrap
            }
        }

        LabSurface {
            id: todayFocus
            objectName: "homeTodayFocus"
            theme: root.theme
            Layout.fillWidth: true
            Layout.preferredHeight: focusContent.implicitHeight + padding * 2
            level: "canvas"
            outlined: false
            padding: 0

            ColumnLayout {
                id: focusContent
                anchors.fill: parent
                spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    LabText {
                        theme: root.theme
                        text: root.focusEyebrow()
                        tone: "muted"
                        variant: "caption"
                        Layout.fillWidth: true
                    }
                    StatusPill {
                        objectName: "homeInterviewInProgressState"
                        theme: root.theme
                        visible: root.activeInterview
                        text: root.expiredInterview ? "已到时" : "进行中"
                        tone: root.expiredInterview ? root.dangerColor : root.accentColor
                        compact: true
                    }
                    StatusPill {
                        theme: root.theme
                        visible: !!root.focusProblem
                        text: root.focusProblemRunnable ? "当前可运行" : "环境受限"
                        tone: root.focusProblemRunnable ? root.successColor : root.warningColor
                        compact: true
                    }
                }
                LabText {
                    objectName: "homeFocusTitle"
                    theme: root.theme
                    Layout.fillWidth: true
                    text: root.focusTitle()
                    variant: "section"
                    strong: true
                    wrapMode: Text.Wrap
                }
                LabText {
                    theme: root.theme
                    Layout.fillWidth: true
                    text: root.focusDescription()
                    tone: root.expiredInterview ? "danger" : "muted"
                    wrapMode: Text.Wrap
                }
                LabText {
                    theme: root.theme
                    visible: root.focusKind === "practice"
                    text: root.statusText(root.currentPractice ? root.currentPractice.status : "")
                    variant: "caption"
                    tone: "muted"
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    LabButton {
                        objectName: "homePrimaryAction"
                        theme: root.theme
                        text: root.primaryLabel()
                        variant: "primary"
                        Layout.minimumWidth: implicitWidth
                        busy: !!app.busy
                        onClicked: root.executePrimary()
                    }
                    LabButton {
                        objectName: "homeInterviewSecondaryAction"
                        theme: root.theme
                        visible: !root.expiredInterview
                        text: root.activeInterview ? "结束并留档" : "面试记录"
                        variant: "ghost"
                        onClicked: root.activeInterview
                                   ? abandonInterviewDialog.open() : app.showInterviewHistory()
                    }
                    Item { Layout.fillWidth: true }
                }
            }
        }

        RowLayout {
            objectName: "homeCurrentPractice"
            Layout.fillWidth: true
            spacing: 16
            ColumnLayout {
                Layout.fillWidth: true
                LabText { theme: root.theme; text: "当前练习"; variant: "section"; strong: true }
                LabText {
                    theme: root.theme; Layout.fillWidth: true; wrapMode: Text.Wrap
                    text: root.currentPractice
                          ? app.problemTitle(root.currentPractice.problem_id, root.currentPractice.title || root.currentPractice.problem_id)
                          : "选择一道可运行题目，独立实现，再检查与复盘。"
                    tone: "muted"
                }
            }
            LabButton {
                theme: root.theme; text: root.currentPractice ? "继续练习" : "浏览题目"; variant: "secondary"
                onClicked: root.currentPractice ? app.openProblem(root.currentPractice.problem_id) : app.navigate("learn")
            }
        }

        LabSurface {
            id: evidenceRail
            objectName: "homeEvidenceRail"
            theme: root.theme
            Layout.fillWidth: true
            Layout.preferredHeight: evidenceContent.implicitHeight + padding * 2
            level: "canvas"
            outlined: false
            padding: 0

            ColumnLayout {
                id: evidenceContent
                objectName: "homeEvidenceContent"
                anchors.fill: parent
                spacing: 16
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.quietBorder }
                RowLayout {
                    Layout.fillWidth: true
                    LabText { theme: root.theme; text: "学习记录"; variant: "section"; Layout.fillWidth: true }
                    LabButton {
                        objectName: "homeProgressAction"
                        theme: root.theme
                        text: "查看进度"
                        variant: "ghost"
                        compact: true
                        onClicked: app.navigate("progress")
                    }
                }
                RowLayout {
                    objectName: "homeEvidenceMetrics"
                    visible: (app.dashboard.mastered_count || 0) + root.dueRetentionCount + root.dueReviewCount > 0
                    Layout.fillWidth: true
                    spacing: 16
                    Repeater {
                        model: [
                            {label: "已掌握", value: app.dashboard.mastered_count || 0},
                            {label: "到期复测", value: root.dueRetentionCount},
                            {label: "待复盘", value: root.dueReviewCount}
                        ]
                        ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 4
                            LabText {
                                theme: root.theme
                                Layout.fillWidth: true
                                text: String(modelData.value)
                                variant: "section"
                                strong: true
                            }
                            LabText {
                                theme: root.theme
                                Layout.fillWidth: true
                                text: modelData.label
                                tone: "muted"
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
                LabText {
                    objectName: "homeEvidenceNote"
                    theme: root.theme
                    Layout.fillWidth: true
                    text: "完成实现、复盘与间隔复测后，掌握记录会在这里更新。"
                    variant: "caption"
                    tone: "subtle"
                    wrapMode: Text.Wrap
                }
            }
        }

        ColumnLayout {
            objectName: "dueRetentionList"
            Layout.fillWidth: true
            visible: root.secondaryRetentions.length > 0
            spacing: 8

            SectionHeader {
                theme: root.theme
                Layout.fillWidth: true
                title: root.focusKind === "retention" ? "其他到期复测" : "到期复测"
                description: "复测不会复制或展示旧答案。"
            }

            Repeater {
                model: root.secondaryRetentions
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: retentionRow.implicitHeight + 24
                    radius: root.theme ? root.theme.radiusMedium : 9
                    color: root.pageSurface
                    border.color: root.quietBorder

                    RowLayout {
                        id: retentionRow
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 12
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            LabText {
                                theme: root.theme
                                Layout.fillWidth: true
                                text: root.retentionLabel(modelData)
                                strong: true
                            }
                            LabText {
                                theme: root.theme
                                Layout.fillWidth: true
                                text: modelData.blocked_reason
                                      || (modelData.due_at ? "到期：" + modelData.due_at
                                                          : "现在可以开始闭卷复测")
                                tone: modelData.blocked_reason ? "warning" : "muted"
                                variant: "caption"
                            }
                        }
                        StatusPill {
                            theme: root.theme
                            visible: !root.retentionActionable(modelData)
                            text: "暂不可开始"
                            tone: root.warningColor
                            compact: true
                        }
                        LabButton {
                            objectName: "startDueRetention"
                            theme: root.theme
                            visible: root.retentionActionable(modelData)
                            text: "开始 " + (modelData.stage || "复测").toUpperCase()
                            variant: "secondary"
                            compact: true
                            onClicked: app.startRetentionFor(modelData.problem_id, modelData.stage)
                        }
                    }
                }
            }
        }

        LabSurface {
            id: recentInterviewCard
            objectName: "homeRecentInterview"
            theme: root.theme
            visible: !root.activeInterview && !!app.recentInterview
                     && !!app.recentInterview.interview_id
            Layout.fillWidth: true
            // Keep enough vertical room for localized status/time strings at
            // narrow widths.  A fixed 82px row clipped the second line and
            // made the report action appear to overlap the interview summary.
            Layout.preferredHeight: recentSummary.implicitHeight + padding * 2
            level: "canvas"
            outlined: false
            padding: 0

            RowLayout {
                id: recentSummary
                anchors.fill: parent
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 2
                    LabText { theme: root.theme; text: "最近面试"; tone: "muted"; variant: "caption" }
                    LabText {
                        theme: root.theme
                        Layout.fillWidth: true
                        text: app.recentInterview.completion_status !== "completed"
                              ? "未完成 · 查看本场记录"
                              : "已完成 · " + (app.recentInterview.overall_score === undefined
                                 || app.recentInterview.overall_score === null
                                 ? "尚未评分" : String(app.recentInterview.overall_score) + " / 100")
                        strong: true
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                    LabText {
                        theme: root.theme
                        Layout.fillWidth: true
                        text: app.recentInterview.finished_at
                              ? Qt.formatDateTime(new Date(app.recentInterview.finished_at), "yyyy/MM/dd hh:mm")
                              : "时间未记录"
                        tone: "muted"
                        variant: "caption"
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }
                LabButton {
                    objectName: "homeRecentInterviewAction"
                    theme: root.theme
                    text: "查看报告"
                    variant: "ghost"
                    compact: true
                    Layout.minimumWidth: 72
                    onClicked: app.openInterview(app.recentInterview.interview_id)
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
        contentItem: LabText {
            theme: root.theme
            width: 360
            text: "本场会以“未完成”留档，已锁定的回答和已有评分不会丢失。"
            wrapMode: Text.Wrap
        }
    }
}
