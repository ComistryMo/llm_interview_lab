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
    // This page is a true gate, not a decorative overlay.  The input shield
    // consumes clicks in the uncovered shell and the focus scope keeps Tab
    // and keyboard activation inside onboarding until the Profile exists.
    focus: visible
    activeFocusOnTab: true
    Keys.onPressed: function(event) {
        if (root.visible) {
            event.accepted = true
            if (event.key === Qt.Key_Escape)
                profileName.forceActiveFocus()
        }
    }
    onVisibleChanged: if (visible) Qt.callLater(function() {
        root.forceActiveFocus()
        if (root.step === 0)
            profileName.forceActiveFocus()
        else if (roleGrid)
            roleGrid.forceActiveFocus()
    })

    MouseArea {
        id: onboardingInputShield
        objectName: "onboardingInputShield"
        anchors.fill: parent
        z: 0
        enabled: root.visible
        acceptedButtons: Qt.AllButtons
        hoverEnabled: true
        onPressed: mouse.accepted = true
        onClicked: mouse.accepted = true
    }

    // The default path has only two user decisions: a display name and a
    // target role. The default path deliberately starts with a fresh
    // self-assessment and No-AI; interview seniority and AI connections can be
    // chosen later without changing the Practice history.
    property int step: 0
    property int stepCount: 2
    // Keep the role picker readable on the smallest supported window.  The
    // content area is narrower than the top-level window because the shell
    // owns margins and the progress/header rows; using the window width here
    // gives us one predictable breakpoint for Chinese copy.
    property bool compactRoleLayout: width < 1180
    property string selectedRole: ""
    property bool rolesAvailable: (app.roles || []).length > 0
    property var selectedRoleCard: {
        var cards = app.roles || []
        for (var i = 0; i < cards.length; ++i) {
            if (cards[i].id === root.selectedRole)
                return cards[i]
        }
        return null
    }
    property string inlineError: ""
    // Do not show a validation banner merely because the user arrived at the
    // role step.  The disabled CTA and helper text already explain what is
    // required; reserve the banner for an actual submit attempt or backend
    // error so the role list keeps its usable height.
    property bool roleSelectionAttempted: false
    property bool submitting: false
    property bool profileNameValid: profileName.text.trim().length > 0
    property string roleSelectionError: root.roleSelectionAttempted
                                        && root.step >= 1
                                        && !root.selectedRoleCard
                                        ? (root.rolesAvailable
                                           ? "请选择一个目标岗位后继续。"
                                           : "当前没有可用岗位，请检查课程资源后重试。")
                                        : ""
    property string displayedError: root.inlineError !== ""
                                    ? root.inlineError
                                    : ((app.onboardingError || "") || root.roleSelectionError)

    function clearError() {
        root.inlineError = ""
        if (app.clearOnboardingError)
            app.clearOnboardingError()
    }

    function selectRole(roleId) {
        root.selectedRole = String(roleId || "")
        root.roleSelectionAttempted = false
        root.clearError()
    }

    function positionSelectedRole() {
        if (!root.selectedRole || !roleGrid.visible)
            return
        var cards = app.roles || []
        for (var index = 0; index < cards.length; ++index) {
            if (cards[index].id === root.selectedRole) {
                // A click already leaves the selected card in view.  Only
                // move the viewport when a restored/keyboard-selected card
                // is genuinely outside the visible range; this avoids the
                // jarring jump that used to hide the first cards.
                var item = roleGrid.itemAtIndex(index)
                if (!item || item.y < roleGrid.contentY
                        || item.y + item.height > roleGrid.contentY + roleGrid.height)
                    roleGrid.positionViewAtIndex(index, GridView.Contain)
                return
            }
        }
    }

    function submitDefaultOnboarding() {
        if (!root.profileNameValid) {
            root.step = 0
            root.inlineError = "请先输入一个档案名称。"
            return
        }
        if (!root.selectedRoleCard) {
            root.roleSelectionAttempted = true
            root.inlineError = "请先选择一个目标岗位。"
            return
        }

        // These defaults are deliberate: they make the first-run path local
        // and deterministic. Advanced choices remain available after Home.
        var displayName = profileName.text.trim()
        var roleId = root.selectedRole
        root.submitting = true
        Qt.callLater(function() {
            app.completeOnboardingWithDisplayName(
                displayName, roleId, "new_grad", "disabled", "{}"
            )
            root.submitting = false
        })
    }

    onSelectedRoleChanged: {
        if (!root.selectedRole)
            return
        // The selected role can be supplied before the GridView has its final
        // geometry. Recompute the index after the layout pass instead of
        // capturing a loop variable in a delayed closure.
        Qt.callLater(function() { root.positionSelectedRole() })
    }

    onStepChanged: {
        if (root.step === 0)
            root.roleSelectionAttempted = false
        if (root.step === 1) {
            Qt.callLater(function() {
                root.positionSelectedRole()
                if (root.visible && roleGrid.visible && !root.selectedRole)
                    roleGrid.forceActiveFocus()
            })
        }
    }

    ColumnLayout {
        z: 1
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 900)
        height: Math.min(parent.height - 36, 690)
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                width: 42; height: 42; radius: 11; color: root.palette.accent
                Text { anchors.centerIn: parent; text: "LL"; color: "white"; font.bold: true }
            }
            ColumnLayout {
                spacing: 2
                Text {
                    text: "开始你的 AI 面试训练"
                    color: root.palette.text
                    font.pixelSize: 25
                    font.bold: true
                }
                Text {
                    text: "只需填写名称并选择岗位；首次使用默认 No-AI，其他选项可以稍后调整。"
                    color: root.palette.muted
                    font.pixelSize: 14
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: (Math.min(Math.max(root.step, 0), root.stepCount - 1) + 1)
                      + " / " + root.stepCount
                color: root.palette.muted
                font.bold: true
            }
        }

        ProgressBar {
            Layout.fillWidth: true
            value: (Math.min(Math.max(root.step, 0), root.stepCount - 1) + 1)
                   / root.stepCount
        }

        LabCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            cardColor: root.palette.surface
            borderColor: root.palette.border
            accentColor: root.step >= 1 ? root.palette.accent : "transparent"

            StackLayout {
                width: parent.width
                height: parent.height
                currentIndex: Math.min(Math.max(root.step, 0), 1)

                ColumnLayout {
                    objectName: "onboardingProfileStep"
                    spacing: 14
                    Text {
                        text: "创建学习档案"
                        color: root.palette.text
                        font.pixelSize: 22
                        font.bold: true
                    }
                    Text {
                        text: "刷题记录、答案、面试报告和求职材料都会保存在本机的学习档案中。"
                        color: root.palette.muted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    TextField {
                        id: profileName
                        objectName: "onboardingProfileName"
                        Layout.fillWidth: true
                        placeholderText: "例如：我的秋招准备"
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
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 74
                        radius: 8
                        color: root.palette.surfaceAlt
                        Text {
                            anchors.fill: parent
                            anchors.margins: 14
                            text: "默认保护隐私\nworkspace/profiles/<id>/ 会被 Git 忽略；连接 AI 不是必选项，首次使用按校招、No-AI 开始。"
                            color: root.palette.text
                            wrapMode: Text.WordWrap
                        }
                    }
                    Item { Layout.fillHeight: true }
                }

                ColumnLayout {
                    objectName: "onboardingRoleStep"
                    spacing: 8
                    Text {
                        text: "选择目标岗位"
                        color: root.palette.text
                        font.pixelSize: 22
                        font.bold: true
                    }
                    Text {
                        text: "岗位会影响推荐路线和面试蓝图，不会改变公共课程。"
                        color: root.palette.muted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    GridView {
                        id: roleGrid
                        objectName: "onboardingRoleGrid"
                        Layout.fillWidth: true
                        // Show complete rows only. A fixed number of visible
                        // rows prevents the next card from being cut in half
                        // by the summary bar; the list remains scrollable when
                        // more roles exist.
                        Layout.fillHeight: false
                        Layout.preferredHeight: visibleRows * cellHeight
                        clip: true
                        model: app.roles || []
                        // Choose columns from the actual role-list width, not
                        // the outer window width. Two readable columns keep
                        // the first viewport useful on compact windows while
                        // the one-column mode remains available below 760px.
                        property int columnCount: width >= 760 ? 2 : 1
                        property int roleCardHeight: root.compactRoleLayout ? 92 : 96
                        property int rowCount: Math.max(1, Math.ceil((app.roles || []).length / columnCount))
                        property int visibleRows: Math.min(rowCount, root.compactRoleLayout ? 2 : 3)
                        cellWidth: Math.max(1, columnCount === 2
                                             ? Math.floor((width - 12) / 2)
                                             : width)
                        cellHeight: roleCardHeight + 12
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height
                        // Keep a scroll gesture from stopping halfway through
                        // a card, which makes the next role look clipped.
                        snapMode: GridView.SnapToRow
                        keyNavigationWraps: false
                        onWidthChanged: Qt.callLater(function() { root.positionSelectedRole() })
                        onHeightChanged: Qt.callLater(function() { root.positionSelectedRole() })
                        ScrollBar.vertical: ScrollBar {
                            // Keep a persistent affordance for the scrollable
                            // role list; the slimmer thumb avoids obscuring
                            // card copy at compact widths.
                            policy: ScrollBar.AlwaysOn
                            width: 5
                            contentItem: Rectangle {
                                implicitWidth: 5
                                radius: 4
                                color: root.palette.muted
                                opacity: 0.45
                            }
                        }

                        delegate: Rectangle {
                            id: roleCard
                            required property var modelData
                            required property int index
                            objectName: "onboardingRoleCard-" + modelData.id
                            width: Math.max(1, roleGrid.columnCount === 2
                                               ? roleGrid.cellWidth - 12
                                               : roleGrid.cellWidth)
                            height: roleGrid.roleCardHeight
                            radius: 10
                            color: root.selectedRole === modelData.id
                                   ? Qt.rgba(0.145, 0.388, 0.922, 0.12)
                                   : roleHitArea.containsMouse
                                     ? Qt.rgba(0.145, 0.388, 0.922, 0.06)
                                     : root.palette.surfaceAlt
                            border.color: root.selectedRole === modelData.id
                                          ? root.palette.accent
                                          : roleCard.activeFocus
                                            ? root.palette.accent
                                            : roleHitArea.containsMouse
                                              ? root.palette.accent
                                              : root.palette.border
                            border.width: root.selectedRole === modelData.id
                                          || roleCard.activeFocus ? 2 : 1
                            activeFocusOnTab: true
                            Accessible.name: modelData.title || "未命名岗位"
                            Accessible.description: modelData.summary || ""
                            Accessible.role: Accessible.ListItem

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: root.compactRoleLayout ? 9 : 10
                                spacing: 3
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: root.compactRoleLayout ? 19 : 20
                                    Text {
                                        objectName: "onboardingRoleTitle-" + modelData.id
                                        text: modelData.title || "未命名岗位"
                                        color: root.palette.text
                                        font.bold: true
                                        font.pixelSize: root.compactRoleLayout ? 14 : 15
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
                                    Layout.preferredHeight: root.compactRoleLayout ? 27 : 30
                                    maximumLineCount: 2
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }
                                // Descriptive copy, not a hyperlink.
                                Text {
                                    text: "面试重点：" + (modelData.interview_content
                                           || "结构化问答与能力验证")
                                    color: root.palette.muted
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 14
                                    maximumLineCount: 1
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: roleHitArea
                                objectName: "onboardingRoleHitArea-" + modelData.id
                                anchors.fill: parent
                                hoverEnabled: true
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
                        visible: (app.roles || []).length === 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? 54 : 0
                        radius: 8
                        color: root.palette.surfaceAlt
                        Text {
                            anchors.fill: parent
                            anchors.margins: 12
                            text: "暂时没有可用岗位。请检查课程资源后重试。"
                            color: root.palette.muted
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Text {
                        visible: roleGrid.contentHeight > roleGrid.height
                        text: "向下滚动查看更多岗位"
                        color: root.palette.muted
                        font.pixelSize: 11
                        Layout.fillWidth: true
                    }
                    Item { Layout.fillHeight: true }
                    Rectangle {
                        objectName: "onboardingSelectionSummary"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
                        radius: 8
                        color: root.selectedRoleCard
                               ? Qt.rgba(0.192, 0.349, 0.851, 0.09)
                               : root.palette.surfaceAlt
                        border.color: root.selectedRoleCard
                                      ? root.palette.accent : root.palette.border
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 10
                            spacing: 8
                            Text {
                                id: selectedRoleLabel
                                objectName: "onboardingSelectedRoleLabel"
                                Layout.fillWidth: true
                                text: root.selectedRoleCard
                                      ? "岗位已选 · " + root.selectedRoleCard.title
                                      : "请选择一个岗位后继续"
                                color: root.selectedRoleCard
                                       ? root.palette.accent : root.palette.muted
                                font.bold: root.selectedRoleCard !== null
                                elide: Text.ElideRight
                            }
                            Rectangle {
                                width: 8; height: 8; radius: 4
                                color: root.selectedRoleCard ? root.palette.accent : root.palette.muted
                                opacity: root.selectedRoleCard ? 1 : 0.55
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: onboardingErrorPanel
            objectName: "onboardingInlineError"
            visible: root.displayedError.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: visible
                                      ? Math.max(54, onboardingErrorText.implicitHeight + 24)
                                      : 0
            radius: 8
            color: Qt.rgba(0.776, 0.239, 0.310, 0.12)
            border.color: root.palette.danger
            Text {
                id: onboardingErrorText
                anchors.fill: parent
                anchors.margins: 12
                text: root.displayedError
                color: root.palette.danger
                wrapMode: Text.WordWrap
                verticalAlignment: Text.AlignVCenter
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Button {
                objectName: "onboardingBackButton"
                text: "上一步"
                enabled: root.step > 0 && !root.submitting && !app.onboardingBusy
                onClicked: {
                    root.clearError()
                    root.step = 0
                }
            }
            Item { Layout.fillWidth: true }
            Button {
                id: continueButton
                objectName: "onboardingContinueButton"
                Layout.preferredWidth: root.step >= 1 ? 144 : 112
                Layout.preferredHeight: 44
                text: root.step >= 1
                      ? (root.submitting || app.onboardingBusy ? "正在创建…" : "开始训练")
                      : "继续"
                highlighted: true
                enabled: !root.submitting
                         && !app.onboardingBusy
                         && !(root.step === 0 && !root.profileNameValid)
                         && !(root.step >= 1 && !root.selectedRoleCard)
                background: Rectangle {
                    radius: 8
                    color: continueButton.enabled
                           ? root.palette.accent : root.palette.border
                    border.width: continueButton.activeFocus ? 2 : 0
                    border.color: root.palette.text
                }
                contentItem: Text {
                    text: continueButton.text
                    color: continueButton.enabled ? "white" : root.palette.muted
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    root.clearError()
                    if (root.step === 0) {
                        if (!root.profileNameValid) {
                            root.inlineError = "请先输入一个档案名称。"
                            return
                        }
                        root.step = 1
                        return
                    }
                    root.submitDefaultOnboarding()
                }
            }
        }
    }
}
