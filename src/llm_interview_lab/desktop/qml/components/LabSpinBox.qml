import QtQuick
import QtQuick.Controls.Basic as Basic

Basic.SpinBox {
    id: control
    property var theme: null
    implicitHeight: Math.max(theme ? theme.controlHeight : 40, contentItem.implicitHeight + 16)
    implicitWidth: 160
    font.family: theme ? theme.uiFontFamily : ""
    font.pixelSize: theme ? theme.fontBody : 14
    leftPadding: 40
    rightPadding: 40
    topPadding: 8
    bottomPadding: 8
    topInset: 0
    bottomInset: 0
    palette.text: theme ? theme.textStrong : "#202020"
    palette.highlight: theme ? theme.accentSoft : "#e9eff5"
    palette.highlightedText: palette.text
    contentItem: TextInput {
        text: control.displayText
        font: control.font
        color: control.palette.text
        selectionColor: control.palette.highlight
        selectedTextColor: control.palette.highlightedText
        horizontalAlignment: TextInput.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: control.inputMethodHints
        clip: true
    }
    background: Rectangle {
        color: control.theme ? control.theme.surfaceRaised : "white"
        radius: control.theme ? control.theme.radiusMedium : 8
        border.width: control.activeFocus ? 2 : 1
        border.color: control.theme ? (control.activeFocus ? control.theme.focusRing : control.theme.controlBorder) : "#c5c5c0"
    }
    up.indicator: Rectangle {
        x: control.mirrored ? 1 : control.width - width - 1
        y: 1
        implicitWidth: 36
        height: control.height - 2
        radius: 7
        color: control.up.pressed || control.up.hovered ? (control.theme ? control.theme.surfaceHover : "#e8e8e5") : "transparent"
        Rectangle { anchors.centerIn: parent; width: 12; height: 2; color: control.palette.text }
        Rectangle { anchors.centerIn: parent; width: 2; height: 12; color: control.palette.text }
    }
    down.indicator: Rectangle {
        x: control.mirrored ? control.width - width - 1 : 1
        y: 1
        implicitWidth: 36
        height: control.height - 2
        radius: 7
        color: control.down.pressed || control.down.hovered ? (control.theme ? control.theme.surfaceHover : "#e8e8e5") : "transparent"
        Rectangle { anchors.centerIn: parent; width: 12; height: 2; color: control.palette.text }
    }
}
