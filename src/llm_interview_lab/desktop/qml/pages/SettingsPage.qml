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
    readonly property bool stackedAppearance: width < 600 || app.fontScale > 1.25
    // Native typing/selection can leave a QML binding intact. Forward only
    // real preference changes, not every unrelated controller stateChanged.
    readonly property string savedCodexModel: app.codexModel || ""
    readonly property string savedCodexEffort: app.codexReasoningEffort || ""
    property bool refreshRequested: false
    function showCodexSettings() {
        contentY = Math.max(0, Math.min(codexSettings.y + content.y - 16, contentHeight - height))
        codexModelField.forceActiveFocus()
    }
    function codexEffortIndex(value) {
        var values = ["", "low", "medium", "high", "xhigh"]
        var index = values.indexOf(String(value || ""))
        return index < 0 ? 0 : index
    }
    contentWidth: width
    contentHeight: content.implicitHeight + 60
    clip: true
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

    ColumnLayout {
        id: content
        x: (root.width - width) / 2
        y: root.compactLayout ? 18 : 28
        width: Math.min(root.theme.formWidth, parent.width - (root.compactLayout ? 36 : 60))
        spacing: 24

        // Main.qml owns the route title; keep the page body focused on the
        // settings context instead of repeating the same large heading.
        LabText { theme: root.theme;
            objectName: "settingsRouteContext"
            text: "本地设置与连接"
            color: root.colors.text
            font.pixelSize: root.theme.scaledPx(18)
            strong: true
        }
        LabText { theme: root.theme;
            text: Qt.platform.os === "osx"
                  ? "调整显示、查看本地数据，并在 Finder 启动无法继承 PATH 时指定 Codex。"
                  : Qt.platform.os === "windows"
                    ? "调整显示、查看本地数据，并在 Windows 无法自动找到 Codex 时指定可执行文件。"
                    : "调整显示、查看本地数据，并在应用无法从 PATH 找到 Codex 时指定可执行文件。"
            color: root.colors.muted
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        LabCard {
            objectName: "settingsAppearanceCard"
            Layout.fillWidth: true
            theme: root.theme; padding: 0; cardColor: root.theme.canvas; borderColor: "transparent"
            LabText { theme: root.theme; text: "外观"; variant: "section"; strong: true }
            GridLayout {
                width: parent.width
                columns: root.stackedAppearance ? 1 : 2
                rowSpacing: 8
                columnSpacing: 20
                LabText {
                    theme: root.theme; text: "主题"; strong: true
                    Layout.preferredWidth: root.stackedAppearance ? -1 : 100
                }
                Flow {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredHeight: childrenRect.height
                    spacing: 6
                    Repeater {
                        model: [{id:"system", label:"跟随系统"}, {id:"light", label:"浅色"}, {id:"dark", label:"深色"}]
                        delegate: LabButton {
                            required property var modelData
                            objectName: "settingsTheme-" + modelData.id
                            theme: root.theme
                            compact: true
                            text: modelData.label
                            checkable: true
                            checked: app.theme === modelData.id
                            variant: checked ? "secondary" : "ghost"
                            background: Rectangle {
                                radius: root.theme.radiusMedium
                                color: parent.checked ? root.theme.surfaceHover : parent.resolvedBackground
                                border.color: parent.checked || parent.activeFocus ? root.theme.focusRing : "transparent"
                                border.width: parent.activeFocus ? 2 : 1
                            }
                            onClicked: app.setTheme(modelData.id)
                        }
                    }
                }
                LabText { theme: root.theme; text: "文字大小"; strong: true }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumHeight: root.theme.controlHeightCompact
                    Slider {
                        objectName: "settingsFontScale"
                        from: 0.85; to: 1.4; value: app.fontScale; stepSize: 0.05
                        Layout.fillWidth: true
                        Layout.maximumWidth: 280
                        implicitHeight: root.theme.controlHeightCompact
                        onMoved: app.setFontScale(value)
                    }
                    LabText { theme: root.theme; text: Math.round(app.fontScale * 100) + "%"; variant: "caption"; tone: "muted" }
                    Item { Layout.fillWidth: true }
                }
                LabText { theme: root.theme; text: "界面语言"; strong: true }
                Flow {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredHeight: childrenRect.height
                    spacing: 6
                    Repeater {
                        model: [{id:"zh-CN", label:"简体中文"}, {id:"en", label:"English（实验性）"}]
                        delegate: LabButton {
                            required property var modelData
                            objectName: "settingsLanguage-" + modelData.id
                            theme: root.theme
                            compact: true
                            text: modelData.label
                            checkable: true
                            checked: app.language === modelData.id
                            variant: checked ? "secondary" : "ghost"
                            background: Rectangle {
                                radius: root.theme.radiusMedium
                                color: parent.checked ? root.theme.surfaceHover : parent.resolvedBackground
                                border.color: parent.checked || parent.activeFocus ? root.theme.focusRing : "transparent"
                                border.width: parent.activeFocus ? 2 : 1
                            }
                            onClicked: app.setLanguage(modelData.id)
                        }
                    }
                }
            }
            LabText { theme: root.theme;
                width: parent.width
                text: app.language === "en"
                      ? "语言选择会在下次启动时保留；题面内容仍以课程提供的语言为准。"
                      : "简体中文是默认语言；选择会在下次启动时保留。"
                color: root.colors.muted
                wrapMode: Text.Wrap
                font.pixelSize: root.theme.fontCaption
            }
        }

        LabCard {
            objectName: "profileSwitcherCard"
            Layout.fillWidth: true
            theme: root.theme; padding: 0; cardColor: root.theme.canvas; borderColor: "transparent"
            LabText { theme: root.theme; text: "学习档案"; color: root.colors.text; strong: true; font.pixelSize: root.theme.scaledPx(18) }
            LabText { theme: root.theme;
                width: parent.width
                text: "切换后，材料、作答、面试和进度都会从所选档案重新读取。"
                color: root.colors.muted
                wrapMode: Text.Wrap
            }
            RowLayout {
                width: parent.width
                spacing: 10
                LabComboBox { theme: root.theme;
                    id: profilePicker
                    objectName: "profileSwitcher"
                    Layout.fillWidth: true
                    enabled: !app.profileSwitchBusy && (app.profileOptions || []).length > 0
                    model: app.profileOptions || []
                    textRole: "display_name"
                    valueRole: "profile_id"
                    currentIndex: {
                        var values = app.profileOptions || []
                        for (var i = 0; i < values.length; ++i)
                            if (values[i].profile_id === app.profileId)
                                return i
                        return -1
                    }
                    onActivated: {
                        var selected = app.profileOptions[currentIndex] || {}
                        if (selected.profile_id && !app.switchProfile(selected.profile_id)) {
                            // A dirty editor or active request can reject a
                            // switch synchronously. ComboBox interaction
                            // temporarily owns currentIndex, so restore the
                            // actual controller Profile instead of leaving a
                            // misleading selection on screen.
                            Qt.callLater(function() {
                                var values = app.profileOptions || []
                                for (var i = 0; i < values.length; ++i) {
                                    if (values[i].profile_id === app.profileId) {
                                        profilePicker.currentIndex = i
                                        break
                                    }
                                }
                            })
                        }
                    }
                }
                StatusPill {
                    theme: null
                    compact: true
                    text: app.profileSwitchBusy ? "切换中" : "当前"
                    tone: app.profileSwitchBusy ? root.colors.warning : root.colors.success
                }
            }
            LabText { theme: root.theme;
                width: parent.width
                visible: (app.profileOptions || []).length === 0
                text: "当前没有可切换的学习档案。返回首次启动流程即可创建一个新的档案。"
                color: root.colors.muted
                wrapMode: Text.Wrap
            }
            LabButton { theme: root.theme;
                objectName: "startProfileSetupFromSettings"
                visible: (app.profileOptions || []).length === 0
                text: "重新创建学习档案"
                onClicked: app.retryProfileSetup()
            }
            LabText { theme: root.theme;
                objectName: "profileSwitcherError"
                width: parent.width
                visible: (app.profileSwitchError || app.profileRestoreError || "").length > 0
                text: app.profileSwitchError || app.profileRestoreError
                color: root.colors.danger
                wrapMode: Text.Wrap
            }
            LabText { theme: root.theme;
                width: parent.width
                visible: (app.profileRestoreErrorCode || "").length > 0
                text: "错误编号：" + app.profileRestoreErrorCode + "。请先备份数据目录，再选择其他档案或重新创建。"
                color: root.colors.muted
                wrapMode: Text.Wrap
                font.pixelSize: root.theme.scaledPx(12)
            }
        }

        LabCard {
            Layout.fillWidth: true
            theme: root.theme; padding: 0; cardColor: root.theme.canvas; borderColor: "transparent"
            LabText { theme: root.theme; text: "本地数据"; color: root.colors.text; strong: true; font.pixelSize: root.theme.scaledPx(18) }
            LabText { theme: root.theme; width: parent.width; text: "学习档案、答案和面试记录默认只保存在本机。应用不提供遥测、账号或云同步。"; color: root.colors.muted; wrapMode: Text.Wrap }
            LabText { theme: root.theme; width: parent.width; text: "数据目录：" + app.dataDirectory; color: root.colors.text; elide: Text.ElideMiddle; font.pixelSize: root.theme.scaledPx(12) }
            LabText { theme: root.theme; width: parent.width; text: "日志目录：" + app.logDirectory; color: root.colors.text; elide: Text.ElideMiddle; font.pixelSize: root.theme.scaledPx(12) }
            Flow {
                width: parent.width
                spacing: 8
                LabButton { theme: root.theme; text: "打开数据目录"; onClicked: app.openDataDirectory() }
                LabButton { theme: root.theme; text: "打开日志目录"; onClicked: app.openLogDirectory() }
                LabButton { theme: root.theme;
                    objectName: "refreshLocalState"
                    text: "刷新本地状态"
                    onClicked: {
                        if (app.submissionDirty || app.coachStreaming || app.busy) {
                            refreshWarningDialog.open()
                        } else {
                            app.refresh()
                        }
                    }
                }
            }
        }

        LabCard {
            id: codexSettings
            objectName: "codexSettingsSection"
            Layout.fillWidth: true
            theme: root.theme; padding: 0; cardColor: root.theme.canvas; borderColor: "transparent"
            LabText { theme: root.theme; text: "Codex 可执行文件"; color: root.colors.text; strong: true; font.pixelSize: root.theme.scaledPx(18) }
            LabText { theme: root.theme;
                width: parent.width
                text: app.codexExecutableDisplay || (Qt.platform.os === "osx"
                      ? "自动查找（PATH、Homebrew 和常见用户目录）"
                      : Qt.platform.os === "windows"
                        ? "自动查找（PATH、npm 和常见用户目录）"
                        : "自动查找（PATH 和常见用户目录）")
                color: root.colors.muted
                elide: Text.ElideMiddle
            }
            RowLayout {
                width: parent.width
                spacing: 8
                StatusPill { theme: root.theme;
                    objectName: "codexDiscoveryStatus"
                    compact: true
                    text: app.codexProbeRunning ? "检查中"
                          : app.aiStatusVariant === "connected" ? "已连接"
                          : app.codexDiscoveryState === "found" ? "已发现（未连接）"
                          : app.codexDiscoveryState === "missing" ? "未发现" : "未检查"
                    tone: app.codexProbeRunning || app.aiStatusVariant === "connecting" ? root.colors.warning
                          : app.aiStatusVariant === "connected" ? root.colors.success
                          : app.codexDiscoveryState === "found" ? root.colors.accent
                          : root.colors.muted
                }
                LabText { theme: root.theme;
                    Layout.fillWidth: true
                    text: app.codexDiscoveryMessage || ""
                    color: root.colors.muted
                    wrapMode: Text.Wrap
                    elide: Text.ElideRight
                }
            }
            LabText { theme: root.theme;
                objectName: "codexDiscoveredPath"
                width: parent.width
                visible: app.codexDiscoveryState === "found" && (app.codexDiscoveredPath || "").length > 0
                text: "来源：" + app.codexDiscoveredPath
                color: root.colors.text
                elide: Text.ElideMiddle
                font.pixelSize: root.theme.scaledPx(12)
            }
            LabText { theme: root.theme; text: "模型与推理强度"; color: root.colors.text; strong: true }
            GridLayout {
                width: parent.width
                columns: root.compactLayout ? 1 : 2
                columnSpacing: 10
                rowSpacing: 8
                LabText { theme: root.theme; text: "模型 ID"; variant: "caption"; tone: "muted"; Layout.row: 0; Layout.column: 0 }
                LabText { theme: root.theme; text: "推理强度"; variant: "caption"; tone: "muted"; Layout.row: root.compactLayout ? 2 : 0; Layout.column: root.compactLayout ? 0 : 1 }
                LabTextField {
                    id: codexModelField
                    Layout.row: 1
                    Layout.column: 0
                    objectName: "codexModelField"
                    theme: root.theme
                    Layout.fillWidth: true
                    text: root.savedCodexModel
                    placeholderText: "模型 ID（留空使用 Codex 默认模型）"
                    accessibleLabel: "Codex 模型 ID"
                }
                LabComboBox { theme: root.theme;
                    id: codexEffort
                    Layout.row: root.compactLayout ? 3 : 1
                    Layout.column: root.compactLayout ? 0 : 1
                    objectName: "codexReasoningEffort"
                    Layout.fillWidth: true
                    textRole: "label"
                    valueRole: "value"
                    model: [
                        {value: "", label: "推理强度：默认"},
                        {value: "low", label: "推理强度：低"},
                        {value: "medium", label: "推理强度：中"},
                        {value: "high", label: "推理强度：高"},
                        {value: "xhigh", label: "推理强度：极高"}
                    ]
                    currentIndex: root.codexEffortIndex(root.savedCodexEffort)
                }
            }
            RowLayout {
                width: parent.width
                LabButton { theme: root.theme;
                    objectName: "saveCodexModelPreferences"
                    text: "保存模型设置"
                    onClicked: {
                        // Saving either preference refreshes the bound form.
                        // Capture both edits before the first refresh.
                        const model = codexModelField.text
                        const effort = codexEffort.currentValue
                        app.setCodexModel(model)
                        app.setCodexReasoningEffort(effort)
                    }
                }
                LabText { theme: root.theme;
                    Layout.fillWidth: true
                    text: "只影响新的 Codex 请求；模型不支持所选强度时会返回明确错误。"
                    color: root.colors.muted
                    wrapMode: Text.Wrap
                    font.pixelSize: root.theme.scaledPx(12)
                }
            }
            Flow {
                width: parent.width
                spacing: 8
                LabButton { theme: root.theme; text: "选择 Codex"; onClicked: codexPicker.open() }
                // Keep this action available even on a fresh install.  The
                // controller clears a stale manual path and starts the same
                // asynchronous discovery used at launch, so a missing Codex
                // is a retryable state rather than a dead control.
                LabButton { theme: root.theme;
                    objectName: "restoreCodexAutoDiscovery"
                    text: app.codexExecutable ? "恢复自动查找" : "重新自动查找"
                    onClicked: app.clearCodexExecutable()
                }
            }
            LabText { theme: root.theme;
                width: parent.width
                text: app.codexDiscoveryState === "found" && app.aiStatusVariant !== "connected"
                      ? "已发现只代表找到可执行文件；连接还需要 Codex 已登录并成功创建 App Server 会话。"
                      : "未检测到 Codex 不会影响本地训练或普通 LLM API。"
                color: root.colors.muted
                wrapMode: Text.Wrap
            }
        }

        LabCard {
            Layout.fillWidth: true
            theme: root.theme; padding: 0; cardColor: root.theme.canvas; borderColor: "transparent"
            LabText { theme: root.theme; text: "安全边界"; color: root.colors.text; strong: true; font.pixelSize: root.theme.scaledPx(18) }
            LabText { theme: root.theme; width: parent.width; text: "本地 Grader 只用于运行你本人信任的代码，不是恶意代码安全沙箱。连接远程 AI 前请核对上下文预览。"; color: root.colors.muted; wrapMode: Text.Wrap }
        }

        LabDivider { theme: root.theme; Layout.fillWidth: true }
        UpdateSettings {
            Layout.fillWidth: true
            manager: app.updateManager
            theme: root.theme
        }
        LabText { theme: root.theme; text: "LLM Interview Lab v" + Qt.application.version + " · 中文优先桌面体验"; color: root.colors.muted; font.pixelSize: root.theme.scaledPx(12) }
    }

    FileDialog {
        id: codexPicker
        title: "选择 Codex 可执行文件"
        fileMode: FileDialog.OpenFile
        onAccepted: app.setCodexExecutable(selectedFile.toString())
    }

    LabStandardDialog { theme: root.theme;
        id: refreshWarningDialog
        objectName: "refreshDirtyDraftDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(460, root.width - 48)
        implicitHeight: refreshWarningBody.implicitHeight + header.implicitHeight + footer.implicitHeight + padding * 2 + spacing * 2
        height: implicitHeight
        title: "丢弃未保存编辑并刷新？"
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            app.refresh()
            refreshRequested = false
        }
        contentItem: ColumnLayout {
            id: refreshWarningBody
            width: refreshWarningDialog.availableWidth
            spacing: 8
            LabText { theme: root.theme;
                Layout.fillWidth: true
                text: (app.submissionDirty
                       ? "当前题目有未保存的编辑。"
                       : "")
                      + (app.coachStreaming
                         ? " 有尚未结束的 AI 请求。"
                         : "")
                      + (app.busy && !app.coachStreaming
                         ? " 本地操作正在进行。"
                         : "")
                      + "刷新会重新读取磁盘快照，并停止未完成的本地操作；未保存内容可能丢失。请先保存或等待完成，或确认继续刷新。"
                color: root.colors.text
                wrapMode: Text.Wrap
            }
            LabText { theme: root.theme;
                Layout.fillWidth: true
                text: "刷新不会修改课程或其他 Profile。"
                color: root.colors.muted
                font.pixelSize: root.theme.scaledPx(12)
                wrapMode: Text.Wrap
            }
        }
    }

    LabStandardDialog { theme: root.theme;
        id: migrationDialog
        visible: app.legacyMigrationAvailable
        modal: true
        title: "发现旧版桌面数据"
        anchors.centerIn: parent
        width: Math.min(560, root.width - 48)
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 14
            LabText { theme: root.theme;
                Layout.fillWidth: true
                text: "检测到 v0.4.0-alpha.1 的学习档案。迁移会先复制、计算 SHA-256 并保留备份；不会删除或覆盖旧目录。\n\n旧目录：" + app.legacyDataDirectory
                color: root.colors.text
                wrapMode: Text.Wrap
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                LabButton { theme: root.theme; text: "稍后处理"; onClicked: { app.dismissLegacyMigration(); migrationDialog.close() } }
                LabButton { theme: root.theme; text: "安全复制"; highlighted: true; onClicked: { app.migrateLegacyData(); migrationDialog.close() } }
            }
        }
    }
}
