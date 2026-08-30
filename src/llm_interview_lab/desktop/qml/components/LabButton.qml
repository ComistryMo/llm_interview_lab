import QtQuick
import QtQuick.Controls

Button {
    id: control

    property var theme: null
    property string variant: "secondary"
    property bool busy: false
    property bool compact: false
    property url iconSource: ""
    property string accessibleName: text
    property string toolTip: ""

    readonly property color resolvedForeground: {
        if (!enabled)
            return theme ? theme.subtle : "#858880"
        if (variant === "primary")
            return theme ? theme.accentForeground : "#ffffff"
        if (variant === "danger")
            return theme ? theme.dangerForeground : "#ffffff"
        return theme ? theme.text : "#2c2e29"
    }
    readonly property color resolvedBackground: {
        if (!enabled)
            return theme ? theme.surfaceSunken : "#eeede8"
        if (variant === "primary") {
            if (down)
                return theme ? theme.accentPressed : "#23489e"
            return hovered ? (theme ? theme.accentHover : "#2852b4")
                           : (theme ? theme.accent : "#315ec7")
        }
        if (variant === "danger") {
            var danger = theme ? theme.danger : "#b44249"
            return down ? Qt.darker(danger, 1.18) : hovered ? Qt.lighter(danger, 1.08) : danger
        }
        if (variant === "ghost")
            return down ? (theme ? theme.surfaceSunken : "#eeede8")
                        : hovered ? (theme ? theme.surfaceHover : "#f1f0eb") : "transparent"
        return down ? (theme ? theme.surfaceSunken : "#eeede8")
                    : hovered ? (theme ? theme.surfaceHover : "#f1f0eb")
                              : (theme ? theme.surfaceRaised : "#ffffff")
    }
    readonly property color resolvedBorder: {
        if (activeFocus)
            return theme ? theme.focusRing : "#315ec7"
        if (variant === "primary" || variant === "danger")
            return resolvedBackground
        if (variant === "ghost")
            return "transparent"
        return theme ? theme.controlBorder : "#cfcdc5"
    }

    enabled: !busy
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: compact ? (theme ? theme.controlHeightCompact : 34)
                            : (theme ? theme.controlHeight : 40)
    implicitWidth: Math.max(compact ? 72 : 96, contentItem.implicitWidth + leftPadding + rightPadding)
    leftPadding: compact ? 12 : 16
    rightPadding: compact ? 12 : 16
    spacing: 8
    font.pixelSize: theme ? theme.scaledPx(14) : 14
    font.family: theme ? theme.uiFontFamily : ""
    font.weight: variant === "primary" ? Font.DemiBold : Font.Medium
    palette.buttonText: resolvedForeground
    icon.source: iconSource
    icon.color: resolvedForeground
    icon.width: compact ? 16 : 18
    icon.height: compact ? 16 : 18
    display: iconSource.toString().length > 0 ? AbstractButton.TextBesideIcon
                                              : AbstractButton.TextOnly
    Accessible.role: Accessible.Button
    Accessible.name: accessibleName || text
    Accessible.description: busy ? qsTr("正在处理") : toolTip
    Accessible.focusable: true
    Accessible.focused: activeFocus
    Accessible.pressed: down

    background: Rectangle {
        radius: control.theme ? control.theme.radiusMedium : 9
        color: control.resolvedBackground
        border.color: control.resolvedBorder
        border.width: control.activeFocus ? 2 : 1

        Behavior on color {
            enabled: !!control.theme && !control.theme.reducedMotion
            ColorAnimation { duration: control.theme ? control.theme.duration(90) : 90 }
        }
    }

    LabBusyIndicator {
        anchors.centerIn: parent
        theme: control.theme
        running: control.busy
        indicatorColor: control.variant === "primary" || control.variant === "danger"
                        ? control.resolvedForeground
                        : (control.theme ? control.theme.accent : "#315ec7")
    }

    contentItem.opacity: busy ? 0 : 1
    ToolTip.visible: toolTip.length > 0 && hovered && !busy
    ToolTip.text: toolTip
    ToolTip.delay: 500
}
