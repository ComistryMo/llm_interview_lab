import QtQuick

Rectangle {
    id: card
    property color cardColor: "#ffffff"
    property color borderColor: "#d9e0ea"
    property int padding: 20
    default property alias content: contentColumn.data
    color: cardColor
    radius: 12
    border.color: borderColor
    border.width: 1
    implicitHeight: contentColumn.implicitHeight + padding * 2

    Column {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: card.padding
        spacing: 10
    }
}
