import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts

Basic.Dialog {
    id: dialog

    property var theme: null
    property string message: ""
    property string detailText: ""
    property string primaryText: qsTr("确认")
    property string secondaryText: qsTr("取消")
    property bool showSecondary: true
    property bool primaryEnabled: true
    property bool primaryBusy: false
    property bool autoClose: true
    property alias bodyData: extraContent.data
    signal primaryTriggered()
    signal secondaryTriggered()

    modal: true
    Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.45) }
    header: null
    footer: null
    focus: true
    closePolicy: Popup.CloseOnEscape
    padding: theme ? theme.space6 : 24
    leftMargin: 24
    rightMargin: 24
    topMargin: 24
    bottomMargin: 24
    implicitWidth: 520
    implicitHeight: contentBody.implicitHeight + topPadding + bottomPadding
    background: Rectangle {
        radius: dialog.theme ? dialog.theme.radiusLarge : 12
        color: dialog.theme ? dialog.theme.surfaceRaised : "#ffffff"
        border.color: dialog.theme ? dialog.theme.borderDefault : "#cfcdc5"
        border.width: 1
    }

    contentItem: ColumnLayout {
        id: contentBody
        spacing: dialog.theme ? dialog.theme.space4 : 16

        LabText {
            visible: dialog.title.length > 0
            Layout.fillWidth: true
            theme: dialog.theme
            text: dialog.title
            variant: "section"
            strong: true
            wrapMode: Text.Wrap
        }

        LabText {
            visible: dialog.message.length > 0
            Layout.fillWidth: true
            theme: dialog.theme
            text: dialog.message
            variant: "bodyLarge"
            wrapMode: Text.Wrap
        }

        LabText {
            visible: dialog.detailText.length > 0
            Layout.fillWidth: true
            theme: dialog.theme
            text: dialog.detailText
            tone: "muted"
            wrapMode: Text.Wrap
        }

        ColumnLayout {
            id: extraContent
            Layout.fillWidth: true
            spacing: dialog.theme ? dialog.theme.space3 : 12
        }

        LabDivider {
            Layout.fillWidth: true
            theme: dialog.theme
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: dialog.theme ? dialog.theme.space2 : 8
            Item { Layout.fillWidth: true }
            LabButton {
                visible: dialog.showSecondary
                theme: dialog.theme
                text: dialog.secondaryText
                variant: "ghost"
                onClicked: {
                    dialog.secondaryTriggered()
                    if (dialog.autoClose)
                        dialog.reject()
                }
            }
            LabButton {
                id: primaryButton
                theme: dialog.theme
                text: dialog.primaryText
                variant: "primary"
                busy: dialog.primaryBusy
                enabled: dialog.primaryEnabled && !dialog.primaryBusy
                onClicked: {
                    dialog.primaryTriggered()
                    if (dialog.autoClose)
                        dialog.accept()
                }
            }
        }
    }

    onOpened: primaryButton.forceActiveFocus()
}
