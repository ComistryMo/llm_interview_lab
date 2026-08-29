import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    objectName: "onboardingPage"
    required property var app
    required property var palette
    color: root.palette.background

    property int step: 0
    // A new learner must make an explicit choice.  In particular, never use
    // a role's array position as a default: catalog ordering is not a user
    // preference and can change between releases.
    property string selectedRole: ""
    property var selectedRoleCard: {
        var cards = app.roles
        for (var i = 0; i < cards.length; ++i) {
            if (cards[i].id === selectedRole)
                return cards[i]
        }
        return null
    }
    property string inlineError: ""
    property bool submitting: false
    property bool profileNameValid: profileName.text.trim().length > 0
    property string displayedError: inlineError !== "" ? inlineError : app.onboardingError

    function selectRole(roleId) {
        root.selectedRole = roleId
        root.inlineError = ""
        app.clearOnboardingError()
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
                    TextField {
                        id: profileName
                        objectName: "onboardingProfileName"
                        Layout.fillWidth: true
                        placeholderText: "例如：我的秋招准备"
                        text: ""
                        maximumLength: 120
                        onTextChanged: {
                            if (root.inlineError.length > 0)
                                root.inlineError = ""
                        }
                        focus: true
                    }
                    Text {
                        visible: profileName.text.length > 0 && !root.profileNameValid
                        text: "请输入至少一个可见字符。"
                        color: root.palette.danger
                        font.pixelSize: 12
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 74; radius: 8; color: root.palette.surfaceAlt
                        Text { anchors.fill: parent; anchors.margins: 14; text: "默认保护隐私\nworkspace/profiles/<id>/ 会被 Git 忽略；连接 AI 不是必选项。"; color: root.palette.text; wrapMode: Text.Wrap }
                    }
                    Item { Layout.fillHeight: true }
                }

                // Role cards use a GridView with explicit cells.  This keeps
                // delegate geometry deterministic inside the scrolling view.
                ColumnLayout {
                    objectName: "onboardingRoleStep"
                    spacing: 8
                    Text { text: "选择目标岗位"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "岗位会影响技能权重、推荐闯关路线和面试蓝图，不会改变公共课程事实。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }

                    GridView {
                        id: roleGrid
                        objectName: "onboardingRoleGrid"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: app.roles
                        property int columnCount: width >= 760 ? 2 : 1
                        cellWidth: Math.max(1, columnCount === 2 ? Math.floor((width - 12) / 2) : width)
                        cellHeight: 108
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: Rectangle {
                            id: roleCard
                            required property var modelData
                            required property int index
                            objectName: "onboardingRoleCard-" + modelData.id
                            width: Math.max(1, roleGrid.columnCount === 2 ? roleGrid.cellWidth - 12 : roleGrid.cellWidth)
                            height: 96
                            radius: 10
                            color: root.selectedRole === modelData.id
                                   ? Qt.rgba(0.145, 0.388, 0.922, 0.12)
                                   : root.palette.surfaceAlt
                            border.color: root.selectedRole === modelData.id
                                          ? root.palette.accent
                                          : roleCard.activeFocus
                                            ? root.palette.accent
                                            : root.palette.border
                            border.width: root.selectedRole === modelData.id || roleCard.activeFocus ? 2 : 1
                            activeFocusOnTab: true
                            Accessible.name: modelData.title
                            Accessible.role: Accessible.ListItem

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 3
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 20
                                    Text {
                                        objectName: "onboardingRoleTitle-" + modelData.id
                                        text: modelData.title
                                        color: root.palette.text
                                        font.bold: true
                                        font.pixelSize: 15
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        objectName: "onboardingRoleSelected-" + modelData.id
                                        text: "✓"
                                        visible: root.selectedRole === modelData.id
                                        color: root.palette.accent
                                        font.bold: true
                                        font.pixelSize: 19
                                        horizontalAlignment: Text.AlignRight
                                        Layout.preferredWidth: 22
                                    }
                                }
                                Text {
                                    text: modelData.summary || ""
                                    color: root.palette.muted
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    maximumLineCount: 2
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: modelData.interview_content || "结构化问答与能力验证"
                                    color: root.palette.accent
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 14
                                    maximumLineCount: 1
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                objectName: "onboardingRoleHitArea-" + modelData.id
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onPressed: roleCard.forceActiveFocus()
                                onClicked: root.selectRole(modelData.id)
                            }
                            Keys.onReturnPressed: {
                                root.selectRole(modelData.id)
                                event.accepted = true
                            }
                            Keys.onSpacePressed: {
                                root.selectRole(modelData.id)
                                event.accepted = true
                            }
                        }
                    }

                    Rectangle {
                        objectName: "onboardingRoleEmptyState"
                        visible: app.roles.length === 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? 54 : 0
                        radius: 8
                        color: root.palette.surfaceAlt
                        Text {
                            anchors.fill: parent
                            anchors.margins: 12
                            text: "暂时没有可用岗位。请检查课程资源后重试。"
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Text {
                        id: selectedRoleLabel
                        objectName: "onboardingSelectedRoleLabel"
                        Layout.fillWidth: true
                        text: root.selectedRoleCard
                              ? "已选择：" + root.selectedRoleCard.title
                              : "请选择一个岗位后继续"
                        color: root.selectedRoleCard ? root.palette.accent : root.palette.muted
                        font.bold: root.selectedRoleCard !== null
                        elide: Text.ElideRight
                    }
                    Text {
                        visible: roleGrid.contentHeight > roleGrid.height
                        text: "岗位列表可滚动查看"
                        color: root.palette.muted
                        font.pixelSize: 11
                        Layout.fillWidth: true
                    }
                }

                ColumnLayout {
                    spacing: 16
                    Text { text: "能力自评"; color: root.palette.text; font.pixelSize: 22; font.bold: true }
                    Text { text: "只展示与目标岗位最相关的技能，用于改善推荐；自评不会授予“已掌握”。"; color: root.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Repeater {
                        id: assessmentRepeater
                        model: root.selectedRoleCard && root.selectedRoleCard.top_skills
                               ? root.selectedRoleCard.top_skills.slice(0, 8) : []
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

        Rectangle {
            id: onboardingErrorPanel
            objectName: "onboardingInlineError"
            visible: root.displayedError.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? Math.max(54, onboardingErrorText.implicitHeight + 24) : 0
            radius: 8
            color: Qt.rgba(0.776, 0.239, 0.310, 0.12)
            border.color: root.palette.danger
            Text {
                id: onboardingErrorText
                anchors.fill: parent
                anchors.margins: 12
                text: root.displayedError
                color: root.palette.danger
                wrapMode: Text.Wrap
                verticalAlignment: Text.AlignVCenter
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button {
                text: "上一步"
                enabled: root.step > 0 && !root.submitting && !app.onboardingBusy
                onClicked: {
                    root.inlineError = ""
                    app.clearOnboardingError()
                    root.step--
                }
            }
            Item { Layout.fillWidth: true }
            Button {
                id: continueButton
                objectName: "onboardingContinueButton"
                text: root.step === 3
                      ? (root.submitting || app.onboardingBusy ? "正在创建…" : "开始训练")
                      : "继续"
                highlighted: true
                enabled: !root.submitting
                         && !app.onboardingBusy
                         && !(root.step === 0 && !root.profileNameValid)
                         && !(root.step === 1 && root.selectedRole.length === 0)
                onClicked: {
                    root.inlineError = ""
                    app.clearOnboardingError()
                    if (root.step < 3) {
                        if (root.step === 1 && root.selectedRole.length === 0) {
                            root.inlineError = "请先选择一个目标岗位。"
                            return
                        }
                        root.step++
                    } else {
                        if (!root.profileNameValid) {
                            root.inlineError = "请先输入一个档案名称。"
                            root.step = 0
                            return
                        }
                        if (root.selectedRole.length === 0) {
                            root.step = 1
                            root.inlineError = "请先选择一个目标岗位。"
                            return
                        }
                        var selected = "disabled"
                        for (var i = 0; i < aiGroup.buttons.length; ++i) {
                            if (aiGroup.buttons[i].checked) {
                                selected = aiGroup.buttons[i].aiId
                                break
                            }
                        }
                        var assessment = ({})
                        if (!skipAssessment.checked) {
                            for (var j = 0; j < assessmentRepeater.count; ++j) {
                                var row = assessmentRepeater.itemAt(j)
                                assessment[row.skillId] = row.level
                            }
                        }
                        var levels = ["intern", "new_grad", "mid", "senior"]
                        var profileId = profileName.text
                        var roleId = root.selectedRole
                        var seniorityId = levels[seniority.currentIndex]
                        var assessmentJson = JSON.stringify(assessment)
                        root.submitting = true
                        Qt.callLater(function() {
                            app.completeOnboardingWithDisplayName(profileId, roleId, seniorityId,
                                                                  selected, assessmentJson)
                            root.submitting = false
                        })
                    }
                }
            }
        }
    }
}
