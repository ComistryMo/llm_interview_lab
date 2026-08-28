import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import "components"
import "pages"

ApplicationWindow {
    id: window
    width: 1280
    height: 800
    minimumWidth: 1080
    minimumHeight: 680
    visible: true
    title: "LLM Interview Lab"
    Material.theme: backend.theme === "dark" ? Material.Dark
                    : backend.theme === "light" ? Material.Light
                    : Material.System
    Material.accent: "#2563eb"

    property bool dark: Material.theme === Material.Dark
    property var colors: ({
        "background": dark ? "#0f141d" : "#f5f7fb",
        "surface": dark ? "#171e29" : "#ffffff",
        "surfaceAlt": dark ? "#202938" : "#eef2f7",
        "border": dark ? "#303b4d" : "#d9e0ea",
        "text": dark ? "#edf2f7" : "#18212f",
        "muted": dark ? "#a3aec0" : "#5f6b7c",
        "accent": "#2563eb",
        "success": "#16845b",
        "warning": "#b56616",
        "danger": "#c63d4f"
    })
    font.pixelSize: Math.round(14 * backend.fontScale)
    color: colors.background

    menuBar: MenuBar {
        Menu {
            title: "应用"
            Action { text: "关于 LLM Interview Lab"; onTriggered: aboutDialog.open() }
            MenuSeparator {}
            Action { text: "设置"; shortcut: StandardKey.Preferences; onTriggered: backend.navigate("settings") }
            Action { text: "退出"; shortcut: StandardKey.Quit; onTriggered: Qt.quit() }
        }
        Menu {
            title: "训练"
            Action { text: "继续训练"; onTriggered: backend.navigate("home") }
            Action { text: "运行公开测试"; shortcut: StandardKey.Refresh; enabled: backend.currentPage === "exercise"; onTriggered: backend.runTests() }
        }
    }

    Shortcut {
        sequences: ["Ctrl+Return", "Meta+Return"]
        enabled: backend.currentPage === "exercise"
        onActivated: backend.runTests()
    }

    // Keep the documented test shortcut available on both Windows/Linux and
    // macOS.  StandardKey.Refresh is platform-dependent and does not map to
    // Ctrl/Command+R in every Qt style, so declare the concrete sequences too.
    Shortcut {
        sequences: ["Ctrl+R", "Meta+R"]
        enabled: backend.currentPage === "exercise"
        onActivated: backend.runTests()
    }

    onClosing: backend.shutdown()

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 216
            Layout.fillHeight: true
            color: window.colors.surface
            border.color: window.colors.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 18
                    Rectangle {
                        width: 34; height: 34; radius: 9; color: window.colors.accent
                        Text { anchors.centerIn: parent; text: "LL"; color: "white"; font.bold: true }
                    }
                    ColumnLayout {
                        spacing: 0
                        Text { text: "LLM Interview Lab"; color: window.colors.text; font.bold: true; font.pixelSize: 15 }
                        Text { text: "本地 AI 面试训练工作台"; color: window.colors.muted; font.pixelSize: 11 }
                    }
                }

                Repeater {
                    model: [
                        {id: "home", label: backend.uiText("nav.home")},
                        {id: "career", label: backend.uiText("nav.career")},
                        {id: "learn", label: backend.uiText("nav.learn")},
                        {id: "interview", label: backend.uiText("nav.interview")},
                        {id: "coach", label: backend.uiText("nav.coach")},
                        {id: "progress", label: backend.uiText("nav.progress")},
                        {id: "connections", label: backend.uiText("nav.connections")},
                        {id: "settings", label: backend.uiText("nav.settings")}
                    ]
                    delegate: Button {
                        id: navButton
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 42
                        text: modelData.label
                        flat: true
                        font.weight: backend.currentPage === modelData.id ? Font.DemiBold : Font.Normal
                        onClicked: backend.navigate(modelData.id)
                        background: Rectangle {
                            radius: 8
                            color: backend.currentPage === modelData.id
                                   ? Qt.rgba(0.145, 0.388, 0.922, 0.13) : "transparent"
                        }
                        contentItem: Text {
                            text: navButton.text
                            color: backend.currentPage === modelData.id ? window.colors.accent : window.colors.text
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 12
                        }
                    }
                }

                Item { Layout.fillHeight: true }
                Rectangle { Layout.fillWidth: true; height: 1; color: window.colors.border }
                Text { text: "学习档案"; color: window.colors.muted; font.pixelSize: 11 }
                Text { text: backend.profileId; color: window.colors.text; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                Text { text: "Alpha · 数据默认保存在本机"; color: window.colors.muted; font.pixelSize: 11 }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 62
                color: window.colors.surface
                border.color: window.colors.border
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 28
                    anchors.rightMargin: 28
                    Text {
                        text: ({home:"首页", career:"求职材料", learn:"刷题训练", exercise:"答题工作区", interview:"模拟面试", coach:"AI 教练", progress:"学习进度", connections:"AI 连接", settings:"设置"})[backend.currentPage] || "LLM Interview Lab"
                        color: window.colors.text
                        font.pixelSize: 20
                        font.weight: Font.DemiBold
                    }
                    Item { Layout.fillWidth: true }
                    StatusPill { text: backend.aiStatus; tone: backend.aiStatus.indexOf("已连接") >= 0 || backend.aiStatus.indexOf("就绪") >= 0 ? window.colors.success : window.colors.muted }
                    BusyIndicator { running: backend.busy; visible: running; implicitWidth: 28; implicitHeight: 28 }
                }
            }

            StackLayout {
                id: pages
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: ({home:0, career:1, learn:2, exercise:3, interview:4, coach:5, progress:6, connections:7, settings:8})[backend.currentPage] || 0
                HomePage { app: backend; palette: window.colors }
                CareerPage { app: backend; palette: window.colors }
                LearnPage { app: backend; palette: window.colors }
                ExercisePage { app: backend; palette: window.colors }
                InterviewPage { app: backend; palette: window.colors }
                CoachPage { app: backend; palette: window.colors }
                ProgressPage { app: backend; palette: window.colors }
                ConnectionsPage { app: backend; palette: window.colors }
                SettingsPage { app: backend; palette: window.colors }
            }
        }
    }

    OnboardingPage {
        anchors.fill: parent
        z: 20
        visible: backend.onboardingRequired
        app: backend
        palette: window.colors
    }

    Popup {
        id: toastPopup
        objectName: "globalToast"
        x: window.width - width - 30
        // Keep transient feedback away from the bottom onboarding CTA.
        y: 82
        width: Math.min(440, message.implicitWidth + 40)
        height: 52
        modal: false
        closePolicy: Popup.NoAutoClose
        background: Rectangle { color: window.dark ? "#293244" : "#172033"; radius: 9 }
        contentItem: Text {
            id: message
            color: "white"
            wrapMode: Text.Wrap
            verticalAlignment: Text.AlignVCenter
            anchors.fill: parent
            anchors.margins: 14
        }
        Timer { id: toastTimer; interval: 3600; onTriggered: toastPopup.close() }
    }
    Connections {
        target: backend
        function onToast(text) { message.text = text; toastPopup.open(); toastTimer.restart() }
    }

    Dialog {
        id: aboutDialog
        title: "关于 LLM Interview Lab"
        modal: true
        standardButtons: Dialog.Ok
        anchors.centerIn: parent
        width: 440
        contentItem: Text {
            width: 400
            text: "v0.4.0-alpha.2\n\n本地优先、岗位感知、AI 辅助的面试训练工作台。\n无需连接 AI 也可完整使用固定课程与手动模拟面试。"
            color: window.colors.text
            wrapMode: Text.Wrap
            lineHeight: 1.35
        }
    }
}
