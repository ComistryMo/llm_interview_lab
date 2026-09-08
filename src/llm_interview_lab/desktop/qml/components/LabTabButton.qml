import QtQuick
import QtQuick.Controls.Basic as Basic

Basic.TabButton {
    id: control
    property var theme: null
    implicitWidth: contentItem.implicitWidth + 32
    implicitHeight: Math.max(theme ? theme.controlHeight : 40, contentItem.implicitHeight + 16)
    padding: 8
    leftPadding: 16
    rightPadding: 16
    topInset: 0
    bottomInset: 0
    hoverEnabled: true
    font.family: theme ? theme.uiFontFamily : ""
    font.pixelSize: theme ? theme.fontBody : 14
    font.weight: checked ? Font.DemiBold : Font.Normal
    background: Rectangle {
        color: control.hovered ? (control.theme ? control.theme.surfaceHover : "#e8e8e5") : "transparent"
        radius: control.theme ? control.theme.radiusSmall : 8
        border.width: control.activeFocus ? 2 : 0
        border.color: control.theme ? control.theme.focusRing : "#4a6f98"
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 8
            anchors.bottomMargin: 0
            height: 2
            visible: control.checked
            color: control.theme ? control.theme.textStrong : "#202020"
        }
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.theme ? (control.checked ? control.theme.textStrong : control.theme.muted) : "#202020"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
