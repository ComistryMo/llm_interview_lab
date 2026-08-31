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
    property bool refreshRequested: false
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
            color: root.palette.muted
            opacity: 0.45
        }
    }

    ColumnLayout {
        id: content
        x: root.compactLayout ? 18 : 30
        y: root.compactLayout ? 18 : 28
        width: parent.width - (root.compactLayout ? 36 : 60)
        spacing: root.compactLayout ? 12 : 16

        // Main.qml owns the route title; keep the page body focused on the
        // settings context instead of repeating the same large heading.
        Text {
            objectName: "settingsRouteContext"
            text: "本地设置与连接"
            color: root.palette.text
            font.pixelSize: 16
            font.bold: true
        }
        Text {
            text: Qt.platform.os === "osx"
                  ? "调整显示、查看本地数据，并在 Finder 启动无法继承 PATH 时指定 Codex。"
                  : Qt.platform.os === "windows"
                    ? "调整显示、查看本地数据，并在 Windows 无法自动找到 Codex 时指定可执行文件。"
                    : "调整显示、查看本地数据，并在应用无法从 PATH 找到 Codex 时指定可执行文件。"
            color: root.palette.muted
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        LabCard {
            Layout.fillWidth: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "外观"; color: root.palette.text; font.bold: true; font.pixelSize: 18 }
            Flow {
                width: parent.width
                spacing: 8
                Repeater {
                    model: [{id:"system", label:"跟随系统"}, {id:"light", label:"浅色"}, {id:"dark", label:"深色"}]
                    delegate: Button {
                        required property var modelData
                        text: modelData.label
                        checkable: true
                        checked: app.theme === modelData.id
                        onClicked: app.setTheme(modelData.id)
                    }
                }
            }
            Text { text: "文字大小"; color: root.palette.text; font.bold: true }
            RowLayout {
                width: parent.width
                Slider { from: 0.85; to: 1.4; value: app.fontScale; stepSize: 0.05; Layout.fillWidth: true; onMoved: app.setFontScale(value) }
                Text { text: Math.round(app.fontScale * 100) + "%"; color: root.palette.muted }
            }
            Text { text: "界面语言"; color: root.palette.text; font.bold: true }
            Flow {
                width: parent.width
                spacing: 8
                Repeater {
                    model: [{id:"zh-CN", label:"简体中文"}, {id:"en", label:"English（实验性）"}]
                    delegate: Button {
                        required property var modelData
                        text: modelData.label
                        checkable: true
                        checked: app.language === modelData.id
                        onClicked: app.setLanguage(modelData.id)
                    }
                }
            }
            Text {
                width: parent.width
                text: app.language === "en"
                      ? "语言选择会在下次启动时保留；题面内容仍以课程提供的语言为准。"
                      : "简体中文是默认语言；选择会在下次启动时保留。"
                color: root.palette.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
        }

        LabCard {
            objectName: "profileSwitcherCard"
            Layout.fillWidth: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "学习档案"; color: root.palette.text; font.bold: true; font.pixelSize: 18 }
            Text {
                width: parent.width
                text: "切换后，材料、作答、面试和进度都会从所选档案重新读取。"
                color: root.palette.muted
                wrapMode: Text.Wrap
            }
            RowLayout {
                width: parent.width
                spacing: 10
                ComboBox {
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
                    tone: app.profileSwitchBusy ? root.palette.warning : root.palette.success
                }
            }
            Text {
                width: parent.width
                visible: (app.profileOptions || []).length === 0
                text: "当前没有可切换的学习档案。返回首次启动流程即可创建一个新的档案。"
                color: root.palette.muted
                wrapMode: Text.Wrap
            }
            Button {
                objectName: "startProfileSetupFromSettings"
                visible: (app.profileOptions || []).length === 0
                text: "重新创建学习档案"
                onClicked: app.retryProfileSetup()
            }
            Text {
                objectName: "profileSwitcherError"
                width: parent.width
                visible: (app.profileSwitchError || app.profileRestoreError || "").length > 0
                text: app.profileSwitchError || app.profileRestoreError
                color: root.palette.danger
                wrapMode: Text.Wrap
            }
            Text {
                width: parent.width
                visible: (app.profileRestoreErrorCode || "").length > 0
                text: "错误编号：" + app.profileRestoreErrorCode + "。请先备份数据目录，再选择其他档案或重新创建。"
                color: root.palette.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
        }

        LabCard {
            Layout.fillWidth: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "本地数据"; color: root.palette.text; font.bold: true; font.pixelSize: 18 }
            Text { width: parent.width; text: "学习档案、答案和面试记录默认只保存在本机。应用不提供遥测、账号或云同步。"; color: root.palette.muted; wrapMode: Text.Wrap }
            Text { width: parent.width; text: "数据目录：" + app.dataDirectory; color: root.palette.text; elide: Text.ElideMiddle; font.pixelSize: 12 }
            Text { width: parent.width; text: "日志目录：" + app.logDirectory; color: root.palette.text; elide: Text.ElideMiddle; font.pixelSize: 12 }
            Flow {
                width: parent.width
                spacing: 8
                Button { text: "打开数据目录"; onClicked: app.openDataDirectory() }
                Button { text: "打开日志目录"; onClicked: app.openLogDirectory() }
                Button {
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
            Layout.fillWidth: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "Codex 可执行文件"; color: root.palette.text; font.bold: true; font.pixelSize: 18 }
            Text {
                width: parent.width
                text: app.codexExecutableDisplay || (Qt.platform.os === "osx"
                      ? "自动查找（PATH、Homebrew 和常见用户目录）"
                      : Qt.platform.os === "windows"
                        ? "自动查找（PATH、npm 和常见用户目录）"
                        : "自动查找（PATH 和常见用户目录）")
                color: root.palette.muted
                elide: Text.ElideMiddle
            }
            RowLayout {
                width: parent.width
                spacing: 8
                StatusPill {
                    objectName: "codexDiscoveryStatus"
                    compact: true
                    text: app.codexProbeRunning ? "检查中"
                          : app.codexDiscoveryState === "found" ? "已发现"
                          : app.codexDiscoveryState === "missing" ? "未发现" : "未检查"
                    tone: app.codexProbeRunning ? root.palette.warning
                          : app.codexDiscoveryState === "found" ? root.palette.success
                          : root.palette.muted
                }
                Text {
                    Layout.fillWidth: true
                    text: app.codexDiscoveryMessage || ""
                    color: root.palette.muted
                    wrapMode: Text.Wrap
                    elide: Text.ElideRight
                }
            }
            Text {
                objectName: "codexDiscoveredPath"
                width: parent.width
                visible: app.codexDiscoveryState === "found" && (app.codexDiscoveredPath || "").length > 0
                text: "来源：" + app.codexDiscoveredPath
                color: root.palette.text
                elide: Text.ElideMiddle
                font.pixelSize: 12
            }
            Flow {
                width: parent.width
                spacing: 8
                Button { text: "选择 Codex"; onClicked: codexPicker.open() }
                // Keep this action available even on a fresh install.  The
                // controller clears a stale manual path and starts the same
                // asynchronous discovery used at launch, so a missing Codex
                // is a retryable state rather than a dead control.
                Button {
                    objectName: "restoreCodexAutoDiscovery"
                    text: app.codexExecutable ? "恢复自动查找" : "重新自动查找"
                    onClicked: app.clearCodexExecutable()
                }
            }
            Text { width: parent.width; text: "未检测到 Codex 不会影响本地训练或普通 LLM API。"; color: root.palette.muted; wrapMode: Text.Wrap }
        }

        LabCard {
            Layout.fillWidth: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            Text { text: "安全边界"; color: root.palette.text; font.bold: true; font.pixelSize: 18 }
            Text { width: parent.width; text: "本地 Grader 只用于运行你本人信任的代码，不是恶意代码安全沙箱。连接远程 AI 前请核对上下文预览。"; color: root.palette.muted; wrapMode: Text.Wrap }
        }

        Text { text: "LLM Interview Lab v" + Qt.application.version + " · 中文优先桌面体验"; color: root.palette.muted; font.pixelSize: 12 }
    }

    FileDialog {
        id: codexPicker
        title: "选择 Codex 可执行文件"
        fileMode: FileDialog.OpenFile
        onAccepted: app.setCodexExecutable(selectedFile.toString())
    }

    Dialog {
        id: refreshWarningDialog
        objectName: "refreshDirtyDraftDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(460, root.width - 48)
        implicitHeight: 220
        height: implicitHeight
        title: "丢弃未保存编辑并刷新？"
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            app.refresh()
            refreshRequested = false
        }
        contentItem: ColumnLayout {
            spacing: 8
            Text {
                Layout.fillWidth: true
                text: (app.submissionDirty
                       ? "当前题目有未保存的编辑。"
                       : "")
                      + (app.coachStreaming
                         ? " Coach 正在生成回答。"
                         : "")
                      + (app.busy && !app.coachStreaming
                         ? " 本地操作正在进行。"
                         : "")
                      + "刷新会重新读取磁盘快照，并停止未完成的本地操作；未保存内容可能丢失。请先保存或等待完成，或确认继续刷新。"
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "刷新不会修改课程或其他 Profile。"
                color: root.palette.muted
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }
        }
    }

    Dialog {
        id: migrationDialog
        visible: app.legacyMigrationAvailable
        modal: true
        title: "发现旧版桌面数据"
        anchors.centerIn: parent
        width: Math.min(560, root.width - 48)
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 14
            Text {
                Layout.fillWidth: true
                text: "检测到 v0.4.0-alpha.1 的学习档案。迁移会先复制、计算 SHA-256 并保留备份；不会删除或覆盖旧目录。\n\n旧目录：" + app.legacyDataDirectory
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                Button { text: "稍后处理"; onClicked: { app.dismissLegacyMigration(); migrationDialog.close() } }
                Button { text: "安全复制"; highlighted: true; onClicked: { app.migrateLegacyData(); migrationDialog.close() } }
            }
        }
    }
}
