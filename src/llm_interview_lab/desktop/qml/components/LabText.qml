import QtQuick

Text {
    id: control

    property var theme: null
    property string variant: "body"
    property string tone: "default"
    property bool strong: false
    property bool monospace: false

    readonly property color resolvedColor: {
        if (tone === "muted")
            return theme ? theme.muted : "#666961"
        if (tone === "subtle")
            return theme ? theme.subtle : "#858880"
        if (tone === "accent")
            return theme ? theme.accent : "#315ec7"
        if (tone === "success")
            return theme ? theme.success : "#28745b"
        if (tone === "warning")
            return theme ? theme.warning : "#8b5b16"
        if (tone === "danger")
            return theme ? theme.danger : "#b44249"
        return theme ? (strong ? theme.textStrong : theme.text) : "#2c2e29"
    }
    readonly property int resolvedSize: {
        var base = variant === "title" ? 26
                 : variant === "section" ? 18
                 : variant === "bodyLarge" ? 15
                 : variant === "caption" ? 12 : 14
        return theme ? theme.scaledPx(base) : base
    }

    color: resolvedColor
    font.pixelSize: resolvedSize
    font.weight: strong || variant === "title" || variant === "section"
                 ? Font.DemiBold : Font.Normal
    font.family: monospace
                 ? (theme ? theme.monospaceFontFamily : "monospace")
                 : (theme ? theme.uiFontFamily : "")
    lineHeight: variant === "title" ? 1.15 : 1.35
    wrapMode: Text.NoWrap
    elide: wrapMode === Text.NoWrap ? Text.ElideRight : Text.ElideNone
    Accessible.role: Accessible.StaticText
    Accessible.name: text
}
