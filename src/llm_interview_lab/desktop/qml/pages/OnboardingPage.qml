import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: root
    objectName: "onboardingPage"

    required property var app
    required property var palette
    // Main.qml supplies these during the Quiet Forge migration. Keeping both
    // optional preserves source-mode and older embedding compatibility.
    property var theme: null
    property string layoutMode: width < 1040 ? "compact"
                                               : width < 1400 ? "standard" : "wide"

    property int step: 0
    property int stepCount: 2
    property string selectedRole: ""
    property string inlineError: ""
    property bool roleSelectionAttempted: false
    property bool submitting: false

    // The onboarding overlay owns the entire window, so its 1180px content
    // threshold is more useful than the shell's sidebar breakpoint here.
    readonly property bool wideLayout: width >= 1180
    readonly property bool compactLayout: width < 1040
    // Compatibility name retained for the targeted first-run contract.
    readonly property bool compactRoleLayout: !wideLayout
    readonly property bool largeText: !!theme && theme.resolvedFontScale > 1.15
    readonly property bool rolesAvailable: (app.roles || []).length > 0
    readonly property bool profileNameValid: profileName.text.trim().length > 0
    readonly property var selectedRoleCard: {
        var cards = app.roles || []
        for (var i = 0; i < cards.length; ++i) {
            if (cards[i].id === root.selectedRole)
                return cards[i]
        }
        return null
    }
    readonly property string roleSelectionError: root.roleSelectionAttempted
                                                    && root.step >= 1
                                                    && !root.selectedRoleCard
                                                ? (root.rolesAvailable
                                                   ? "请选择一个目标岗位后继续。"
                                                   : "当前没有可用岗位，请检查课程资源后重试。")
                                                : ""
    readonly property string displayedError: root.inlineError !== ""
                                               ? root.inlineError
                                               : ((app.onboardingError || "")
                                                  || root.roleSelectionError)

    color: theme ? theme.canvas : root.palette.background
    focus: visible
    activeFocusOnTab: true

    function scaledPx(px) {
        return root.theme ? root.theme.scaledPx(px) : px
    }

    function clearError() {
        root.inlineError = ""
        if (app.clearOnboardingError)
            app.clearOnboardingError()
    }

    function selectRole(roleId) {
        root.selectedRole = String(roleId || "")
        var cards = app.roles || []
        for (var i = 0; i < cards.length; ++i) {
            if (cards[i].id === root.selectedRole) {
                roleGrid.currentIndex = i
                break
            }
        }
        root.roleSelectionAttempted = false
        root.clearError()
        Qt.callLater(function() { root.positionSelectedRole() })
    }

    function positionSelectedRole() {
        if (!root.selectedRole || !roleGrid.visible)
            return
        var cards = app.roles || []
        for (var index = 0; index < cards.length; ++index) {
            if (cards[index].id !== root.selectedRole)
                continue
            var item = roleGrid.itemAtIndex(index)
            if (!item || item.y < roleGrid.contentY
                    || item.y + item.height > roleGrid.contentY + roleGrid.height)
                roleGrid.positionViewAtIndex(index, GridView.Center)
            return
        }
    }

    function submitDefaultOnboarding() {
        if (root.submitting || app.onboardingBusy)
            return
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

        // The first run is deliberately local and deterministic. Seniority
        // and AI connections remain editable after onboarding.
        var displayName = profileName.text.trim()
        var roleId = root.selectedRole
        root.submitting = true
        Qt.callLater(function() {
            try {
                app.completeOnboardingWithDisplayName(
                    displayName, roleId, "new_grad", "disabled", "{}"
                )
            } finally {
                root.submitting = false
            }
        })
    }

    // Consume only the one page-level shortcut we own. Tab, Shift+Tab and
    // arrow navigation remain available to the controls and GridView.
    Keys.onEscapePressed: function(event) {
        if (root.step > 0) {
            root.clearError()
            root.step = 0
        } else {
            profileName.forceActiveFocus()
        }
        event.accepted = true
    }

    onVisibleChanged: if (visible) Qt.callLater(function() {
        root.forceActiveFocus()
        if (root.step === 0)
            profileName.forceActiveFocus()
        else
            roleGrid.forceActiveFocus()
    })

    onSelectedRoleChanged: if (root.selectedRole)
        Qt.callLater(function() { root.positionSelectedRole() })

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

    RowLayout {
        id: onboardingFrame
        z: 1
        anchors.centerIn: parent
        width: Math.min(parent.width - (root.compactLayout ? 28 : 48),
                        root.wideLayout ? 1220 : 900)
        height: Math.min(parent.height - (root.compactLayout ? 24 : 36), 720)
        spacing: root.wideLayout ? 16 : 0

        Rectangle {
            id: brandPanel
            visible: root.wideLayout
            Layout.fillHeight: true
            Layout.preferredWidth: visible
                                   ? Math.round((onboardingFrame.width - 16) * 0.32) : 0
            radius: root.theme ? root.theme.radiusLarge : 12
            color: root.theme ? root.theme.surfaceSunken : root.palette.surfaceAlt
            border.color: root.theme ? root.theme.borderSubtle : root.palette.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 32
                spacing: 16

                Image {
                    Layout.preferredWidth: 68
                    Layout.preferredHeight: 68
                    source: "../../resources/app-icon.svg"
                    sourceSize.width: 136
                    sourceSize.height: 136
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    Accessible.name: "LLM Interview Lab"
                }

                Text {
                    Layout.fillWidth: true
                    text: "把面试准备，变成可验证的能力"
                    color: root.theme ? root.theme.textStrong : root.palette.text
                    font.pixelSize: root.scaledPx(26)
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    text: "根据目标岗位安排训练路线，用公开测试、复盘和间隔复测帮助你独立完成，而不是替你给出答案。"
                    color: root.theme ? root.theme.text : root.palette.muted
                    font.pixelSize: root.scaledPx(14)
                    lineHeight: 1.35
                    wrapMode: Text.WordWrap
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Repeater {
                        model: [
                            "岗位导向的推荐路线",
                            "本地保存的个人训练记录",
                            "无需连接 AI 也能完整开始"
                        ]
                        RowLayout {
                            required property string modelData
                            spacing: 9
                            Rectangle {
                                Layout.preferredWidth: 18
                                Layout.preferredHeight: 18
                                radius: 9
                                color: root.theme ? root.theme.accentSoft
                                                  : Qt.rgba(0.32, 0.39, 0.85, 0.12)
                                Text {
                                    anchors.centerIn: parent
                                    text: "✓"
                                    color: root.palette.accent
                                    font.pixelSize: root.scaledPx(11)
                                    font.bold: true
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData
                                color: root.theme ? root.theme.textStrong : root.palette.text
                                font.pixelSize: root.scaledPx(14)
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    text: "源码模式使用仓库内 Workspace；桌面安装包使用系统应用数据目录。两种模式都默认保存在本机。"
                    color: root.theme ? root.theme.subtle : root.palette.muted
                    font.pixelSize: root.scaledPx(12)
                    lineHeight: 1.35
                    wrapMode: Text.WordWrap
                }
            }
        }

        Rectangle {
            id: formPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: root.theme ? root.theme.radiusLarge : 12
            color: root.theme ? root.theme.surface : root.palette.surface
            border.color: root.theme ? root.theme.borderDefault : root.palette.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: root.compactLayout ? 16 : 24
                spacing: root.compactLayout ? 9 : 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Image {
                        visible: !root.wideLayout
                        Layout.preferredWidth: visible ? 40 : 0
                        Layout.preferredHeight: visible ? 40 : 0
                        source: "../../resources/app-icon.svg"
                        sourceSize.width: 80
                        sourceSize.height: 80
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        Accessible.name: "LLM Interview Lab"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: root.step === 0 ? "创建你的学习档案" : "选择目标岗位"
                            color: root.theme ? root.theme.textStrong : root.palette.text
                            font.pixelSize: Math.min(
                                root.scaledPx(root.compactLayout ? 22 : 25),
                                root.compactLayout ? 28 : 32
                            )
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.step === 0
                                  ? "只需一个名称；首次使用默认按校招、No-AI 开始。"
                                  : "岗位只影响推荐路线和面试蓝图，不会改变公共课程。"
                            color: root.theme ? root.theme.text : root.palette.muted
                            font.pixelSize: root.scaledPx(13)
                            maximumLineCount: root.compactLayout ? 1 : 2
                            wrapMode: Text.WordWrap
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        text: (Math.min(Math.max(root.step, 0), root.stepCount - 1) + 1)
                              + " / " + root.stepCount
                        color: root.theme ? root.theme.subtle : root.palette.muted
                        font.pixelSize: root.scaledPx(12)
                        font.bold: true
                    }
                }

                ProgressBar {
                    id: stepProgress
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4
                    value: (Math.min(Math.max(root.step, 0), root.stepCount - 1) + 1)
                           / root.stepCount
                    background: Rectangle {
                        radius: 2
                        color: root.theme ? root.theme.surfaceSunken : root.palette.surfaceAlt
                    }
                    contentItem: Item {
                        implicitHeight: 4
                        Rectangle {
                            width: parent.width * stepProgress.visualPosition
                            height: parent.height
                            radius: 2
                            color: root.palette.accent
                        }
                    }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: Math.min(Math.max(root.step, 0), 1)

                    Flickable {
                        id: profileStep
                        objectName: "onboardingProfileStep"
                        clip: true
                        contentWidth: width
                        contentHeight: profileContent.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height
                        ScrollBar.vertical: ScrollBar {
                            policy: profileStep.interactive
                                    ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                        }

                        Column {
                            id: profileContent
                            width: profileStep.width
                            spacing: 14

                            Text {
                                width: parent.width
                                text: "学习档案名称"
                                color: root.theme ? root.theme.textStrong : root.palette.text
                                font.pixelSize: root.scaledPx(15)
                                font.weight: Font.DemiBold
                            }

                            LabTextField {
                                id: profileName
                                objectName: "onboardingProfileName"
                                width: parent.width
                                theme: root.theme
                                accessibleLabel: "学习档案名称"
                                placeholderText: "例如：我的秋招准备"
                                maximumLength: 120
                                busy: root.submitting || app.onboardingBusy
                                onTextChanged: {
                                    if (root.inlineError.length > 0)
                                        root.inlineError = ""
                                }
                            }

                            Text {
                                width: parent.width
                                visible: profileName.text.length > 0 && !root.profileNameValid
                                text: "请输入至少一个可见字符。"
                                color: root.palette.danger
                                font.pixelSize: root.scaledPx(12)
                                wrapMode: Text.WordWrap
                            }

                            Rectangle {
                                width: parent.width
                                height: Math.max(root.scaledPx(78), privacyCopy.implicitHeight + 28)
                                radius: root.theme ? root.theme.radiusMedium : 8
                                color: root.theme ? root.theme.surfaceSunken : root.palette.surfaceAlt
                                border.color: root.theme ? root.theme.borderSubtle : "transparent"

                                Text {
                                    id: privacyCopy
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    text: "默认保存在本机\n源码运行时使用仓库内 workspace/profiles/；桌面安装包使用系统应用数据目录。连接 AI 不是必选项，只有你确认的上下文才会发送。"
                                    color: root.theme ? root.theme.text : root.palette.text
                                    font.pixelSize: root.scaledPx(13)
                                    lineHeight: 1.3
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }

                    Item {
                        objectName: "onboardingRoleStep"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 7

                            GridView {
                                id: roleGrid
                                objectName: "onboardingRoleGrid"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: app.roles || []
                                property int columnCount: root.wideLayout ? 2 : 1
                                property int roleCardHeight: root.largeText ? 108
                                                               : root.wideLayout ? 96 : 94
                                property int rowCount: Math.max(
                                    1, Math.ceil((app.roles || []).length / columnCount)
                                )
                                property int visibleRows: Math.max(
                                    1, Math.floor(Math.max(1, height) / cellHeight)
                                )
                                cellWidth: Math.max(1, columnCount === 2
                                                     ? Math.floor((width - 12) / 2)
                                                     : width)
                                cellHeight: roleCardHeight + 10
                                cacheBuffer: Math.max(0, contentHeight)
                                boundsBehavior: Flickable.StopAtBounds
                                interactive: contentHeight > height
                                snapMode: GridView.SnapToRow
                                keyNavigationWraps: false
                                onWidthChanged: Qt.callLater(function() {
                                    root.positionSelectedRole()
                                })
                                onHeightChanged: Qt.callLater(function() {
                                    root.positionSelectedRole()
                                })
                                ScrollBar.vertical: ScrollBar {
                                    policy: roleGrid.interactive
                                            ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                                    width: 5
                                    contentItem: Rectangle {
                                        implicitWidth: 5
                                        radius: 3
                                        color: root.theme ? root.theme.borderStrong
                                                          : root.palette.muted
                                        opacity: 0.65
                                    }
                                }

                                delegate: Rectangle {
                                    id: roleCard
                                    required property var modelData
                                    required property int index
                                    objectName: "onboardingRoleCard-" + modelData.id
                                    width: Math.max(1, roleGrid.columnCount === 2
                                                       ? roleGrid.cellWidth - 10
                                                       : roleGrid.cellWidth - 8)
                                    height: roleGrid.roleCardHeight
                                    radius: root.theme ? root.theme.radiusMedium : 9
                                    color: root.selectedRole === modelData.id
                                           ? (root.theme ? root.theme.accentSoft
                                                         : Qt.rgba(0.32, 0.39, 0.85, 0.12))
                                           : roleHitArea.containsMouse
                                             ? (root.theme ? root.theme.surfaceHover
                                                           : Qt.rgba(0.32, 0.39, 0.85, 0.06))
                                             : (root.theme ? root.theme.surfaceRaised
                                                           : root.palette.surfaceAlt)
                                    border.color: root.selectedRole === modelData.id
                                                  || roleCard.activeFocus
                                                  || roleHitArea.containsMouse
                                                  ? root.palette.accent
                                                  : (root.theme
                                                     ? root.theme.borderDefault
                                                     : root.palette.border)
                                    border.width: root.selectedRole === modelData.id
                                                  || roleCard.activeFocus ? 2 : 1
                                    activeFocusOnTab: true
                                    Accessible.name: modelData.title || "未命名岗位"
                                    Accessible.description: modelData.summary || ""
                                    Accessible.role: Accessible.ListItem
                                    Accessible.selected: root.selectedRole === modelData.id

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: root.largeText ? 8 : 10
                                        spacing: 2

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 6
                                            Text {
                                                objectName: "onboardingRoleTitle-" + modelData.id
                                                Layout.fillWidth: true
                                                text: modelData.title || "未命名岗位"
                                                color: root.theme ? root.theme.textStrong
                                                                  : root.palette.text
                                                font.pixelSize: root.scaledPx(14)
                                                font.weight: Font.DemiBold
                                                maximumLineCount: root.largeText ? 1 : 2
                                                wrapMode: Text.WordWrap
                                                elide: Text.ElideRight
                                            }
                                            Text {
                                                objectName: "onboardingRoleSelected-" + modelData.id
                                                Layout.preferredWidth: 22
                                                text: "✓"
                                                visible: root.selectedRole === modelData.id
                                                color: root.palette.accent
                                                font.pixelSize: root.scaledPx(17)
                                                font.bold: true
                                                horizontalAlignment: Text.AlignRight
                                            }
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.summary || ""
                                            color: root.theme ? root.theme.text : root.palette.muted
                                            font.pixelSize: root.scaledPx(11)
                                            maximumLineCount: root.largeText ? 1 : 2
                                            wrapMode: Text.WordWrap
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "面试重点 · " + (modelData.interview_content
                                                  || "结构化问答与能力验证")
                                            color: root.theme ? root.theme.subtle : root.palette.muted
                                            font.pixelSize: root.scaledPx(10)
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
                                    Keys.onReturnPressed: function(event) {
                                        root.selectRole(modelData.id)
                                        event.accepted = true
                                    }
                                    Keys.onSpacePressed: function(event) {
                                        root.selectRole(modelData.id)
                                        event.accepted = true
                                    }
                                }
                            }

                            Rectangle {
                                objectName: "onboardingRoleEmptyState"
                                visible: !root.rolesAvailable
                                Layout.fillWidth: true
                                Layout.preferredHeight: visible ? 64 : 0
                                radius: root.theme ? root.theme.radiusMedium : 8
                                color: root.theme ? root.theme.surfaceSunken
                                                  : root.palette.surfaceAlt
                                border.color: root.theme ? root.theme.borderSubtle
                                                         : root.palette.border
                                Text {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    text: "暂时没有可用岗位。请检查课程资源后重试。"
                                    color: root.theme ? root.theme.text : root.palette.muted
                                    font.pixelSize: root.scaledPx(13)
                                    wrapMode: Text.WordWrap
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Text {
                                visible: roleGrid.contentHeight > roleGrid.height
                                Layout.fillWidth: true
                                text: "滚动查看更多岗位"
                                color: root.theme ? root.theme.subtle : root.palette.muted
                                font.pixelSize: root.scaledPx(11)
                            }

                            Rectangle {
                                objectName: "onboardingSelectionSummary"
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.largeText ? 42 : 38
                                radius: root.theme ? root.theme.radiusSmall : 8
                                color: root.selectedRoleCard
                                       ? (root.theme ? root.theme.accentSoft
                                                     : Qt.rgba(0.32, 0.39, 0.85, 0.09))
                                       : (root.theme ? root.theme.surfaceSunken
                                                     : root.palette.surfaceAlt)
                                border.color: root.selectedRoleCard
                                              ? root.palette.accent
                                              : (root.theme ? root.theme.borderSubtle
                                                            : root.palette.border)

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
                                              ? "已选择：" + root.selectedRoleCard.title
                                              : "请选择一个岗位后继续"
                                        color: root.selectedRoleCard
                                               ? root.palette.accent
                                               : (root.theme ? root.theme.subtle
                                                             : root.palette.muted)
                                        font.pixelSize: root.scaledPx(12)
                                        font.bold: root.selectedRoleCard !== null
                                        elide: Text.ElideRight
                                    }
                                    Rectangle {
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: root.selectedRoleCard
                                               ? root.palette.accent
                                               : (root.theme ? root.theme.subtle
                                                             : root.palette.muted)
                                        opacity: root.selectedRoleCard ? 1 : 0.5
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
                                              ? Math.max(root.scaledPx(48),
                                                         onboardingErrorText.implicitHeight + 20)
                                              : 0
                    radius: root.theme ? root.theme.radiusSmall : 8
                    color: root.theme ? root.theme.dangerSoft
                                      : Qt.rgba(0.776, 0.239, 0.310, 0.12)
                    border.color: root.palette.danger

                    Text {
                        id: onboardingErrorText
                        anchors.fill: parent
                        anchors.margins: 10
                        text: root.displayedError
                        color: root.palette.danger
                        font.pixelSize: root.scaledPx(12)
                        wrapMode: Text.WordWrap
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: root.theme ? root.theme.borderSubtle : root.palette.border
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabButton {
                        objectName: "onboardingBackButton"
                        theme: root.theme
                        variant: "ghost"
                        font.pixelSize: Math.min(root.scaledPx(14), 17)
                        text: "上一步"
                        visible: root.step > 0
                        enabled: root.step > 0 && !root.submitting && !app.onboardingBusy
                        onClicked: {
                            root.clearError()
                            root.step = 0
                        }
                    }

                    Text {
                        visible: root.step >= 1 && !root.selectedRoleCard
                        Layout.fillWidth: true
                        text: "选择岗位后即可开始；稍后仍可在设置中调整。"
                        color: root.theme ? root.theme.subtle : root.palette.muted
                        font.pixelSize: root.scaledPx(11)
                        maximumLineCount: 1
                        elide: Text.ElideRight
                    }

                    Item {
                        visible: root.step === 0 || !!root.selectedRoleCard
                        Layout.fillWidth: true
                    }

                    LabButton {
                        id: continueButton
                        objectName: "onboardingContinueButton"
                        theme: root.theme
                        variant: "primary"
                        font.pixelSize: Math.min(root.scaledPx(14), 17)
                        Layout.preferredWidth: root.step >= 1 ? 144 : 112
                        Layout.preferredHeight: 44
                        text: root.step >= 1
                              ? (root.submitting || app.onboardingBusy
                                 ? "正在创建…" : "开始训练")
                              : "继续"
                        busy: root.submitting || app.onboardingBusy
                        enabled: !root.submitting
                                 && !app.onboardingBusy
                                 && !(root.step === 0 && !root.profileNameValid)
                                 && !(root.step >= 1 && !root.selectedRoleCard)
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
    }
}
