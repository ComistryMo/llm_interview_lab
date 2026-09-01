import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    // Keep the editor as the primary workspace.  The Coach drawer remains
    // available on demand, but opening it by default steals useful width from
    // a long coding session on wide monitors.
    property bool coachOpen: false
    // `width` is the page viewport after the shell/sidebar.  These thresholds
    // therefore map to a 1440px window for the three-column view and keep the
    // 900px minimum window on a single, usable editor surface.
    property bool wideLayout: width >= 1180
    // Only a completed test operation needs the expanded result viewport.
    // Save/retention notices stay compact so the editor and primary action
    // remain visible on a first visit.
    property bool testResultExpanded: ["测试通过", "测试失败", "保存失败", "结果已过期"].indexOf(app.testState) >= 0
    property bool mediumLayout: width >= 820
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
        return app.problemBrief(root.activeProblemId,
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
            SplitView.preferredWidth: root.wideLayout ? 330 : 300
            SplitView.minimumWidth: 248
            color: root.palette.surface
            border.color: root.palette.border
            ScrollView {
                id: detailsScroll
                anchors.fill: parent; anchors.margins: 20; clip: true
                Column {
                    id: detailsColumn
                    width: detailsScroll.availableWidth; spacing: 12
                    Text { width: parent.width; text: root.hasTask ? app.currentTask.problem_id : "尚未选择题目"; color: root.hasTask ? root.palette.accent : root.palette.muted; font.bold: true; font.pixelSize: 12 }
                    Text { width: parent.width; text: root.displayTitle(); color: root.palette.text; font.pixelSize: 21; font.bold: true; wrapMode: Text.Wrap }
                    StatusPill { text: root.hasTask ? (app.currentTask.validation || "尚未开始") : "未选择"; tone: root.hasTask ? root.palette.success : root.palette.muted }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { width: parent.width; text: root.displayTask(); color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; lineHeight: 1.25 }
                    Button {
                        visible: app.language !== "en" && root.hasTask && !!app.currentTask.task
                        text: root.showOriginalContract ? "隐藏英文题目" : "查看英文题目"
                        flat: true
                        palette.buttonText: root.palette.text
                        Layout.alignment: Qt.AlignLeft
                        onClicked: root.showOriginalContract = !root.showOriginalContract
                    }
                    Text {
                        visible: root.showOriginalContract
                        width: parent.width
                        text: app.currentTask.task || ""
                        color: root.palette.muted
                        wrapMode: Text.Wrap
                        textFormat: Text.MarkdownText
                        lineHeight: 1.2
                    }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { text: "掌握流程"; color: root.palette.text; font.bold: true }
                    Text {
                        width: detailsColumn.width
                        text: root.actionExplanation()
                        color: root.primaryActionKind() === "blocked" ? root.palette.warning : root.palette.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                }
            }
        }

        Rectangle {
            SplitView.fillWidth: true
                SplitView.minimumWidth: 380
            color: root.palette.background
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                Rectangle {
                    objectName: "exerciseToolbar"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 42
                    radius: 10
                    color: root.palette.surfaceAlt
                    border.color: root.palette.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 2
                        Text { text: "submission.py"; color: root.palette.text; font.bold: true; Layout.leftMargin: 4 }
                        Item { Layout.fillWidth: true }
                        // Reference panes remain available on compact layouts;
                        // wide screens keep the editor deliberately quiet.
                        Button {
                            visible: !root.wideLayout
                            text: "题面"
                            flat: true
                            palette.buttonText: root.palette.text
                            onClicked: detailsDrawer.open()
                        }
                        Button {
                            visible: !root.wideLayout || !root.coachOpen
                            text: "AI 辅助（可选）"
                            flat: true
                            palette.buttonText: root.palette.text
                            onClicked: root.wideLayout ? root.coachOpen = true : coachDrawer.open()
                        }
                        Button { text: "保存"; flat: true; palette.buttonText: root.palette.text; enabled: root.hasTask && !app.busy; onClicked: app.saveSubmission(editor.text) }
                    }
                }
                Rectangle {
                    objectName: "exerciseContextStrip"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    radius: 8
                    color: root.palette.surfaceAlt
                    border.color: root.palette.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10
                        Text {
                            objectName: "exerciseContextLabel"
                            text: (app.currentTask.problem_id || "当前题目")
                                  + " · " + root.displayTitle()
                            color: root.palette.text
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        StatusPill {
                            objectName: "exerciseContextStatus"
                            text: app.submissionDirty ? "未保存" : (app.testState || "未测试")
                            tone: app.submissionDirty ? root.palette.warning
                                  : app.testState === "测试通过" ? root.palette.success
                                  : root.palette.muted
                        }
                    }
                }
                Rectangle {
                    id: editorFrame
                    objectName: "exerciseEditorFrame"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: root.palette.surface
                    radius: 9
                    border.color: editor.activeFocus ? root.palette.accent : root.palette.border
                    border.width: editor.activeFocus ? 2 : 1
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        Rectangle {
                            objectName: "exerciseEditorHeader"
                            Layout.fillWidth: true
                            Layout.preferredHeight: 30
                            color: root.palette.surfaceAlt
                            border.color: root.palette.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 12
                                spacing: 10
                                Text { text: "Python"; color: root.palette.accent; font.bold: true; font.pixelSize: 11 }
                                Text { text: "纯文本编辑"; color: root.palette.muted; font.pixelSize: 11 }
                                Item { Layout.fillWidth: true }
                                Text { text: app.submissionDirty ? "本地草稿 · 尚未保存" : "本地草稿 · 已保存"; color: app.submissionDirty ? root.palette.warning : root.palette.muted; font.pixelSize: 11 }
                            }
                        }
                        TextArea {
                            id: editor
                            Layout.fillWidth: true; Layout.fillHeight: true
                            text: app.submissionText
                            enabled: root.hasTask
                            readOnly: !root.hasTask
                            color: root.palette.text
                            selectionColor: root.palette.accent
                            font.family: root.codeFontFamily
                            font.pixelSize: 14
                            wrapMode: TextEdit.NoWrap
                            tabStopDistance: 32
                            padding: 12
                            clip: true
                            background: Rectangle { color: "transparent" }
                            Accessible.name: "Submission editor"
                            onTextChanged: if (!root.syncingEditor) app.updateSubmissionDraft(text)
                        }
                    }
                    // A quiet rail makes the editor boundary legible without
                    // pretending to render a second, non-interactive editor.
                    Rectangle {
                        x: 0; y: 30; width: 3
                        height: Math.max(0, parent.height - 30)
                        color: root.palette.accent
                        opacity: 0.72
                    }
                    Rectangle {
                        objectName: "exerciseNoTaskState"
                        visible: !root.hasTask
                        anchors.fill: parent
                        z: 2
                        color: root.palette.surface
                        opacity: 0.97
                        ColumnLayout {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 48, 360)
                            spacing: 10
                            Text {
                                Layout.fillWidth: true
                                text: "还没有打开题目"
                                color: root.palette.text
                                font.pixelSize: 18
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "先从刷题训练选择一道可运行题目，编辑器和公开测试会自动绑定到当前作答。"
                                color: root.palette.muted
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Button {
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
                    Text {
                        visible: app.testedRevision.length > 0
                        text: "测试版本：" + app.testedRevision.slice(0, 12)
                        color: root.palette.muted
                        font.pixelSize: 11
                    }
                    Item { Layout.fillWidth: true }
                    Text { visible: app.submissionDirty; text: "未保存"; color: root.palette.warning; font.pixelSize: 11 }
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
                    color: root.palette.surface
                    border.color: app.testState === "测试通过" ? root.palette.success
                                  : app.testState === "测试失败" || app.testState === "保存失败"
                                    ? root.palette.danger : root.palette.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Text {
                            text: "公开测试输出"
                            color: root.palette.muted
                            font.bold: true
                            font.pixelSize: 11
                        }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            Text {
                                width: parent.width
                                text: app.testOutput || "运行公开测试后，结果会显示在这里。"
                                color: root.palette.text
                                font.family: root.codeFontFamily
                                font.pixelSize: 12
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
                    color: root.palette.surface
                    border.color: root.primaryActionKind() === "blocked" ? root.palette.warning : root.palette.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 12
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: root.primaryActionKind() === "blocked" ? "下一阶段暂不可用" : "下一步"
                                color: root.primaryActionKind() === "blocked" ? root.palette.warning : root.palette.accent
                                font.pixelSize: 11
                                font.bold: true
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.actionExplanation()
                                color: root.palette.text
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }
                        Button {
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
                                color: practicePrimaryButton.enabled ? root.palette.accent : root.palette.border
                            }
                            contentItem: Text {
                                text: practicePrimaryButton.text
                                color: practicePrimaryButton.enabled ? "white" : root.palette.muted
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: root.runPrimaryAction()
                        }
                        Button {
                            objectName: "practiceBlockedNextAction"
                            visible: root.primaryActionKind() === "blocked"
                            text: "返回可做题目"
                            flat: true
                            palette.buttonText: root.palette.text
                            Layout.preferredWidth: 132
                            Layout.preferredHeight: 40
                            onClicked: app.navigate("learn")
                        }
                    }
                }
                Text { text: "实现、审查与间隔复测会分别留证；一次测试通过不会直接授予已掌握。"; color: root.palette.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
            }
        }

        Rectangle {
            visible: root.wideLayout && root.coachOpen
            SplitView.preferredWidth: root.coachOpen ? 310 : 0
            SplitView.minimumWidth: root.coachOpen ? 270 : 0
            color: root.palette.surface
            border.color: root.palette.border
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "AI 辅助（可选）"; color: root.palette.text; font.bold: true; font.pixelSize: 17 }
                    Item { Layout.fillWidth: true }
                    Button { text: "×"; flat: true; onClicked: root.coachOpen = false }
                }
                Text { text: "遵守 H0–H5 帮助边界；AI 辅助不会静默修改当前答案。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; font.pixelSize: 12 }
                Text {
                    Layout.fillWidth: true
                    text: "需要提示或只读审查时，再打开 AI 辅助页面。模拟面试请进入“模拟面试”；本页不会自动占用训练流程。"
                    color: root.palette.text
                    wrapMode: Text.Wrap
                }
                Item { Layout.fillHeight: true }
                Button { text: "在 AI 教练中打开当前任务（可选）"; Layout.fillWidth: true; onClicked: app.navigate("coach") }
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
                Text { text: root.displayTitle(); color: root.palette.text; font.pixelSize: 20; font.bold: true; wrapMode: Text.Wrap; width: parent.width }
                Text { text: root.displayTask(); color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; width: parent.width }
                Button {
                    visible: app.language !== "en" && root.hasTask && !!app.currentTask.task
                    text: root.showOriginalContract ? "隐藏英文题目" : "查看英文题目"
                    flat: true
                    palette.buttonText: root.palette.text
                    onClicked: root.showOriginalContract = !root.showOriginalContract
                }
                Text { visible: root.showOriginalContract; text: app.currentTask.task || ""; color: root.palette.muted; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; width: parent.width }
            }
        }
    }

    Drawer {
        id: coachDrawer
        objectName: "exerciseCoachDrawer"
        edge: Qt.RightEdge
        width: Math.min(380, root.width * 0.82)
        height: root.height
        modal: true
        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12
            Text { text: "AI 辅助（可选）"; color: root.palette.text; font.pixelSize: 20; font.bold: true }
            Text { text: "模拟面试请进入“模拟面试”。这里仅提供主动请求的解释和只读审查，不会自动修改答案。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Button { text: "打开 AI 辅助页面"; Layout.fillWidth: true; onClicked: { coachDrawer.close(); app.navigate("coach") } }
            Item { Layout.fillHeight: true }
        }
    }

    Dialog {
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
                Text { text: "这里记录你的自我复盘（source=self），用于准备后续正式审查；不会代替导师或 AI 评审，也不会直接授予“已掌握”。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                TextArea { id: explanation; Layout.fillWidth: true; Layout.preferredHeight: 80; placeholderText: "解释实现思路与不变式"; wrapMode: Text.Wrap }
                TextField { id: complexity; Layout.fillWidth: true; placeholderText: "时间与空间复杂度" }
                TextArea { id: boundaries; Layout.fillWidth: true; Layout.preferredHeight: 70; placeholderText: "边界情况、异常和输入不变性"; wrapMode: Text.Wrap }
            RowLayout {
                    CheckBox { id: contractPassed; text: "我已完成契约自检" }
                    CheckBox { id: oralPassed; text: "我已完成口述自答" }
            }
        }
    }
}
