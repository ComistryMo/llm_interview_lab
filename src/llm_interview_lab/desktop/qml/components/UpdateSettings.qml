import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var manager
    required property var theme
    readonly property var update: manager.state
    readonly property bool busy: ["checking", "downloading", "cancelling"].indexOf(update.status) >= 0
    spacing: 12

    LabText { theme: root.theme; text: "应用更新"; variant: "section"; strong: true }
    LabText {
        theme: root.theme; Layout.fillWidth: true; wrapMode: Text.Wrap
        text: "当前版本 " + root.update.current_version + " · 官方 GitHub Releases"
        tone: "muted"; variant: "caption"
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 12
        LabText { theme: root.theme; text: "发布渠道" }
        LabComboBox {
            objectName: "updateChannel"
            theme: root.theme; Layout.fillWidth: true; Layout.maximumWidth: 250
            model: ["包含预发布版（Alpha / RC）", "仅正式版"]
            currentIndex: root.update.channel === "stable" ? 1 : 0
            enabled: !root.busy
            onActivated: root.manager.setChannel(currentIndex === 1 ? "stable" : "preview")
        }
        Item { Layout.fillWidth: true }
    }
    LabText {
        objectName: "updateStatus"
        theme: root.theme; Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.update.message
        color: root.update.status === "error" ? root.theme.warning : root.theme.muted
    }
    LabText {
        theme: root.theme; Layout.fillWidth: true; wrapMode: Text.Wrap; strong: true
        visible: Boolean(root.update.release_version)
        text: "可用版本 " + (root.update.release_version || "")
    }
    ScrollView {
        Layout.fillWidth: true
        visible: Boolean(root.update.notes)
        Layout.preferredHeight: Math.min(220, notes.implicitHeight + 16)
        clip: true
        LabText {
            id: notes
            theme: root.theme; width: parent.width - 16
            text: root.update.notes || ""; wrapMode: Text.Wrap; textFormat: Text.PlainText
        }
    }
    ProgressBar {
        objectName: "updateDownloadProgress"
        visible: root.update.status === "downloading" || root.update.status === "cancelling"
        Layout.fillWidth: true; value: (root.update.progress || 0) / 100
        implicitHeight: 6
        background: Rectangle { radius: 3; color: root.theme.surfaceHover }
        contentItem: Item {
            Rectangle { width: parent.width * parent.parent.visualPosition; height: parent.height; radius: 3; color: root.theme.focusRing }
        }
    }
    LabText {
        theme: root.theme; visible: root.update.status === "downloaded"
        Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; variant: "caption"; tone: "muted"
        text: "SHA-256: " + (root.update.sha256 || "")
    }
    Flow {
        Layout.fillWidth: true; Layout.preferredHeight: childrenRect.height; spacing: 8
        LabButton {
            objectName: "checkDesktopUpdate"; theme: root.theme
            text: root.update.status === "checking" ? "正在检查…" : "检查更新"
            enabled: !root.busy
            onClicked: root.manager.check()
        }
        LabButton {
            objectName: "downloadDesktopUpdate"; theme: root.theme; variant: "primary"
            visible: Boolean(root.update.asset_url) && ["available", "error", "cancelled"].indexOf(root.update.status) >= 0
            enabled: !root.busy
            text: root.update.status === "available" ? "下载新版" : "重试下载"
            onClicked: root.manager.download()
        }
        LabButton {
            objectName: "cancelDesktopUpdate"; theme: root.theme
            visible: root.update.status === "downloading" || root.update.status === "cancelling"
            enabled: root.update.status === "downloading"; text: "取消下载"
            onClicked: root.manager.cancel()
        }
        LabButton {
            objectName: "openUpdateDownload"; theme: root.theme; variant: "primary"
            visible: root.update.status === "downloaded"; text: "打开下载位置"
            onClicked: root.manager.openDownloadLocation()
        }
        LabButton {
            objectName: "openOfficialReleases"; theme: root.theme; variant: "ghost"
            text: "官方发布页面"; onClicked: root.manager.openReleasePage()
        }
    }
    LabText {
        theme: root.theme; Layout.fillWidth: true; wrapMode: Text.Wrap; variant: "caption"; tone: "muted"
        text: "仅下载并校验，不执行安装、不覆盖运行中的应用。Windows 请解压到新目录；macOS 请退出旧版后再替换应用。学习档案、连接和本地语音模型仍使用原数据位置。"
    }
}
