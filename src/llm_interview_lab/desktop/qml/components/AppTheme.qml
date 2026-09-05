import QtQuick

QtObject {
    id: theme

    property bool darkMode: false
    property real fontScale: 1.0
    property real motionScale: 1.0
    property string uiFontFamily: ""
    readonly property string monospaceFontFamily: Qt.platform.os === "windows"
                                                    ? "Cascadia Mono"
                                                    : Qt.platform.os === "osx"
                                                      ? "SF Mono" : "monospace"

    readonly property real resolvedFontScale: Math.max(0.85, Math.min(1.5, fontScale || 1.0))
    readonly property real resolvedMotionScale: Math.max(0.0, Math.min(2.0, motionScale))
    readonly property bool reducedMotion: resolvedMotionScale <= 0.01

    // Conversation-first neutrals. Blue identifies focus and links, not every
    // action or panel; opaque reading surfaces stay separate from chrome.
    // The aliases below deliberately describe purpose rather than a page.
    readonly property color canvas: darkMode ? "#212121" : "#fafaf9"
    readonly property color chrome: darkMode ? "#171717" : "#f0f0ee"
    readonly property color surface: darkMode ? "#262626" : "#ffffff"
    readonly property color surfaceRaised: darkMode ? "#303030" : "#ffffff"
    readonly property color surfaceSunken: darkMode ? "#292929" : "#f3f3f1"
    readonly property color surfaceHover: darkMode ? "#363636" : "#e8e8e5"
    readonly property color surfaceAlt: surfaceSunken
    readonly property color elevated: surfaceRaised

    readonly property color textStrong: darkMode ? "#ececec" : "#202020"
    readonly property color text: darkMode ? "#c7c7c7" : "#484848"
    readonly property color muted: darkMode ? "#ababab" : "#666666"
    readonly property color subtle: darkMode ? "#939393" : "#707070"
    readonly property color primary: darkMode ? "#ececec" : "#202020"
    readonly property color primaryHover: darkMode ? "#d8d8d8" : "#363636"
    readonly property color primaryPressed: darkMode ? "#c4c4c4" : "#484848"
    readonly property color primaryForeground: darkMode ? "#202020" : "#ffffff"
    // QML reserves property names shaped like onSignal. Use explicit
    // foreground names rather than the CSS-style onAccent/onDanger spelling.
    readonly property color accentForeground: darkMode ? "#11131a" : "#ffffff"
    readonly property color dangerForeground: darkMode ? "#11131a" : "#ffffff"

    readonly property color borderSubtle: darkMode ? "#333333" : "#e7e7e3"
    readonly property color borderDefault: darkMode ? "#404040" : "#dcdcd7"
    readonly property color borderStrong: darkMode ? "#9c9c9c" : "#62625f"
    readonly property color border: borderDefault
    readonly property color controlBorder: darkMode ? "#808080" : "#8d8d89"
    readonly property color focusRing: darkMode ? "#8baacf" : "#4a6f98"

    readonly property color accent: darkMode ? "#93b4dc" : "#3c638e"
    readonly property color accentHover: darkMode ? "#afc7e4" : "#315478"
    readonly property color accentPressed: darkMode ? "#7e9fc7" : "#294665"
    readonly property color accentSoft: darkMode ? "#293645" : "#e9eff5"
    readonly property color toastBackground: darkMode ? "#303030" : "#ffffff"
    readonly property color toastForeground: textStrong
    readonly property color success: darkMode ? "#68cda4" : "#18795a"
    readonly property color warning: darkMode ? "#e4b86f" : "#8b5a0a"
    readonly property color danger: darkMode ? "#f0838d" : "#b53f4b"
    readonly property color successSoft: darkMode ? "#173329" : "#e3f1eb"
    readonly property color warningSoft: darkMode ? "#352b18" : "#f5ecdb"
    readonly property color dangerSoft: darkMode ? "#3a2024" : "#f8e6e8"

    readonly property int space1: 4
    readonly property int space2: 8
    readonly property int space3: 12
    readonly property int space4: 16
    readonly property int space5: 20
    readonly property int space6: 24
    readonly property int space8: 32

    readonly property int radiusSmall: 6
    readonly property int radiusMedium: 10
    readonly property int radiusLarge: 12
    readonly property int radiusRound: 999

    readonly property int fontCaption: scaledPx(12)
    readonly property int fontBody: scaledPx(14)
    readonly property int fontBodyLarge: scaledPx(15)
    readonly property int fontSection: scaledPx(18)
    readonly property int fontTitle: scaledPx(26)
    readonly property int controlHeight: Math.max(40, scaledPx(28) + 12)
    readonly property int controlHeightCompact: Math.max(34, scaledPx(24) + 10)
    readonly property int pagePadding: 24

    readonly property int breakpointCompact: 1040
    readonly property int breakpointWide: 1400

    // Existing pages receive this object through window.colors. Keep every
    // historical key until those pages are migrated independently.
    readonly property QtObject legacyPalette: QtObject {
        readonly property color background: theme.canvas
        readonly property color surface: theme.surface
        readonly property color surfaceAlt: theme.surfaceAlt
        readonly property color border: theme.borderDefault
        readonly property color text: theme.textStrong
        readonly property color muted: theme.muted
        readonly property color accent: theme.accent
        readonly property color accentForeground: theme.accentForeground
        readonly property color success: theme.success
        readonly property color warning: theme.warning
        readonly property color danger: theme.danger
    }

    function scaledPx(px) {
        return Math.max(1, Math.round(Number(px) * resolvedFontScale))
    }

    function duration(milliseconds) {
        if (reducedMotion)
            return 0
        return Math.max(1, Math.round(Number(milliseconds) * resolvedMotionScale))
    }

    function withAlpha(value, alpha) {
        return Qt.rgba(value.r, value.g, value.b, Math.max(0, Math.min(1, alpha)))
    }
}
