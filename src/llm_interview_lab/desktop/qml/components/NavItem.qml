import QtQuick
import QtQuick.Controls

Button {
    id: control

    property var theme: null
    property string label: ""
    property url iconSource: ""
    property bool selected: false
    property bool compact: false
    property bool busy: false
    property string badgeText: ""

    text: compact ? "" : label
    enabled: !busy
    checkable: false
    highlighted: selected
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: compact ? 44 : 184
    implicitHeight: compact ? 44 : 40
    leftPadding: compact ? 10 : 12
    rightPadding: compact ? 10 : 12
    spacing: 10
    font.pixelSize: theme ? theme.scaledPx(13) : 13
    font.family: theme ? theme.uiFontFamily : ""
    font.weight: selected ? Font.DemiBold : Font.Normal
    display: compact ? AbstractButton.IconOnly : AbstractButton.TextBesideIcon
    icon.source: iconSource
    icon.color: selected
                ? (theme ? theme.accent : "#315ec7")
                : (theme ? theme.muted : "#666961")
    icon.width: 18
    icon.height: 18
    palette.buttonText: selected
                        ? (theme ? theme.textStrong : "#1f211d")
                        : (theme ? theme.text : "#2c2e29")
    Accessible.role: Accessible.Button
    Accessible.name: label
    Accessible.description: selected ? qsTr("当前页面") : ""
    Accessible.focusable: true
    Accessible.focused: activeFocus
    Accessible.selected: selected
    Accessible.pressed: down

    background: Rectangle {
        radius: control.theme ? control.theme.radiusMedium : 9
        color: control.down
               ? (control.theme ? control.theme.surfaceSunken : "#eeede8")
               : control.selected
                 ? (control.theme ? control.theme.accentSoft : "#e7e9fa")
               : control.hovered
                 ? (control.theme ? control.theme.surfaceHover : "#f1f0eb")
                 : "transparent"
        border.color: control.activeFocus
                      ? (control.theme ? control.theme.focusRing : "#315ec7")
                      : "transparent"
        border.width: control.activeFocus ? 2 : 1

        Rectangle {
            visible: control.selected
            width: 2
            height: Math.max(16, parent.height - 16)
            radius: 2
            anchors.left: parent.left
            anchors.leftMargin: 2
            anchors.verticalCenter: parent.verticalCenter
            color: control.theme ? control.theme.accent : "#315ec7"
        }
    }

    Rectangle {
        visible: !control.compact && control.badgeText.length > 0
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.verticalCenter: parent.verticalCenter
        implicitWidth: badgeLabel.implicitWidth + 12
        implicitHeight: 20
        radius: 10
        color: control.theme ? control.theme.surfaceSunken : "#eeede8"
        border.color: control.theme ? control.theme.borderSubtle : "#e2e0d9"
        LabText {
            id: badgeLabel
            anchors.centerIn: parent
            theme: control.theme
            text: control.badgeText
            variant: "caption"
            tone: "muted"
        }
    }

    LabBusyIndicator {
        anchors.centerIn: parent
        theme: control.theme
        running: control.busy
    }

    contentItem.opacity: busy ? 0 : 1
    ToolTip.visible: compact && hovered && label.length > 0
    ToolTip.text: label
    ToolTip.delay: 450
}
