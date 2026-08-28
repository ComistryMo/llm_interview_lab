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
                    Text { width: parent.width; text: app.currentTask.problem_id || "暂无当前题目"; color: root.palette.accent; font.bold: true; font.pixelSize: 12 }
                    Text { width: parent.width; text: app.currentTask.title || "选择一道题开始"; color: root.palette.text; font.pixelSize: 21; font.bold: true; wrapMode: Text.Wrap }
                    StatusPill { text: app.currentTask.validation || "尚未开始"; tone: root.palette.success }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { width: parent.width; text: app.currentTask.task || "请先从刷题训练中打开已解锁的题目。"; color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; lineHeight: 1.25 }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                Text { text: "掌握流程"; color: root.palette.text; font.bold: true }
                Button { width: detailsColumn.width; text: "契约审查 + 口述答辩"; onClicked: reviewDialog.open() }
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
                    Button { text: "保存"; flat: true; onClicked: app.saveSubmission(editor.text) }
                    Button { text: "运行测试"; highlighted: true; enabled: !app.busy; onClicked: { app.saveSubmission(editor.text); app.runTests() } }
                    Button { text: "提交"; enabled: !app.busy; onClicked: app.submitCurrent() }
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
                        Text { width: parent.width; text: app.testOutput || "公开测试输出会显示在这里。"; color: root.palette.text; font.family: "Cascadia Mono, Consolas, monospace"; font.pixelSize: 12; wrapMode: Text.Wrap }
                    }
                }
                    Text { text: "公开测试通过只是实现证据，不等于已掌握。"; color: root.palette.warning; font.pixelSize: 12; font.bold: true }
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
                    Text { text: "AI 教练"; color: root.palette.text; font.bold: true; font.pixelSize: 17 }
                    Item { Layout.fillWidth: true }
                    Button { text: "×"; flat: true; onClicked: root.coachOpen = false }
                }
                Text { text: "遵守 H0–H5 帮助边界；AI 教练不能静默修改当前答案。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; font.pixelSize: 12 }
                ComboBox {
                    id: helpLevel
                    Layout.fillWidth: true
                    model: [
                        {id: "H1", label: "H1 · 文档 / 语法"},
                        {id: "H2", label: "H2 · 概念方向"},
                        {id: "H3", label: "H3 · 结构步骤"}
                    ]
                    textRole: "label"
                    valueRole: "id"
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: root.palette.surfaceAlt; radius: 8
                    ScrollView { anchors.fill: parent; anchors.margins: 10; Text { id: coachTranscript; width: parent.width; color: root.palette.text; wrapMode: Text.Wrap; text: "可以请求限定范围的提示或代码审查。\n" } }
                }
                TextArea { id: coachInput; Layout.fillWidth: true; Layout.preferredHeight: 76; placeholderText: "询问当前题目的概念、提示或审查……"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.background; radius: 8; border.color: root.palette.border } }
                CheckBox { id: shareSubmission; text: "在上下文预览中包含当前答案" }
                Button { text: "查看上下文预览"; Layout.fillWidth: true; onClicked: app.navigate("coach") }
            }
        }
    }

    Button {
        visible: !root.coachOpen
        anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14
            text: "AI 教练"
        onClicked: root.coachOpen = true
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
