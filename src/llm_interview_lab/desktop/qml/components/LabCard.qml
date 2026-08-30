import QtQuick

Rectangle {
    id: card
    property color cardColor: "#ffffff"
    property color borderColor: "#d9e0ea"
    property int padding: 20
    // Prominent cards (for example the current task on Home) get a slightly
    // stronger frame without introducing a second card component or changing
    // the content contract used by existing pages.
    property bool prominent: false
    default property alias content: contentColumn.data
    color: cardColor
    radius: prominent ? 14 : 12
    border.color: borderColor
    border.width: prominent ? 2 : 1
    implicitHeight: contentColumn.implicitHeight + padding * 2

    Column {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: card.padding
        spacing: 11
    }
}
