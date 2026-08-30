import QtQuick

Rectangle {
    id: card
    property color cardColor: "#ffffff"
    property color borderColor: "#d9e0ea"
    // A narrow accent rail gives priority cards a consistent visual anchor
    // without adding another card variant or changing their content API.
    property color accentColor: "transparent"
    // Keep surfaces compact enough for a 620px-tall window.  Pages can still
    // opt into a larger inset for a prominent hero, but the shared default
    // should not make every section read like a floating dashboard tile.
    property int padding: 16
    // Prominent cards (for example the current task on Home) get a slightly
    // stronger frame without introducing a second card component or changing
    // the content contract used by existing pages.
    property bool prominent: false
    default property alias content: contentColumn.data
    color: cardColor
    // Slightly generous corners and a quiet frame make the surface feel
    // deliberate at both desktop scales without turning every section into a
    // floating, over-rounded tile.
    radius: prominent ? 12 : 10
    border.color: borderColor
    border.width: prominent ? 2 : 1
    implicitHeight: contentColumn.implicitHeight + padding * 2

    Rectangle {
        visible: card.accentColor.a > 0.001 && parent.height > 32
        x: 1
        y: 14
        width: 3
        height: Math.max(0, parent.height - 28)
        radius: 2
        color: card.accentColor
        antialiasing: true
    }

    Column {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: card.padding
        spacing: 12
    }
}
