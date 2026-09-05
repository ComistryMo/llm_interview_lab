import QtQuick
import QtQuick.Controls.Basic as Basic

Basic.TextField {
    id: control

    property var theme: null
    property string accessibleLabel: ""
    property string errorText: ""
    property bool busy: false
    readonly property bool invalid: errorText.length > 0

    enabled: !busy
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: theme ? theme.controlHeight : 40
    // Keep text inside the control on Windows styles and with enlarged CJK
    // fonts.  The default TextField vertical metrics can otherwise place the
    // baseline half outside the painted background.
    height: Math.max(implicitHeight, theme ? theme.scaledPx(44) : 44)
    verticalAlignment: Text.AlignVCenter
    clip: true
    leftPadding: 12
    rightPadding: busy ? 38 : 12
    topPadding: 8
    bottomPadding: 8
    color: theme ? theme.textStrong : "#2c2e29"
    // Basic has no floating label or style-owned top inset. Keep the existing
    // focus/IME-aware hint without Material moving the background underneath it.
    placeholderTextColor: "transparent"
    selectionColor: theme ? theme.accent : "#315ec7"
    selectedTextColor: theme ? theme.accentForeground : "#ffffff"
    font.pixelSize: theme ? theme.scaledPx(14) : 14
    font.family: theme ? theme.uiFontFamily : ""
    selectByMouse: true
    Accessible.role: Accessible.EditableText
    Accessible.name: accessibleLabel || placeholderText
    Accessible.description: invalid ? errorText : ""
    Accessible.focusable: true
    Accessible.focused: activeFocus

    background: Rectangle {
        radius: control.theme ? control.theme.radiusMedium : 9
        color: control.enabled
               ? (control.theme ? control.theme.surfaceRaised : "#ffffff")
               : (control.theme ? control.theme.surfaceSunken : "#eeede8")
        border.color: control.invalid
                      ? (control.theme ? control.theme.danger : "#b44249")
                      : control.activeFocus
                        ? (control.theme ? control.theme.focusRing : "#315ec7")
                        : control.hovered
                          ? (control.theme ? control.theme.borderStrong : "#a9aaa2")
                          : (control.theme ? control.theme.controlBorder : "#cfcdc5")
        border.width: control.activeFocus || control.invalid ? 2 : 1
    }

    Text {
        id: controlledPlaceholder
        objectName: "labTextFieldPlaceholder"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: control.leftPadding
        anchors.rightMargin: control.rightPadding
        // Hide on focus as soon as the learner starts editing.  Some input
        // methods report their first composition keystroke before Qt updates
        // ``inputMethodComposing`` or ``text``; relying on those signals alone
        // briefly paints the hint over the composing glyph.
        visible: control.text.length === 0 && !control.activeFocus && !control.inputMethodComposing
        text: control.placeholderText
        color: control.theme ? control.theme.subtle : "#858880"
        font: control.font
        elide: Text.ElideRight
        maximumLineCount: 1
        verticalAlignment: Text.AlignVCenter
        z: 2
    }

    LabBusyIndicator {
        anchors.right: parent.right
        anchors.rightMargin: 11
        anchors.verticalCenter: parent.verticalCenter
        width: 16
        height: 16
        theme: control.theme
        running: control.busy
    }
}
