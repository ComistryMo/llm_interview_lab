import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property bool coachOpen: true
    property bool focusMode: false
    property bool wideLayout: width >= 1260
    property bool mediumLayout: width >= 1050
    property var actions: (app.currentTask && app.currentTask.actions) || ({})
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
        if (app.currentTask && app.currentTask.environment_available === false)
            return "blocked"
        var review = root.reviewAction()
        if (review.actionable === true)
            return "review"
        if (review.state && review.state !== "complete")
            return "blocked"
        var retention = root.nextRetentionAction()
        if (retention) {
            if ((retention.state === "due" || retention.state === "in_progress")
                    && retention.actionable === true)
                return "retention"
            return "blocked"
        }
        if (root.canSubmitCurrent())
            return "submit"
        return "test"
    }

    function primaryActionLabel() {
        var kind = root.primaryActionKind()
        if (kind === "review")
            return "开始契约审查"
        if (kind === "retention")
            return "开始 " + (root.nextRetentionAction().stage || "复测").toUpperCase()
        if (kind === "submit")
            return "提交实现"
        return "运行公开测试"
    }

    function actionExplanation() {
        if (app.currentTask && app.currentTask.environment_available === false)
            return app.currentTask.environment || "当前运行环境不满足这道题的要求。"
        var review = root.reviewAction()
        if (review.state && review.state !== "complete" && root.primaryActionKind() === "blocked")
            return review.blocked_reason || "请先完成实现提交，再进入契约审查。"
        var retention = root.nextRetentionAction()
        if (retention && root.primaryActionKind() === "blocked")
            return root.retentionBlockedText(retention)
        if (root.primaryActionKind() === "review")
            return "公开测试和提交已完成；现在补充实现解释、复杂度与边界证据。"
        if (root.primaryActionKind() === "submit")
            return "当前保存版本已通过公开测试，可以提交实现证据。"
        return "运行测试前会先保存编辑器中的最新代码。"
    }

    function runPrimaryAction() {
        var kind = root.primaryActionKind()
        if (kind === "review")
            reviewDialog.open()
        else if (kind === "retention")
            app.startRetentionFor(app.currentTask.problem_id, root.nextRetentionAction().stage)
        else if (kind === "submit")
            app.submitCurrent()
        else if (kind === "test")
            app.runTestsForCurrentSubmission(editor.text)
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Rectangle {
            visible: root.wideLayout || (root.mediumLayout && !root.focusMode)
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
                    Text { width: parent.width; text: app.currentTask.problem_id || "暂无当前题目"; color: root.palette.accent; font.bold: true; font.pixelSize: 12 }
                    Text { width: parent.width; text: app.currentTask.title || "选择一道题开始"; color: root.palette.text; font.pixelSize: 21; font.bold: true; wrapMode: Text.Wrap }
                    StatusPill { text: app.currentTask.validation || "尚未开始"; tone: root.palette.success }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { width: parent.width; text: app.currentTask.task || "请先从刷题训练中打开已解锁的题目。"; color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; lineHeight: 1.25 }
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
            SplitView.minimumWidth: 420
            color: root.palette.background
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "submission.py"; color: root.palette.text; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Button { visible: !root.wideLayout && !root.focusMode; text: "题面"; onClicked: detailsDrawer.open() }
                    Button {
                        visible: !root.focusMode && (!root.wideLayout || !root.coachOpen)
                        text: "AI 教练"
                        onClicked: root.wideLayout ? root.coachOpen = true : coachDrawer.open()
                    }
                    Button { text: root.focusMode ? "退出专注" : "专注编码"; onClicked: root.focusMode = !root.focusMode }
                    Button { text: "保存"; flat: true; onClicked: app.saveSubmission(editor.text) }
                }
                TextArea {
                    id: editor
                    Layout.fillWidth: true; Layout.fillHeight: true
                    text: app.submissionText
                    color: root.palette.text
                    selectionColor: root.palette.accent
                    font.family: root.codeFontFamily
                    font.pixelSize: 14
                    wrapMode: TextEdit.NoWrap
                    tabStopDistance: 32
                    padding: 12
                    clip: true
                    background: Rectangle { color: root.palette.surface; radius: 9; border.color: root.palette.border }
                    Accessible.name: "Submission editor"
                    onTextChanged: app.updateSubmissionDraft(text)
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: app.testState || "未测试"
                        color: app.testState === "测试通过" ? root.palette.success
                               : app.testState === "测试失败" || app.testState === "保存失败" ? root.palette.danger
                               : app.testState === "结果已过期" ? root.palette.warning : root.palette.muted
                        font.pixelSize: 12
                        font.bold: true
                    }
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
                    Layout.fillWidth: true; Layout.preferredHeight: 154; radius: 9
                    color: root.palette.surface; border.color: root.palette.border
                    ScrollView {
                        anchors.fill: parent; anchors.margins: 12; clip: true
                        Text { width: parent.width; text: app.testOutput || "公开测试输出会显示在这里。"; color: root.palette.text; font.family: root.codeFontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                    }
                }
                Rectangle {
                    objectName: "practiceNextAction"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 70
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
                            objectName: "practicePrimaryAction"
                            visible: root.primaryActionKind() !== "blocked"
                            text: root.primaryActionLabel()
                            highlighted: true
                            enabled: !app.busy
                            onClicked: root.runPrimaryAction()
                        }
                        StatusPill {
                            visible: root.primaryActionKind() === "blocked"
                            text: "已说明原因"
                            tone: root.palette.warning
                        }
                    }
                }
                Text { text: "实现、审查与间隔复测会分别留证；一次测试通过不会直接授予已掌握。"; color: root.palette.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
            }
        }

        Rectangle {
            visible: root.wideLayout && root.coachOpen && !root.focusMode
            SplitView.preferredWidth: root.coachOpen ? 310 : 0
            SplitView.minimumWidth: root.coachOpen ? 270 : 0
            color: root.palette.surface
            border.color: root.palette.border
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "AI 教练"; color: root.palette.text; font.bold: true; font.pixelSize: 17 }
                    Item { Layout.fillWidth: true }
                    Button { text: "×"; flat: true; onClicked: root.coachOpen = false }
                }
                Text { text: "遵守 H0–H5 帮助边界；AI 教练不能静默修改当前答案。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; font.pixelSize: 12 }
                Text {
                    Layout.fillWidth: true
                    text: "需要提示或只读审查时，在 AI 教练页面打开当前任务。该页面提供真实的发送、停止与上下文预览。"
                    color: root.palette.text
                    wrapMode: Text.Wrap
                }
                Item { Layout.fillHeight: true }
                Button { text: "在 AI 教练中打开当前任务"; Layout.fillWidth: true; onClicked: app.navigate("coach") }
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
            clip: true
            Column {
                x: 20
                width: parent.width - 40
                spacing: 12
                Text { text: app.currentTask.title || "题面"; color: root.palette.text; font.pixelSize: 20; font.bold: true; wrapMode: Text.Wrap; width: parent.width }
                Text { text: app.currentTask.task || "暂无题面"; color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; width: parent.width }
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
            spacing: 12
            Text { text: "AI 教练"; color: root.palette.text; font.pixelSize: 20; font.bold: true }
            Text { text: "AI 只提供解释和审查，不会自动修改答案。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Button { text: "打开 AI 教练页面"; Layout.fillWidth: true; onClicked: { coachDrawer.close(); app.navigate("coach") } }
            Item { Layout.fillHeight: true }
        }
    }

    Dialog {
        id: reviewDialog
        title: "契约审查与口述答辩"
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
                Text { text: "审查只记录证据，不能跳过 D+2 / D+7，也不能直接授予“已掌握”。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                TextArea { id: explanation; Layout.fillWidth: true; Layout.preferredHeight: 80; placeholderText: "解释实现思路与不变式"; wrapMode: Text.Wrap }
                TextField { id: complexity; Layout.fillWidth: true; placeholderText: "时间与空间复杂度" }
                TextArea { id: boundaries; Layout.fillWidth: true; Layout.preferredHeight: 70; placeholderText: "边界情况、异常和输入不变性"; wrapMode: Text.Wrap }
            RowLayout {
                    CheckBox { id: contractPassed; text: "契约审查通过" }
                    CheckBox { id: oralPassed; text: "口述答辩通过" }
            }
        }
    }
}
