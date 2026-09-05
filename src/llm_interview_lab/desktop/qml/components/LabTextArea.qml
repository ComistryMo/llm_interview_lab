import QtQuick
import QtQuick.Controls.Basic as Basic

// The Basic input keeps its placeholder inside the same padding as the text;
// Material's floating label is incompatible with our solid custom surfaces.
Basic.TextArea {
    id: control
    property var theme: null

    padding: 12
    leftPadding: padding
    rightPadding: padding
    topInset: 0
    bottomInset: 0
    clip: true
    selectByMouse: true
    wrapMode: TextEdit.Wrap
    color: theme ? theme.textStrong : palette.text
    selectionColor: theme ? theme.accent : palette.highlight
    selectedTextColor: theme ? theme.accentForeground : palette.highlightedText
    // Hide before the first IME preedit glyph arrives. Basic also suppresses
    // the hint when text or preeditText is nonempty, including paste/commit.
    placeholderTextColor: activeFocus ? "transparent" : theme ? theme.subtle : palette.placeholderText
    font.pixelSize: theme ? theme.fontBody : 14
    font.family: theme ? theme.uiFontFamily : ""
    Accessible.name: placeholderText

    background: Rectangle {
        color: control.theme ? control.theme.surfaceSunken : control.palette.base
        radius: control.theme ? control.theme.radiusMedium : 8
        border.color: control.activeFocus
                      ? control.selectionColor
                      : control.theme ? control.theme.borderDefault : control.palette.mid
        border.width: control.activeFocus ? 2 : 1
    }
}
