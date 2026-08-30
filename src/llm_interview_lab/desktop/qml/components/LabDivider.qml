import QtQuick

Rectangle {
    id: divider

    property var theme: null
    property int orientation: Qt.Horizontal
    property int thickness: 1
    property int inset: 0

    color: theme ? theme.borderSubtle : "#e2e0d9"
    implicitWidth: orientation === Qt.Horizontal ? 1 : thickness
    implicitHeight: orientation === Qt.Horizontal ? thickness : 1
    anchors.leftMargin: orientation === Qt.Horizontal ? inset : 0
    anchors.rightMargin: orientation === Qt.Horizontal ? inset : 0
    anchors.topMargin: orientation === Qt.Vertical ? inset : 0
    anchors.bottomMargin: orientation === Qt.Vertical ? inset : 0
    Accessible.ignored: true
}
