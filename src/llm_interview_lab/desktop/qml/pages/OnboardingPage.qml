import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    required property var app
    required property var palette
    color: root.palette.background
    property int step: 0
    property string selectedRole: app.roles.length ? app.roles[3].id : "ai_algorithm_research_engineer"
    property var selectedRoleCard: {
        for (var i = 0; i < app.roles.length; ++i)
            if (app.roles[i].id === selectedRole) return app.roles[i]
        return null
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 900)
        height: Math.min(parent.height - 60, 690)
        spacing: 18

        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                width: 42; height: 42; radius: 11; color: root.palette.accent
                Text { anchors.centerIn: parent; text: "LL"; color: "white"; font.bold: true }
            }
            ColumnLayout {
                spacing: 2
                Text { text: "设置本地 AI 面试训练工作台"; color: root.palette.text; font.pixelSize: 25; font.bold: true }
                Text { text: "最多四步，之后可以随时修改。"; color: root.palette.muted; font.pixelSize: 14 }
            }
            Item { Layout.fillWidth: true }
            Text { text: (step + 1) + " / 4"; color: root.palette.muted; font.bold: true }
        }

        ProgressBar { Layout.fillWidth: true; value: (step + 1) / 4 }

        LabCard {
            Layout.fillWidth: true; Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            StackLayout {
                width: parent.width; height: parent.height; currentIndex: root.step

                ColumnLayout {
                    spacing: 16
                    Text { text: "创建学习档案"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "刷题记录、答案、面试报告和求职材料都保存在这个本地学习档案中。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    TextField { id: profileName; Layout.fillWidth: true; placeholderText: "档案名称"; text: "default"; maximumLength: 64; focus: true }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 74; radius: 8; color: root.palette.surfaceAlt
                        Text { anchors.fill: parent; anchors.margins: 14; text: "默认保护隐私\nworkspace/profiles/<id>/ 会被 Git 忽略；连接 AI 不是必选项。"; color: root.palette.text; wrapMode: Text.Wrap }
                    }
                    Item { Layout.fillHeight: true }
                }

                ColumnLayout {
                    spacing: 12
                    Text { text: "选择目标岗位"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "岗位会影响技能权重、推荐闯关路线和面试蓝图，不会改变公共课程事实。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        GridLayout {
                            width: parent.width; columns: 2; columnSpacing: 12; rowSpacing: 12
                            Repeater {
                                model: app.roles
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true; Layout.preferredHeight: 118
                                    radius: 10
                                    color: root.selectedRole === modelData.id ? Qt.rgba(0.145, 0.388, 0.922, 0.12) : root.palette.surfaceAlt
                                    border.color: root.selectedRole === modelData.id ? root.palette.accent : root.palette.border
                                    border.width: root.selectedRole === modelData.id ? 2 : 1
                                    Column {
                                        anchors.fill: parent; anchors.margins: 13; spacing: 4
                                        Text { text: modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 15 }
                                        Text { width: parent.width; text: modelData.summary; color: root.palette.muted; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                        Text { width: parent.width; text: modelData.interview_content || "结构化问答与能力验证"; color: root.palette.accent; font.pixelSize: 11; elide: Text.ElideRight }
                                    }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.selectedRole = modelData.id }
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    spacing: 16
                    Text { text: "能力自评"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "只展示与目标岗位最相关的技能，用于改善推荐；自评不会授予“已掌握”。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Repeater {
                        id: assessmentRepeater
                        model: root.selectedRoleCard ? root.selectedRoleCard.top_skills.slice(0, 8) : []
                        delegate: RowLayout {
                            required property var modelData
                            property string skillId: modelData.id
                            property int level: Math.round(levelSlider.value)
                            Layout.fillWidth: true
                            Text { text: modelData.title; color: root.palette.text; Layout.preferredWidth: 220; elide: Text.ElideRight }
                            Slider { id: levelSlider; Layout.fillWidth: true; from: 0; to: 4; stepSize: 1; value: 1 }
                            Text { text: "0 · 1 · 2 · 3 · 4"; color: root.palette.muted; font.pixelSize: 11 }
                        }
                    }
                    CheckBox { id: skipAssessment; text: "跳过，从基础开始"; checked: true }
                    RowLayout {
                        Text { text: "求职阶段"; color: root.palette.muted }
                        ComboBox { id: seniority; Layout.preferredWidth: 220; model: ["实习", "校招", "有经验", "高级"]; currentIndex: 1 }
                    }
                    Item { Layout.fillHeight: true }
                }

                ColumnLayout {
                    spacing: 16
                    Text { text: "选择是否连接 AI"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "默认不连接 AI。之后仍可从“AI 连接”页面添加 Codex 或自己的 LLM API。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    ButtonGroup { id: aiGroup }
                    Repeater {
                        model: [
                            {id:"disabled", title:"暂不连接 AI", detail:"固定课程、测试、复测和手动面试全部可用。"},
                            {id:"provider", title:"稍后连接普通 LLM API", detail:"发送前预览上下文；Key 保存在系统密钥环。"},
                            {id:"codex", title:"稍后连接 Codex", detail:"通过官方 App Server 使用 Sandbox 与显式操作审批。"}
                        ]
                        delegate: RadioButton {
                            required property var modelData
                            required property int index
                            id: aiChoice
                            ButtonGroup.group: aiGroup
                            checked: index === 0
                            text: modelData.title + "\n" + modelData.detail
                            contentItem: Text { text: aiChoice.text; color: root.palette.text; leftPadding: 42; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter }
                            property string aiId: modelData.id
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 8; color: root.palette.surfaceAlt
                        Text { anchors.fill: parent; anchors.margins: 13; text: "远程 AI 只会收到上下文预览中勾选的内容。不要上传雇主代码或整个学习档案。"; color: root.palette.text; wrapMode: Text.Wrap }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button { text: "上一步"; enabled: root.step > 0; onClicked: root.step-- }
            Item { Layout.fillWidth: true }
            Button {
                text: root.step === 3 ? "开始训练" : "继续"
                highlighted: true
                onClicked: {
                    if (root.step < 3) root.step++
                    else {
                        var selected = "disabled"
                        for (var i = 0; i < aiGroup.buttons.length; ++i)
                            if (aiGroup.buttons[i].checked) selected = aiGroup.buttons[i].aiId
                        var assessment = ({})
                        if (!skipAssessment.checked) {
                            for (var j = 0; j < assessmentRepeater.count; ++j) {
                                var row = assessmentRepeater.itemAt(j)
                                assessment[row.skillId] = row.level
                            }
                        }
                        var levels = ["intern", "new_grad", "mid", "senior"]
                        app.completeOnboarding(profileName.text, root.selectedRole, levels[seniority.currentIndex], selected, JSON.stringify(assessment))
                    }
                }
            }
        }
    }
}
