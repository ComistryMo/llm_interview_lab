import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var palette
    contentWidth: width
    contentHeight: content.implicitHeight + 56
    clip: true

    ColumnLayout {
        id: content
        x: 28
        y: 24
        width: parent.width - 56
        spacing: 16

        Text { text: "本地求职材料"; color: root.palette.text; font.pixelSize: 24; font.bold: true }
        Text {
            Layout.fillWidth: true
            text: "简历、求职意向、项目、论文、比赛、真实面试问题和岗位 JD 保存在 Git 忽略的学习档案中。文件存在不代表 AI 可以读取。"
            color: root.palette.muted
            wrapMode: Text.Wrap
        }

        LabCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 238
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
            RowLayout {
                width: parent.width
                Text {
                    Layout.fillWidth: true
                    text: "PDF / DOCX 保持不可直接读取，不会发送给 AI。每场面试都会重新请求授权。"
                    color: root.palette.muted
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
                Button {
                    text: "复制到学习档案"
                    highlighted: true
                    enabled: selectedPath.text.length > 0
                    onClicked: {
                        app.addMaterial(filePicker.selectedFile.toString(), materialKind.currentValue || "other", materialTitle.text, aiAccess.checked)
                        materialTitle.text = ""
                        selectedPath.text = ""
                        aiAccess.checked = false
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
            Layout.preferredHeight: 110
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
                Layout.preferredHeight: 136
                cardColor: root.palette.surface
                borderColor: root.palette.border
                RowLayout {
                    width: parent.width
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 16 }
                        Text { text: modelData.id + " · " + modelData.kind; color: root.palette.accent }
                    }
                    StatusPill {
                        text: modelData.ai_access ? "可在逐场授权后供 AI 使用" : "仅保存在本机"
                        tone: modelData.ai_access ? root.palette.warning : root.palette.muted
                    }
                }
                Text {
                    width: parent.width
                    text: "SHA-256  " + modelData.sha256
                    color: root.palette.muted
                    font.family: "Cascadia Mono"
                    font.pixelSize: 11
                    wrapMode: Text.WrapAnywhere
                }
                Text { text: "内容不会被自动预览或上传。"; color: root.palette.muted; font.pixelSize: 12 }
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
