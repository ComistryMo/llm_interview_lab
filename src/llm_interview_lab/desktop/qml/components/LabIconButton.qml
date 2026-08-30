import QtQuick
import QtQuick.Controls

Button {
    id: control

    property var theme: null
    property url iconSource: ""
    property bool busy: false
    property string accessibleName: ""
    property string toolTip: accessibleName
    property string variant: "ghost"
    property int buttonSize: theme ? theme.controlHeight : 40

    readonly property color foreground: !enabled
                                        ? (theme ? theme.subtle : "#858880")
                                        : checked || highlighted
                                          ? (theme ? theme.accent : "#315ec7")
                                          : (theme ? theme.muted : "#666961")

    enabled: !busy
    checkable: false
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: buttonSize
    implicitHeight: buttonSize
    padding: 9
    display: AbstractButton.IconOnly
    icon.source: iconSource
    icon.color: foreground
    icon.width: Math.max(16, buttonSize - 20)
    icon.height: Math.max(16, buttonSize - 20)
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName || toolTip
    Accessible.description: busy ? qsTr("正在处理") : toolTip
    Accessible.focusable: true
    Accessible.focused: activeFocus
    Accessible.pressed: down
    Accessible.checked: checked

    background: Rectangle {
        radius: control.theme ? control.theme.radiusMedium : 9
        color: {
            if (control.down)
                return control.theme ? control.theme.surfaceSunken : "#eeede8"
            if (control.hovered || control.checked || control.highlighted)
                return control.theme ? control.theme.surfaceHover : "#f1f0eb"
            return "transparent"
        }
        border.color: control.activeFocus
                      ? (control.theme ? control.theme.focusRing : "#315ec7")
                      : control.checked
                        ? (control.theme ? control.theme.borderDefault : "#cfcdc5")
                        : "transparent"
        border.width: control.activeFocus ? 2 : 1
    }

    LabBusyIndicator {
        anchors.centerIn: parent
        theme: control.theme
        running: control.busy
        indicatorColor: control.foreground
    }

    contentItem.opacity: busy ? 0 : 1
    ToolTip.visible: toolTip.length > 0 && hovered && !busy
    ToolTip.text: toolTip
    ToolTip.delay: 500
}
