import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    required property var app
    required property var colors
    required property var theme
    property bool compactLayout: width < 780
    contentWidth: width
    contentHeight: content.implicitHeight + 56
    clip: true
    // PDF/DOCX keep their original binary file and, when text is extractable,
    // receive a SHA-bound UTF-8 snapshot inside the same ignored Profile.
    readonly property bool selectedOpaqueMaterial: {
        var value = String(selectedPath.text || "").toLowerCase()
        return value.endsWith(".pdf") || value.endsWith(".docx")
    }
    ScrollBar.vertical: ScrollBar {
        width: 6
        policy: ScrollBar.AlwaysOn
        visible: root.contentHeight > root.height
        contentItem: Rectangle {
            implicitWidth: 5
            radius: 3
            color: root.colors.muted
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
        x: (root.width - width) / 2
        y: root.compactLayout ? 18 : 24
        width: Math.min(root.theme.listWidth, parent.width - (root.compactLayout ? 36 : 56))
        spacing: 24

        // Main.qml already identifies this route.  Keep the page heading
        // focused on the user's next action instead of repeating it.
        LabText { theme: root.theme;
            objectName: "careerRouteContext"
            text: "管理本地求职材料"
            color: root.colors.text
            font.pixelSize: root.theme.scaledPx(18)
            strong: true
        }
        LabText { theme: root.theme;
            Layout.fillWidth: true
            text: "简历、求职意向、项目、论文、比赛、真实面试问题和岗位 JD 保存在 Git 忽略的学习档案中。文件存在不代表 AI 可以读取。"
            color: root.colors.muted
            wrapMode: Text.Wrap
        }

        LabCard {
            Layout.fillWidth: true
            Layout.maximumWidth: root.theme.formWidth
            theme: root.theme
            padding: 0
            cardColor: root.theme.canvas
            borderColor: "transparent"
            LabText { theme: root.theme; text: "添加一个明确文件"; color: root.colors.text; font.pixelSize: root.theme.scaledPx(18); strong: true }
            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: 12
                rowSpacing: 10
                LabText { theme: root.theme; text: "材料类型"; variant: "caption"; tone: "muted" }
                LabText { theme: root.theme; text: "标题（可选）"; variant: "caption"; tone: "muted" }
                LabComboBox { theme: root.theme;
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
                LabTextField { id: materialTitle; theme: root.theme; Layout.fillWidth: true; accessibleLabel: "材料标题"; placeholderText: "例如：项目经历与岗位 JD" }
                LabText { theme: root.theme; text: "文件路径"; Layout.columnSpan: 2; variant: "caption"; tone: "muted" }
                LabTextField { id: selectedPath; theme: root.theme; Layout.fillWidth: true; readOnly: true; placeholderText: "选择 .md、.txt、.json、.yaml、.pdf 或 .docx" }
                LabButton { theme: root.theme; text: "选择文件"; onClicked: filePicker.open() }
            }
            LabCheckBox { theme: root.theme;
                id: aiAccess
                width: parent.width
                objectName: "materialAiAccess"
                enabled: selectedPath.text.length > 0
                         && !app.busy
                text: root.selectedOpaqueMaterial
                      ? "允许提取 SHA 绑定的只读文本快照，并在逐场确认后供 AI 使用"
                      : "允许在单次明确授权后把这个 UTF-8 文本文件加入 AI 上下文"
            }
            LabText { theme: root.theme;
                objectName: "materialAiCapabilityNotice"
                visible: selectedPath.text.length > 0 && root.selectedOpaqueMaterial
                width: parent.width
                text: "文本型 PDF 会提取正文；DOCX 会提取段落和表格。扫描 PDF 暂不 OCR，无法提取时仍可仅保存在本机，但不能授权给 AI。"
                color: root.colors.muted
                font.pixelSize: root.theme.scaledPx(12)
                wrapMode: Text.Wrap
            }
            Flow {
                width: parent.width
                spacing: 8
                LabText { theme: root.theme;
                    width: root.compactLayout ? parent.width : parent.width - 150
                    text: "原文件和文本快照都只保存在当前学习档案；每场面试仍会展示 ID、用途与 SHA 并重新请求授权。"
                    color: root.colors.muted
                    font.pixelSize: root.theme.scaledPx(12)
                    wrapMode: Text.Wrap
                }
                LabButton { theme: root.theme;
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
            LabText { theme: root.theme; text: "材料清单"; color: root.colors.text; font.pixelSize: root.theme.scaledPx(18); strong: true }
            Item { Layout.fillWidth: true }
            LabText { theme: root.theme; text: app.materials.length + " 条本地记录"; color: root.colors.muted }
        }

        LabCard {
            visible: app.materials.length === 0
            Layout.fillWidth: true
            Layout.minimumHeight: 96
            cardColor: root.colors.surface
            borderColor: root.colors.border
            LabText { theme: root.theme; text: "这个学习档案尚未添加材料。"; color: root.colors.text; strong: true }
            LabText { theme: root.theme; text: "不添加材料也能使用固定课程和题库模拟面试。"; color: root.colors.muted }
        }

        Repeater {
            model: app.materials
            delegate: LabCard {
                required property var modelData
                Layout.fillWidth: true
                cardColor: root.colors.surface
                borderColor: root.colors.border
                ColumnLayout {
                    width: parent.width
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            LabText { theme: root.theme; text: modelData.title || "未命名材料"; color: root.colors.text; strong: true; font.pixelSize: root.theme.scaledPx(18); elide: Text.ElideRight; Layout.fillWidth: true }
                            LabText { theme: root.theme; text: root.materialKindText(modelData.kind) + " · " + root.materialSizeText(modelData.size_bytes); color: root.colors.accent; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        StatusPill { theme: root.theme;
                            text: modelData.ai_access ? "可在逐场授权后供 AI 使用" : "仅保存在本机"
                            tone: modelData.ai_access ? root.colors.warning : root.colors.muted
                            Layout.alignment: Qt.AlignTop
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        LabText { theme: root.theme; text: "文件已保存在本机；不会自动预览或上传。"; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12); Layout.fillWidth: true; wrapMode: Text.Wrap }
                        LabButton { theme: root.theme; variant: "ghost";
                            id: detailsButton
                            text: details.visible ? "收起详情" : "查看文件详情"
                            onClicked: details.visible = !details.visible
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        LabCheckBox { theme: root.theme;
                            id: materialAiAccessToggle
                            objectName: "materialAiAccessToggle"
                            checked: !!modelData.ai_access
                            enabled: !app.busy
                            text: "允许在逐场授权后供 AI 使用"
                            Accessible.name: text
                            onClicked: {
                                var desired = checked
                                if (!app.setMaterialAiAccess(modelData.id, desired))
                                    checked = !desired
                            }
                        }
                        LabText { theme: root.theme;
                            Layout.fillWidth: true
                            text: modelData.ai_access
                                  ? "已开启；每场面试仍需用户明确同意。"
                                  : "仅保存在本机，未授权给 AI。"
                            color: root.colors.muted
                            font.pixelSize: root.theme.scaledPx(12)
                            wrapMode: Text.Wrap
                        }
                    }
                    ColumnLayout {
                        id: details
                        visible: false
                        width: parent.width
                        spacing: 3
                        LabText { theme: root.theme; text: "材料 ID：" + modelData.id; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12); elide: Text.ElideRight; Layout.fillWidth: true }
                        LabText { theme: root.theme; text: "相对路径：" + modelData.relative_path; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12); elide: Text.ElideMiddle; Layout.fillWidth: true }
                        LabText { theme: root.theme; text: "SHA-256：" + modelData.sha256; color: root.colors.muted; font.family: "Cascadia Mono"; font.pixelSize: root.theme.scaledPx(12); wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                        LabText { theme: root.theme;
                            visible: !!modelData.text_snapshot
                            text: {
                                var snapshot = modelData.text_snapshot || ({})
                                return "文本快照：" + (snapshot.format || "未知格式")
                                      + " · " + (snapshot.sha256 || "未记录")
                            }
                            color: root.colors.muted
                            font.pixelSize: root.theme.scaledPx(12)
                            wrapMode: Text.WrapAnywhere
                            Layout.fillWidth: true
                        }
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
        onAccepted: {
            selectedPath.text = selectedFile.toString()
            // Consent is always explicit for the newly selected file. PDF /
            // DOCX extraction runs only after the user chooses the checkbox.
            aiAccess.checked = false
        }
    }
}
