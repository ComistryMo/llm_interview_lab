import QtQuick

Rectangle {
    id: surface

    property var theme: null
    property string level: "base"
    property int padding: theme ? theme.space4 : 16
    property int cornerRadius: theme ? theme.radiusLarge : 12
    property bool outlined: true
    property bool interactive: false
    property bool selected: false
    property bool busy: false
    property string accessibleName: ""
    signal activated()
    default property alias content: contentHost.data

    readonly property color baseColor: {
        if (level === "canvas")
            return theme ? theme.canvas : "#fafaf9"
        if (level === "raised")
            return theme ? theme.surfaceRaised : "#ffffff"
        if (level === "sunken")
            return theme ? theme.surfaceSunken : "#eeede8"
        if (level === "chrome")
            return theme ? theme.chrome : "#ecebe6"
        return theme ? theme.surface : "#fbfaf7"
    }

    color: interactive && (hoverHandler.hovered || tapHandler.pressed)
           ? (theme ? theme.surfaceHover : "#f1f0eb") : baseColor
    radius: cornerRadius
    border.color: activeFocus || selected
                  ? (theme ? theme.focusRing : "#315ec7")
                  : outlined ? (theme ? theme.borderSubtle : "#e2e0d9") : "transparent"
    border.width: activeFocus ? 2 : 1
    opacity: enabled ? 1 : 0.58
    activeFocusOnTab: interactive && enabled
    implicitWidth: Math.max(1, contentHost.childrenRect.width + padding * 2)
    implicitHeight: Math.max(1, contentHost.childrenRect.height + padding * 2)
    Accessible.role: interactive ? Accessible.Button : Accessible.Grouping
    Accessible.name: accessibleName
    Accessible.focusable: interactive
    Accessible.focused: activeFocus
    Accessible.pressed: tapHandler.pressed
    Keys.onSpacePressed: if (interactive && enabled && !busy) activated()
    Keys.onReturnPressed: if (interactive && enabled && !busy) activated()

    Item {
        id: contentHost
        anchors.fill: parent
        anchors.margins: surface.padding
        opacity: surface.busy ? 0.55 : 1
    }

    HoverHandler {
        id: hoverHandler
        enabled: surface.interactive && surface.enabled && !surface.busy
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    TapHandler {
        id: tapHandler
        enabled: surface.interactive && surface.enabled && !surface.busy
        onTapped: {
            surface.forceActiveFocus()
            surface.activated()
        }
    }

    LabBusyIndicator {
        anchors.centerIn: parent
        theme: surface.theme
        running: surface.busy
    }
}
