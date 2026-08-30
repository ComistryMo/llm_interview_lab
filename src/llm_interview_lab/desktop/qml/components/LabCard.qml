import QtQuick

Rectangle {
    id: card

    property var theme: null
    // Compatibility surface: existing pages set these properties directly.
    property color cardColor: theme ? theme.surface : "#ffffff"
    property color borderColor: theme ? theme.borderDefault : "#d9e0ea"
    property color accentColor: "transparent"
    property int padding: 16
    property bool prominent: false

    // New opt-in interaction states. Existing cards remain passive groups.
    property bool interactive: false
    property bool selected: false
    property bool busy: false
    property string accessibleName: ""
    property int cornerRadius: prominent
                               ? (theme ? theme.radiusLarge : 12)
                               : (theme ? theme.radiusMedium : 10)
    signal activated()
    default property alias content: contentColumn.data

    readonly property color resolvedColor: interactive && enabled
                                           && (hoverHandler.hovered || tapHandler.pressed)
                                           ? (theme ? theme.surfaceHover : Qt.darker(cardColor, 1.03))
                                           : cardColor

    color: resolvedColor
    radius: cornerRadius
    border.color: activeFocus || selected
                  ? (theme ? theme.focusRing : accentColor.a > 0 ? accentColor : "#3159d9")
                  : borderColor
    border.width: activeFocus || prominent ? 2 : 1
    opacity: enabled ? 1 : 0.58
    activeFocusOnTab: interactive && enabled
    implicitWidth: contentColumn.implicitWidth + padding * 2
    implicitHeight: contentColumn.implicitHeight + padding * 2
    Accessible.role: interactive ? Accessible.Button : Accessible.Grouping
    Accessible.name: accessibleName
    Accessible.focusable: interactive
    Accessible.focused: activeFocus
    Accessible.pressed: tapHandler.pressed
    Accessible.selected: selected

    Keys.onSpacePressed: function(event) {
        if (interactive && enabled && !busy) {
            activated()
            event.accepted = true
        }
    }
    Keys.onReturnPressed: function(event) {
        if (interactive && enabled && !busy) {
            activated()
            event.accepted = true
        }
    }

    Rectangle {
        visible: card.accentColor.a > 0.001 && card.height > 32
        x: 1
        y: 14
        width: 3
        height: Math.max(0, card.height - 28)
        radius: 2
        color: card.accentColor
        antialiasing: true
    }

    Column {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: card.padding
        spacing: 12
        opacity: card.busy ? 0.55 : 1
    }

    HoverHandler {
        id: hoverHandler
        enabled: card.interactive && card.enabled && !card.busy
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    TapHandler {
        id: tapHandler
        enabled: card.interactive && card.enabled && !card.busy
        onTapped: {
            card.forceActiveFocus()
            card.activated()
        }
    }

    LabBusyIndicator {
        anchors.centerIn: parent
        theme: card.theme
        running: card.busy
    }

    Behavior on color {
        enabled: !!card.theme && !card.theme.reducedMotion
        ColorAnimation { duration: card.theme ? card.theme.duration(90) : 90 }
    }
}
