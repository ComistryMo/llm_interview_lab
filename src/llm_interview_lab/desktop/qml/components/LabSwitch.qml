import QtQuick
import QtQuick.Controls.Basic as Basic

Basic.Switch {
    id: control
    property var theme: null
    implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
    implicitHeight: Math.max(theme ? theme.controlHeight : 40, contentItem.implicitHeight + 16)
    padding: 8
    leftPadding: 52
    rightPadding: 0
    font.family: theme ? theme.uiFontFamily : ""
    font.pixelSize: theme ? theme.fontBody : 14
    FontMetrics { id: metrics; font: control.font }
    indicator: Rectangle {
        width: 40
        height: 24
        y: control.topPadding + Math.max(0, (metrics.height - height) / 2)
        radius: 12
        color: control.checked ? (control.theme ? control.theme.accent : "#3c638e")
                               : control.theme ? control.theme.controlBorder : "#8d8d89"
        border.width: control.activeFocus ? 2 : 0
        border.color: control.theme ? control.theme.focusRing : "#4a6f98"
        opacity: control.enabled ? 1 : 0.5
        Rectangle {
            x: control.visualPosition * (parent.width - width - 6) + 3
            y: 3
            width: 18
            height: 18
            radius: 9
            color: control.theme ? (control.checked ? control.theme.accentForeground : control.theme.textStrong) : "white"
        }
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.theme ? (control.enabled ? control.theme.textStrong : control.theme.subtle) : "#202020"
        wrapMode: Text.Wrap
        lineHeight: 1.45
    }
}
