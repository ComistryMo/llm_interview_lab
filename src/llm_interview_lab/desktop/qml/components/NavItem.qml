import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Controls.impl

Basic.Button {
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
    implicitHeight: Math.max(compact ? 44 : 40, contentItem.implicitHeight + 16)
    topInset: 0
    bottomInset: 0
    topPadding: 8
    bottomPadding: 8
    leftPadding: compact ? 10 : 12
    rightPadding: compact ? 10 : 12
    spacing: 10
    font.pixelSize: theme ? theme.scaledPx(13) : 13
    font.family: theme ? theme.uiFontFamily : ""
    font.weight: selected ? Font.DemiBold : Font.Normal
    display: compact ? AbstractButton.IconOnly : AbstractButton.TextBesideIcon
    icon.source: iconSource
    icon.color: theme ? theme.textStrong : "#303030"
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
                 ? (control.theme ? control.theme.surfaceHover : "#e8e8e5")
               : control.hovered
                 ? (control.theme ? control.theme.surfaceHover : "#f1f0eb")
                 : "transparent"
        border.color: control.activeFocus
                      ? (control.theme ? control.theme.focusRing : "#315ec7")
                      : "transparent"
        border.width: control.activeFocus ? 2 : 1

    }

    contentItem: IconLabel {
        opacity: control.busy ? 0 : 1
        spacing: control.spacing
        display: control.display
        alignment: control.compact ? Qt.AlignCenter : Qt.AlignLeft
        icon: control.icon
        text: control.text
        font: control.font
        color: control.theme ? control.theme.textStrong : "#303030"
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

    ToolTip.visible: compact && hovered && label.length > 0
    ToolTip.text: label
    ToolTip.delay: 450
}
