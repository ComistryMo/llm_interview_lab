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

    // Quiet Forge uses warm neutral surfaces and one restrained blue accent.
    // The aliases below deliberately describe purpose rather than a page.
    readonly property color canvas: darkMode ? "#0d0e10" : "#f4f3ef"
    readonly property color chrome: darkMode ? "#111316" : "#eceae4"
    readonly property color surface: darkMode ? "#16181c" : "#fcfbf8"
    readonly property color surfaceRaised: darkMode ? "#1c1f24" : "#ffffff"
    readonly property color surfaceSunken: darkMode ? "#101215" : "#eeece6"
    readonly property color surfaceHover: darkMode ? "#20242a" : "#e9e7e1"
    readonly property color surfaceAlt: surfaceSunken
    readonly property color elevated: surfaceRaised

    readonly property color textStrong: darkMode ? "#f3f2ee" : "#202227"
    readonly property color text: darkMode ? "#a8adb6" : "#646870"
    readonly property color muted: darkMode ? "#a8adb6" : "#646870"
    readonly property color subtle: darkMode ? "#838a95" : "#6f737b"
    // QML reserves property names shaped like onSignal. Use explicit
    // foreground names rather than the CSS-style onAccent/onDanger spelling.
    readonly property color accentForeground: darkMode ? "#11131a" : "#ffffff"
    readonly property color dangerForeground: darkMode ? "#11131a" : "#ffffff"

    readonly property color borderSubtle: darkMode ? "#24282e" : "#e3e0d8"
    readonly property color borderDefault: darkMode ? "#30353d" : "#d2cfc6"
    readonly property color borderStrong: darkMode ? "#454b55" : "#b7b3aa"
    readonly property color border: borderDefault
    readonly property color controlBorder: darkMode ? "#686e78" : "#8b877e"
    readonly property color focusRing: darkMode ? "#92a6ff" : "#5263d8"

    readonly property color accent: darkMode ? "#92a6ff" : "#5263d8"
    readonly property color accentHover: darkMode ? "#a8b8ff" : "#4656c2"
    readonly property color accentPressed: darkMode ? "#748bee" : "#3948aa"
    readonly property color accentSoft: darkMode ? "#202947" : "#e7e9fa"
    readonly property color toastBackground: darkMode ? "#eceae4" : "#1c1f24"
    readonly property color toastForeground: darkMode ? "#202227" : "#f3f2ee"
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
    readonly property int radiusMedium: 9
    readonly property int radiusLarge: 12
    readonly property int radiusRound: 999

    readonly property int fontCaption: scaledPx(12)
    readonly property int fontBody: scaledPx(14)
    readonly property int fontBodyLarge: scaledPx(15)
    readonly property int fontSection: scaledPx(18)
    readonly property int fontTitle: scaledPx(26)
    readonly property int controlHeight: 40
    readonly property int controlHeightCompact: 34
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
