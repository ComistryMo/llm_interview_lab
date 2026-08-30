import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    property bool compactLayout: width < 780
    contentWidth: width
    contentHeight: content.implicitHeight + 56
    clip: true
    ScrollBar.vertical: ScrollBar {
        width: 6
        policy: ScrollBar.AlwaysOn
        visible: root.contentHeight > root.height
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 3
            color: root.palette.muted
            opacity: 0.45
        }
    }

    function materialKindText(value) {
        return ({resume: "简历", career_intent: "求职意向", internship: "实习经历",
                 project: "项目经历", paper: "论文材料", competition: "比赛经历",
                 interview_question: "真实面试问题", job_description: "岗位 JD",
                 portfolio: "作品集", experience: "经历", research: "研究材料",
                 other: "其他"})[value] || value || "其他"
    }

    function materialSizeText(value) {
        var bytes = Number(value || 0)
        if (bytes < 1024)
            return bytes + " B"
        if (bytes < 1024 * 1024)
            return Math.round(bytes / 1024) + " KB"
        return (bytes / (1024 * 1024)).toFixed(1) + " MB"
    }

    ColumnLayout {
        id: content
        x: root.compactLayout ? 18 : 28
        y: root.compactLayout ? 18 : 24
        width: parent.width - (root.compactLayout ? 36 : 56)
        spacing: root.compactLayout ? 12 : 16

        // Main.qml already identifies this route.  Keep the page heading
        // focused on the user's next action instead of repeating it.
        Text {
            objectName: "careerRouteContext"
            text: "管理本地求职材料"
            color: root.palette.text
            font.pixelSize: 16
            font.bold: true
        }
        Text {
            Layout.fillWidth: true
            text: "简历、求职意向、项目、论文、比赛、真实面试问题和岗位 JD 保存在 Git 忽略的学习档案中。文件存在不代表 AI 可以读取。"
            color: root.palette.muted
            wrapMode: Text.Wrap
        }

        LabCard {
            Layout.fillWidth: true
            cardColor: root.palette.surface
            borderColor: root.palette.border
            Text { text: "添加一个明确文件"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: 12
                rowSpacing: 10
                ComboBox {
                    id: materialKind
                    Layout.fillWidth: true
                    model: [
                        {id:"resume", label:"简历"},
                        {id:"career_intent", label:"求职意向"},
                        {id:"internship", label:"实习经历"},
                        {id:"project", label:"项目经历"},
                        {id:"paper", label:"论文材料"},
                        {id:"competition", label:"比赛经历"},
                        {id:"interview_question", label:"真实面试问题"},
                        {id:"job_description", label:"岗位 JD"},
                        {id:"portfolio", label:"作品集"},
                        {id:"other", label:"其他"}
                    ]
                    textRole: "label"
                    valueRole: "id"
                }
                TextField { id: materialTitle; Layout.fillWidth: true; placeholderText: "标题（可选）" }
                TextField { id: selectedPath; Layout.fillWidth: true; readOnly: true; placeholderText: "选择 .md、.txt、.json、.yaml、.pdf 或 .docx" }
                Button { text: "选择文件"; onClicked: filePicker.open() }
            }
            CheckBox {
                id: aiAccess
                text: "允许在单次明确授权后把这个 UTF-8 文本文件加入 AI 上下文"
            }
            Flow {
                width: parent.width
                spacing: 8
                Text {
                    width: root.compactLayout ? parent.width : parent.width - 150
                    text: "PDF / DOCX 保持不可直接读取，不会发送给 AI。每场面试都会重新请求授权。"
                    color: root.palette.muted
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
                Button {
                    text: "复制到学习档案"
                    highlighted: true
                    enabled: selectedPath.text.length > 0 && !app.busy
                    onClicked: {
                        // Keep the form intact when validation, copying, or
                        // consent fails.  The controller returns a boolean so
                        // a failed import is immediately retryable.
                        var added = app.addMaterial(filePicker.selectedFile.toString(), materialKind.currentValue || "other", materialTitle.text, aiAccess.checked)
                        if (added) {
                            materialTitle.text = ""
                            selectedPath.text = ""
                            aiAccess.checked = false
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "材料清单"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
            Item { Layout.fillWidth: true }
            Text { text: app.materials.length + " 条本地记录"; color: root.palette.muted }
        }

        LabCard {
            visible: app.materials.length === 0
            Layout.fillWidth: true
            Layout.minimumHeight: 96
            cardColor: root.palette.surface
            borderColor: root.palette.border
            Text { text: "这个学习档案尚未添加材料。"; color: root.palette.text; font.bold: true }
            Text { text: "不添加材料也能使用固定课程和题库模拟面试。"; color: root.palette.muted }
        }

        Repeater {
            model: app.materials
            delegate: LabCard {
                required property var modelData
                Layout.fillWidth: true
                cardColor: root.palette.surface
                borderColor: root.palette.border
                ColumnLayout {
                    width: parent.width
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: modelData.title || "未命名材料"; color: root.palette.text; font.bold: true; font.pixelSize: 16; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { text: root.materialKindText(modelData.kind) + " · " + root.materialSizeText(modelData.size_bytes); color: root.palette.accent; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        StatusPill {
                            text: modelData.ai_access ? "可在逐场授权后供 AI 使用" : "仅保存在本机"
                            tone: modelData.ai_access ? root.palette.warning : root.palette.muted
                            Layout.alignment: Qt.AlignTop
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "文件已保存在本机；不会自动预览或上传。"; color: root.palette.muted; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        ToolButton {
                            id: detailsButton
                            text: details.visible ? "收起详情" : "查看文件详情"
                            onClicked: details.visible = !details.visible
                        }
                    }
                    ColumnLayout {
                        id: details
                        visible: false
                        width: parent.width
                        spacing: 3
                        Text { text: "材料 ID：" + modelData.id; color: root.palette.muted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: "相对路径：" + modelData.relative_path; color: root.palette.muted; font.pixelSize: 11; elide: Text.ElideMiddle; Layout.fillWidth: true }
                        Text { text: "SHA-256：" + modelData.sha256; color: root.palette.muted; font.family: "Cascadia Mono"; font.pixelSize: 10; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                    }
                }
            }
        }
    }

    FileDialog {
        id: filePicker
        title: "选择一份求职材料"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Supported files (*.md *.txt *.json *.yaml *.yml *.pdf *.docx)"]
        onAccepted: selectedPath.text = selectedFile.toString()
    }
}
