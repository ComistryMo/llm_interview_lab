import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "../components"

Item {
    id: root
    required property var app
    required property var colors
    required property var theme
    // `width` is the page viewport after the shell/sidebar.  These thresholds
    // therefore map to a 1440px window for the two-column view and keep the
    // 900px minimum window on a single, usable editor surface.
    property bool wideLayout: root.Window.window && root.Window.window.width >= 1180
    // Only a completed test operation needs the expanded result viewport.
    // Save/retention notices stay compact so the editor and primary action
    // remain visible on a first visit.
    property bool testResultExpanded: ["测试通过", "测试失败", "保存失败", "结果已过期", "运行代码", "脚本已结束", "运行失败"].indexOf(app.testState) >= 0
    property bool mediumLayout: wideLayout
    property bool compactHeight: height < 600
    property var actions: (app.currentTask && app.currentTask.actions) || ({})
    property string activeProblemId: app.currentTask && app.currentTask.problem_id
                                     ? String(app.currentTask.problem_id) : ""
    // A page can briefly be visible before a problem is selected (for
    // example after a fresh onboarding or a stale deep link).  Treat that as
    // a real empty state instead of exposing a test button that silently does
    // nothing against an absent submission.
    property bool hasTask: root.activeProblemId.length > 0
    property bool syncingEditor: false
    property bool showOriginalContract: false
    readonly property bool sourceTaskChinese: (app.currentTask.task || "").indexOf("\n## 任务\n") >= 0
    property string codeFontFamily: Qt.platform.os === "windows" ? "Cascadia Mono"
                                    : Qt.platform.os === "osx" ? "Menlo" : "monospace"

    function canSubmitCurrent() {
        return app.testState === "测试通过"
               && !app.submissionDirty
               && (app.testedRevision || "").length > 0
    }

    function reviewAction() {
        return root.actions.review || ({})
    }

    function nextRetentionAction() {
        var retention = root.actions.retention || ({})
        var stages = ["d2", "d7"]
        for (var i = 0; i < stages.length; ++i) {
            var item = retention[stages[i]] || null
            if (item && item.state !== "complete")
                return item
        }
        return null
    }

    function retentionBlockedText(item) {
        if (!item)
            return ""
        if (item.blocked_reason)
            return item.blocked_reason
        if (item.state === "future")
            return item.due_at ? "复测尚未到期，预计可开始时间：" + item.due_at : "复测尚未到期。"
        if (item.state === "missing_asset")
            return "这道题缺少经过验证的复测资产，当前不能达到已掌握。"
        if (item.state === "missing_environment")
            return "当前运行环境不满足本次复测要求。"
        return "当前复测阶段暂不可开始。"
    }

    function primaryActionKind() {
        if (!root.hasTask)
            return "no-task"
        if (app.currentTask && app.currentTask.environment_available === false)
            return "blocked"
        var review = root.reviewAction()
        if (review.actionable === true)
            return "review"
        if (review.state === "complete") {
            var retention = root.nextRetentionAction()
            if (retention) {
                if ((retention.state === "due" || retention.state === "in_progress")
                        && retention.actionable === true)
                    return "retention"
                return "blocked"
            }
        }
        if (root.canSubmitCurrent())
            return "submit"
        return "test"
    }

    function primaryActionLabel() {
        var kind = root.primaryActionKind()
        if (kind === "no-task")
            return "返回刷题训练"
        if (kind === "review")
            return "开始自助复盘"
        if (kind === "retention")
            return "开始 " + (root.nextRetentionAction().stage || "复测").toUpperCase()
        if (kind === "submit")
            return "提交实现"
        return "运行公开测试"
    }

    function actionExplanation() {
        if (!root.hasTask)
            return "请先在刷题训练中选择一道可运行题目；选择后，编辑器和公开测试会针对当前题目建立。"
        if (app.currentTask && app.currentTask.environment_available === false)
            return app.currentTask.environment || "当前运行环境不满足这道题的要求。"
        var review = root.reviewAction()
        var retention = root.nextRetentionAction()
        if (review.state === "complete" && retention && root.primaryActionKind() === "blocked")
            return root.retentionBlockedText(retention)
        if (root.primaryActionKind() === "review")
            return "公开测试和提交已完成；现在开始自助复盘，补充实现解释、复杂度与边界证据。"
        if (root.primaryActionKind() === "submit")
            return "当前保存版本已通过公开测试，可以提交实现证据。"
        return "运行测试前会先保存编辑器中的最新代码。"
    }

    function displayTitle() {
        return app.problemTitle(root.activeProblemId,
                                app.currentTask.title || "选择一道题开始")
    }

    function displayTask() {
        if (app.language === "en") return app.currentTask.task || "Select a problem to begin."
        return app.problemStatement(root.activeProblemId,
                                app.currentTask.task || "请先从刷题训练中打开已解锁的题目。")
    }

    function runPrimaryAction() {
        var kind = root.primaryActionKind()
        if (kind === "no-task")
            app.navigate("learn")
        else if (kind === "review")
            reviewDialog.open()
        else if (kind === "retention")
            app.startRetentionFor(app.currentTask.problem_id, root.nextRetentionAction().stage)
        else if (kind === "submit")
            app.submitCurrent()
        else if (kind === "test")
            app.runTestsForCurrentSubmission(editor.text)
    }

    // TextArea bindings are intentionally broken once a learner types.  When
    // navigation opens another problem, explicitly rehydrate the editor from
    // the backend snapshot so the previous task's answer can never leak into
    // the new task.  The guard prevents this synchronization from being
    // mistaken for a learner edit.
    function syncEditorFromBackend() {
        if (!editor)
            return
        root.syncingEditor = true
        editor.text = app.submissionText || ""
        root.syncingEditor = false
    }
    function flushDraft() {
        if (!root.hasTask || !app.submissionDirty) return true
        if (editor.preeditText.length) return false
        // Closing saves editing state only; it never runs or submits code.
        return app.saveSubmission(editor.text)
    }

    onActiveProblemIdChanged: {
        root.showOriginalContract = false
        Qt.callLater(root.syncEditorFromBackend)
    }
    Component.onCompleted: Qt.callLater(root.syncEditorFromBackend)
    // A modal review left open while navigating away must never reappear on
    // the next exercise. Review is opened only by the explicit primary action.
    onVisibleChanged: if (visible) Qt.callLater(function() {
        if (reviewDialog.visible)
            reviewDialog.close()
    })

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Rectangle {
            visible: root.wideLayout || root.mediumLayout
            SplitView.preferredWidth: root.wideLayout ? Math.min(560, root.width * 0.38) : 300
            SplitView.minimumWidth: 248
            color: root.colors.surface
            border.color: "transparent"
            ScrollView {
                id: detailsScroll
                anchors.fill: parent; anchors.margins: 20; clip: true
                Column {
                    id: detailsColumn
                    width: detailsScroll.availableWidth; spacing: 12
                    LabText { theme: root.theme; width: parent.width; text: root.hasTask ? app.currentTask.problem_id : "尚未选择题目"; color: root.hasTask ? root.colors.accent : root.colors.muted; strong: true; font.pixelSize: root.theme.scaledPx(12) }
                    LabText { theme: root.theme; width: parent.width; text: root.displayTitle(); color: root.colors.text; font.pixelSize: root.theme.scaledPx(24); strong: true; wrapMode: Text.Wrap }
                    StatusPill { theme: root.theme; text: root.hasTask ? (app.currentTask.validation || "尚未开始") : "未选择"; tone: root.hasTask ? root.colors.success : root.colors.muted }
                    Rectangle { width: parent.width; height: 1; color: root.colors.border }
                    LabText { theme: root.theme; objectName: "practiceQuestionPrompt"; width: parent.width; text: app.renderMarkdown(root.displayTask(), root.theme.fontSection, root.theme.monospaceFontFamily); color: root.colors.text; font.pixelSize: root.theme.fontBodyLarge; wrapMode: Text.Wrap; textFormat: Text.RichText; lineHeight: 1.6 }
                    LabButton { theme: root.theme;
                        visible: app.language !== "en" && root.hasTask && !!app.currentTask.task && !root.sourceTaskChinese
                        text: root.showOriginalContract ? "隐藏英文题目" : "查看英文题目"
                        flat: true
                        palette.buttonText: root.colors.text
                        Layout.alignment: Qt.AlignLeft
                        onClicked: root.showOriginalContract = !root.showOriginalContract
                    }
                    LabText { theme: root.theme;
                        visible: root.showOriginalContract
                        width: parent.width
                        text: app.renderMarkdown(app.currentTask.task || "", root.theme.fontSection, root.theme.monospaceFontFamily)
                        color: root.colors.muted
                        wrapMode: Text.Wrap
                        textFormat: Text.RichText
                        lineHeight: 1.2
                    }
                    Rectangle { width: parent.width; height: 1; color: root.colors.border }
                    LabText { theme: root.theme; text: "掌握流程"; color: root.colors.text; strong: true }
                    LabText { theme: root.theme;
                        width: detailsColumn.width
                        text: root.actionExplanation()
                        color: root.primaryActionKind() === "blocked" ? root.colors.warning : root.colors.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: root.theme.scaledPx(12)
                    }
                }
            }
        }

        Rectangle {
            SplitView.fillWidth: true
                SplitView.minimumWidth: 380
            color: root.colors.background
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                Rectangle {
                    objectName: "exerciseToolbar"
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.theme.controlHeight + 8
                    radius: 0
                    color: "transparent"
                    border.color: "transparent"
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 2
                        LabText { theme: root.theme; text: "submission.py"; color: root.colors.text; strong: true; Layout.leftMargin: 4 }
                        Item { Layout.fillWidth: true }
                        // Reference panes remain available on compact layouts;
                        // wide screens keep the editor deliberately quiet.
                        LabButton { theme: root.theme;
                            visible: !root.wideLayout
                            text: "题面"
                            flat: true
                            palette.buttonText: root.colors.text
                            onClicked: detailsDrawer.open()
                        }
                        LabButton { theme: root.theme; text: "保存"; flat: true; palette.buttonText: root.colors.text; enabled: root.hasTask && !app.busy; onClicked: app.saveSubmission(editor.text) }
                        LabButton { objectName: "runPracticeScript"; theme: root.theme; text: "运行代码"; variant: "secondary"; enabled: root.hasTask && !app.busy; onClicked: app.runPracticeScript(editor.text, "") }
                    }
                }
                Rectangle {
                    objectName: "exerciseContextStrip"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    radius: 8
                    color: root.colors.surfaceAlt
                    border.color: root.colors.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10
                        LabText { theme: root.theme;
                            objectName: "exerciseContextLabel"
                            text: (app.currentTask.problem_id || "当前题目")
                                  + " · " + root.displayTitle()
                            color: root.colors.text
                            strong: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        StatusPill {
                            theme: root.theme
                            objectName: "exerciseContextStatus"
                            text: app.submissionDirty ? "未保存" : (app.testState || "未测试")
                            tone: app.submissionDirty ? root.colors.warning
                                  : app.testState === "测试通过" ? root.colors.success
                                  : root.colors.muted
                        }
                    }
                }
                Rectangle {
                    id: editorFrame
                    objectName: "exerciseEditorFrame"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: root.colors.surface
                    radius: root.theme.radiusMedium
                    border.color: "transparent"
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        Rectangle {
                            objectName: "exerciseEditorHeader"
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(32, root.theme.fontCaption + 16)
                            color: "transparent"
                            border.color: "transparent"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 12
                                spacing: 10
                                LabText { theme: root.theme; text: "Python"; color: root.colors.accent; strong: true; font.pixelSize: root.theme.scaledPx(12) }
                                LabText { theme: root.theme; text: "本地作答"; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12) }
                                Item { Layout.fillWidth: true }
                                LabText { theme: root.theme; text: app.submissionDirty ? "本地草稿 · 尚未保存" : "本地草稿 · 已保存"; color: app.submissionDirty ? root.colors.warning : root.colors.muted; font.pixelSize: root.theme.scaledPx(12) }
                            }
                        }
                        LabCodeEditor {
                            id: editor
                            objectName: "practiceCodeEditor"
                            theme: root.theme
                            Layout.fillWidth: true; Layout.fillHeight: true
                            text: app.submissionText
                            enabled: root.hasTask
                            readOnly: !root.hasTask
                            color: root.colors.text
                            selectionColor: root.colors.accent
                            font.family: root.codeFontFamily
                            font.pixelSize: root.theme.scaledPx(14)
                            wrapMode: TextEdit.NoWrap
                            tabStopDistance: 32
                            clip: true
                            Accessible.name: "Submission editor"
                            onTextChanged: if (!root.syncingEditor) app.updateSubmissionDraft(text)
                        }
                    }
                    Rectangle {
                        objectName: "exerciseNoTaskState"
                        visible: !root.hasTask
                        anchors.fill: parent
                        z: 2
                        color: root.colors.surface
                        opacity: 0.97
                        ColumnLayout {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 48, 360)
                            spacing: 10
                            LabText { theme: root.theme;
                                Layout.fillWidth: true
                                text: "还没有打开题目"
                                color: root.colors.text
                                font.pixelSize: root.theme.scaledPx(18)
                                strong: true
                                horizontalAlignment: Text.AlignHCenter
                            }
                            LabText { theme: root.theme;
                                Layout.fillWidth: true
                                text: "先从刷题训练选择一道可运行题目，编辑器和公开测试会自动绑定到当前作答。"
                                color: root.colors.muted
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                            LabButton { theme: root.theme;
                                objectName: "exerciseChooseProblem"
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredHeight: 40
                                text: "去刷题训练"
                                highlighted: true
                                palette.buttonText: "white"
                                onClicked: app.navigate("learn")
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    LabText { theme: root.theme;
                        visible: app.testedRevision.length > 0
                        text: "测试版本：" + app.testedRevision.slice(0, 12)
                        color: root.colors.muted
                        font.pixelSize: root.theme.scaledPx(12)
                    }
                    Item { Layout.fillWidth: true }
                    LabText { theme: root.theme; visible: app.submissionDirty; text: "未保存"; color: root.colors.warning; font.pixelSize: root.theme.scaledPx(12) }
                }
                Rectangle {
                    objectName: "exerciseTestOutput"
                    Layout.fillWidth: true
                    // Keep the initial workspace focused on the editor.  Once
                    // a real result exists the panel expands; long output is
                    // still constrained by the inner ScrollView.
                    Layout.preferredHeight: root.testResultExpanded
                                          ? (root.compactHeight ? 128 : 154)
                                          : (root.compactHeight ? 78 : 92)
                    Layout.minimumHeight: root.compactHeight ? 68 : 80
                    radius: 9
                    color: root.colors.surface
                    border.color: app.testState === "测试通过" ? root.colors.success
                                  : app.testState === "测试失败" || app.testState === "保存失败"
                                    ? root.colors.danger : root.colors.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        LabText { theme: root.theme;
                            objectName: "practiceOutputHeading"
                            text: "执行输出"
                            color: root.colors.muted
                            strong: true
                            font.pixelSize: root.theme.scaledPx(12)
                        }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            LabText { theme: root.theme;
                                width: parent.width
                                text: app.testOutput || "运行代码或公开测试后，结果会显示在这里。"
                                color: root.colors.text
                                font.family: root.codeFontFamily
                                font.pixelSize: root.theme.scaledPx(12)
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
                Rectangle {
                    objectName: "practiceNextAction"
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.compactHeight ? 62 : 70
                    radius: 9
                    color: root.colors.surface
                    border.color: root.primaryActionKind() === "blocked" ? root.colors.warning : root.colors.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 12
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            LabText { theme: root.theme;
                                text: root.primaryActionKind() === "blocked" ? "下一阶段暂不可用" : "下一步"
                                color: root.primaryActionKind() === "blocked" ? root.colors.warning : root.colors.accent
                                font.pixelSize: root.theme.scaledPx(12)
                                strong: true
                            }
                            LabText { theme: root.theme;
                                Layout.fillWidth: true
                                text: root.actionExplanation()
                                color: root.colors.text
                                font.pixelSize: root.theme.scaledPx(12)
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }
                        LabButton { theme: root.theme;
                            id: practicePrimaryButton
                            objectName: "practicePrimaryAction"
                            visible: root.primaryActionKind() !== "blocked"
                            text: root.primaryActionLabel()
                            highlighted: true
                            Layout.preferredWidth: 156
                            Layout.preferredHeight: 42
                            enabled: !app.busy
                            background: Rectangle {
                                radius: 8
                                color: practicePrimaryButton.enabled ? root.colors.accent : root.colors.border
                            }
                            contentItem: LabText { theme: root.theme;
                                text: practicePrimaryButton.text
                                color: practicePrimaryButton.enabled ? "white" : root.colors.muted
                                strong: true
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: root.runPrimaryAction()
                        }
                        LabButton { theme: root.theme;
                            objectName: "practiceBlockedNextAction"
                            visible: root.primaryActionKind() === "blocked"
                            text: "返回可做题目"
                            flat: true
                            palette.buttonText: root.colors.text
                            Layout.preferredWidth: 132
                            Layout.preferredHeight: 40
                            onClicked: app.navigate("learn")
                        }
                    }
                }
                LabText { theme: root.theme; text: "实现、审查与间隔复测会分别留证；一次测试通过不会直接授予已掌握。"; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12); wrapMode: Text.Wrap }
            }
        }

    }

    Drawer {
        id: detailsDrawer
        objectName: "exerciseDetailsDrawer"
        edge: Qt.LeftEdge
        width: Math.min(380, root.width * 0.82)
        height: root.height
        modal: true
        contentItem: ScrollView {
            anchors.fill: parent
            clip: true
            Column {
                x: 20
                width: parent.width - 40
                spacing: 12
                LabText { theme: root.theme; text: root.displayTitle(); color: root.colors.text; font.pixelSize: root.theme.scaledPx(24); strong: true; wrapMode: Text.Wrap; width: parent.width }
                LabText { theme: root.theme; text: app.renderMarkdown(root.displayTask(), root.theme.fontSection, root.theme.monospaceFontFamily); color: root.colors.text; font.pixelSize: root.theme.fontBodyLarge; wrapMode: Text.Wrap; textFormat: Text.RichText; width: parent.width }
                LabButton { theme: root.theme;
                    visible: app.language !== "en" && root.hasTask && !!app.currentTask.task && !root.sourceTaskChinese
                    text: root.showOriginalContract ? "隐藏英文题目" : "查看英文题目"
                    flat: true
                    palette.buttonText: root.colors.text
                    onClicked: root.showOriginalContract = !root.showOriginalContract
                }
                LabText { theme: root.theme; visible: root.showOriginalContract; text: app.renderMarkdown(app.currentTask.task || "", root.theme.fontSection, root.theme.monospaceFontFamily); color: root.colors.muted; wrapMode: Text.Wrap; textFormat: Text.RichText; width: parent.width }
            }
        }
    }


    LabStandardDialog { theme: root.theme;
        id: reviewDialog
        title: "自助复盘（非正式评审）"
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
                LabText { theme: root.theme; text: "这里记录你的自我复盘（source=self），用于准备后续正式审查；不会代替导师或 AI 评审，也不会直接授予“已掌握”。"; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                LabTextArea { id: explanation; theme: root.theme; Layout.fillWidth: true; Layout.preferredHeight: 80; placeholderText: "解释实现思路与不变式" }
                LabTextField { id: complexity; theme: root.theme; Layout.fillWidth: true; placeholderText: "时间与空间复杂度" }
                LabTextArea { id: boundaries; theme: root.theme; Layout.fillWidth: true; Layout.preferredHeight: 70; placeholderText: "边界情况、异常和输入不变性" }
            RowLayout {
                    LabCheckBox { theme: root.theme; id: contractPassed; text: "我已完成契约自检" }
                    LabCheckBox { theme: root.theme; id: oralPassed; text: "我已完成口述自答" }
            }
        }
    }
}
