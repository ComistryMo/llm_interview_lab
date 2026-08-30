import QtQuick
import QtQuick.Controls

ComboBox {
    id: control

    property var theme: null
    property string accessibleLabel: ""

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: theme ? theme.controlHeight : 40
    leftPadding: 12
    rightPadding: 34
    font.pixelSize: theme ? theme.scaledPx(14) : 14
    font.family: theme ? theme.uiFontFamily : ""
    Accessible.role: Accessible.ComboBox
    Accessible.name: accessibleLabel || currentText
    Accessible.focusable: true
    Accessible.focused: activeFocus

    contentItem: Text {
        leftPadding: 0
        rightPadding: 0
        text: control.displayText
        color: control.enabled
               ? (control.theme ? control.theme.textStrong : "#202227")
               : (control.theme ? control.theme.subtle : "#858880")
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: control.width - width - 12
        anchors.verticalCenter: parent.verticalCenter
        text: "⌄"
        color: control.theme ? control.theme.muted : "#666961"
        font.pixelSize: control.theme ? control.theme.scaledPx(16) : 16
    }

    background: Rectangle {
        radius: control.theme ? control.theme.radiusMedium : 9
        color: control.theme ? control.theme.surfaceRaised : "#ffffff"
        border.color: control.activeFocus
                      ? (control.theme ? control.theme.focusRing : "#315ec7")
                      : control.hovered
                        ? (control.theme ? control.theme.borderStrong : "#a9aaa2")
                        : (control.theme ? control.theme.controlBorder : "#cfcdc5")
        border.width: control.activeFocus ? 2 : 1
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 260)
        padding: 4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }

        background: Rectangle {
            radius: control.theme ? control.theme.radiusMedium : 9
            color: control.theme ? control.theme.surfaceRaised : "#ffffff"
            border.color: control.theme ? control.theme.borderDefault : "#cfcdc5"
        }
    }

    delegate: ItemDelegate {
        required property var modelData
        required property int index
        width: control.width - 8
        height: control.theme ? control.theme.controlHeight : 40
        highlighted: control.highlightedIndex === index
        hoverEnabled: true
        contentItem: Text {
            text: control.textRole ? modelData[control.textRole] : modelData
            color: control.theme ? control.theme.textStrong : "#202227"
            font: control.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: control.theme ? control.theme.radiusSmall : 6
            color: parent.highlighted || parent.hovered
                   ? (control.theme ? control.theme.surfaceHover : "#f1f0eb")
                   : "transparent"
        }
    }
}
