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
    Material.theme: backend.theme === "dark" ? Material.Dark : Material.Light
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
                        Text { text: "Local training workbench"; color: window.colors.muted; font.pixelSize: 11 }
                    }
                }

                Repeater {
                    model: [
                        {id: "home", label: "Home"},
                        {id: "career", label: "Career profile"},
                        {id: "learn", label: "Learn"},
                        {id: "interview", label: "Interview"},
                        {id: "coach", label: "AI Coach"},
                        {id: "progress", label: "Progress"},
                        {id: "connections", label: "Connections"},
                        {id: "settings", label: "Settings"}
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
                Text { text: "Profile"; color: window.colors.muted; font.pixelSize: 11 }
                Text { text: backend.profileId; color: window.colors.text; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                Text { text: "Alpha · local-first"; color: window.colors.muted; font.pixelSize: 11 }
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
                        text: ({home:"Home", career:"Career profile", learn:"Learning path", exercise:"Exercise workspace", interview:"Mock interview", coach:"AI coach", progress:"Progress", connections:"AI connections", settings:"Settings"})[backend.currentPage] || "LLM Interview Lab"
                        color: window.colors.text
                        font.pixelSize: 20
                        font.weight: Font.DemiBold
                    }
                    Item { Layout.fillWidth: true }
                    StatusPill { text: backend.aiStatus; tone: backend.aiStatus.indexOf("connected") >= 0 ? window.colors.success : window.colors.muted }
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
        x: window.width - width - 30
        y: window.height - height - 30
        width: Math.min(440, message.implicitWidth + 40)
        height: 52
        modal: false
        closePolicy: Popup.NoAutoClose
        background: Rectangle { color: window.dark ? "#293244" : "#172033"; radius: 9 }
        contentItem: Text { id: message; color: "white"; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter }
        Timer { id: toastTimer; interval: 3600; onTriggered: toastPopup.close() }
    }
    Connections {
        target: backend
        function onToast(text) { message.text = text; toastPopup.open(); toastTimer.restart() }
    }
}
