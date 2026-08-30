import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control

    property var theme: null

    hoverEnabled: true
    minimumSize: 0.08
    implicitWidth: orientation === Qt.Vertical ? 10 : 80
    implicitHeight: orientation === Qt.Horizontal ? 10 : 80
    padding: 2
    Accessible.role: Accessible.ScrollBar
    Accessible.name: orientation === Qt.Vertical ? qsTr("垂直滚动") : qsTr("水平滚动")

    contentItem: Rectangle {
        implicitWidth: 6
        implicitHeight: 6
        radius: 3
        color: control.pressed
               ? (control.theme ? control.theme.borderStrong : "#a9aaa2")
               : control.hovered
                 ? (control.theme ? control.theme.muted : "#666961")
                 : (control.theme ? control.theme.subtle : "#858880")
        opacity: control.enabled && control.size < 1.0 ? (control.active ? 0.9 : 0.55) : 0

        Behavior on opacity {
            enabled: !!control.theme && !control.theme.reducedMotion
            NumberAnimation { duration: control.theme ? control.theme.duration(120) : 120 }
        }
    }

    background: Rectangle {
        color: "transparent"
    }
}
