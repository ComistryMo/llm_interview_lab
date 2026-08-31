import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Phase 0 presentation-only prototype (synthetic: true). It does not import
// the production controller, read a Profile, or invoke a grader.
ApplicationWindow {
    id: window
    visible: true
    width: 1280
    height: 800
    minimumWidth: 960
    minimumHeight: 620
    title: "LLM Interview Lab · Coding Workbench Prototype"
    color: theme.canvas
    font.family: Qt.platform.os === "windows" ? "Microsoft YaHei UI"
                 : Qt.platform.os === "osx" ? "PingFang SC" : "Noto Sans CJK SC"
    font.pixelSize: 13

    property string prototypeDirection: "graphite-blue"
    property bool prototypeDark: false
    property int selectedCase: 0
    property string runState: "尚未运行"

    QtObject {
        id: theme
        readonly property bool graphite: window.prototypeDirection === "graphite-blue"
        readonly property bool violet: window.prototypeDirection === "obsidian-violet"
        readonly property bool warm: window.prototypeDirection === "warm-frost"
        readonly property color canvas: window.prototypeDark
            ? (graphite ? "#0e1116" : violet ? "#111016" : "#171614")
            : (graphite ? "#f4f6fa" : violet ? "#f5f3f8" : "#f5f2eb")
        readonly property color chrome: window.prototypeDark
            ? (graphite ? "#151a22" : violet ? "#191620" : "#24211d")
            : (graphite ? "#e9edf4" : violet ? "#ece8f1" : "#ebe6dc")
        readonly property color surface: window.prototypeDark
            ? (graphite ? "#1a202a" : violet ? "#211d2a" : "#2c2823")
            : "#fffefb"
        readonly property color raised: window.prototypeDark
            ? (graphite ? "#222a36" : violet ? "#2b2537" : "#373129")
            : (graphite ? "#f9fbff" : violet ? "#fbf9fd" : "#fffefa")
        readonly property color codeSurface: window.prototypeDark
            ? (graphite ? "#10151d" : violet ? "#15121b" : "#1d1a17")
            : (graphite ? "#f1f4f8" : violet ? "#f1eef5" : "#f1eee7")
        readonly property color text: window.prototypeDark ? "#edf1f7" : "#20252d"
        readonly property color muted: window.prototypeDark ? "#aab3c2" : "#68717e"
        readonly property color faint: window.prototypeDark ? "#727c8e" : "#8b94a1"
        readonly property color line: window.prototypeDark
            ? (graphite ? "#303947" : violet ? "#393143" : "#443e36")
            : (graphite ? "#dfe4ec" : violet ? "#e3dfe8" : "#ded8cd")
        readonly property color accent: graphite ? "#6f8cff" : violet ? "#9a83e8" : "#b07a46"
        readonly property color accentSoft: window.prototypeDark
            ? (graphite ? "#27365f" : violet ? "#392d5c" : "#4a3628")
            : (graphite ? "#e8edff" : violet ? "#eee9ff" : "#f4e7d6")
        readonly property color success: window.prototypeDark ? "#8fd1b0" : "#277653"
        readonly property color warning: window.prototypeDark ? "#e8bf83" : "#97631e"
        readonly property color codeText: window.prototypeDark ? "#e5eaf3" : "#27313d"
        readonly property color codeMuted: window.prototypeDark ? "#768398" : "#87919f"
    }

    function directionLabel() {
        return theme.violet ? "Obsidian Violet" : theme.warm ? "Warm Frost" : "Graphite Blue"
    }
    function selectCase(value) {
        selectedCase = value
        runState = "尚未运行"
    }

    Rectangle {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 58
        color: theme.chrome
        border.color: theme.line
        border.width: 1
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            spacing: 14
            Rectangle {
                Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 8
                color: theme.accent
                Text { anchors.centerIn: parent; text: "⌁"; color: "#ffffff"; font.pixelSize: 20; font.bold: true }
            }
            ColumnLayout {
                Layout.preferredWidth: 168; spacing: 0
                Text { text: "LLM Interview Lab"; color: theme.text; font.pixelSize: 14; font.bold: true }
                Text { text: "Quiet Forge · 原型"; color: theme.muted; font.pixelSize: 11 }
            }
            Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 22; color: theme.line }
            Text {
                Layout.fillWidth: true
                text: "训练  /  Tensor & Stable Loss  /  LOSS-014"
                color: theme.muted; font.pixelSize: 13; elide: Text.ElideRight
            }
            Rectangle {
                Layout.preferredWidth: 126; Layout.preferredHeight: 28; radius: 14
                color: theme.accentSoft; border.color: theme.accent
                Row {
                    anchors.centerIn: parent; spacing: 7
                    Rectangle { width: 7; height: 7; radius: 4; color: theme.success; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "本地模式"; color: theme.text; font.pixelSize: 11; font.bold: true }
                }
            }
            Text { text: directionLabel(); color: theme.faint; font.pixelSize: 11 }
            Rectangle {
                Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 14
                color: theme.raised; border.color: theme.line
                Text { anchors.centerIn: parent; text: "练"; color: theme.text; font.pixelSize: 11; font.bold: true }
            }
        }
    }

    RowLayout {
        anchors.top: topBar.bottom; anchors.left: parent.left
        anchors.right: parent.right; anchors.bottom: parent.bottom
        spacing: 0
        Rectangle {
            id: problemPane
            Layout.preferredWidth: 350; Layout.fillHeight: true
            color: theme.surface; border.color: theme.line; border.width: 1
            Flickable {
                anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 18
                anchors.topMargin: 22; anchors.bottomMargin: 18
                contentWidth: width; contentHeight: details.implicitHeight; clip: true
                Column {
                    id: details; width: parent.width; spacing: 15
                    Row {
                        spacing: 8
                        Text { text: "LOSS-014"; color: theme.accent; font.pixelSize: 11; font.bold: true }
                        Rectangle { width: 58; height: 21; radius: 10; color: theme.accentSoft; Text { anchors.centerIn: parent; text: "中等"; color: theme.text; font.pixelSize: 10 } }
                        Rectangle { width: 72; height: 21; radius: 10; color: theme.raised; Text { anchors.centerIn: parent; text: "25 分钟"; color: theme.muted; font.pixelSize: 10 } }
                    }
                    Text {
                        width: parent.width; text: "实现稳定的\nMasked Cross Entropy"
                        color: theme.text; font.pixelSize: 24; font.bold: true; lineHeight: 1.1
                    }
                    Text {
                        width: parent.width
                        text: "为一批变长序列计算稳定的分类损失，并保留可解释的有效 Token 证据。"
                        color: theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; lineHeight: 1.25
                    }
                    Rectangle { width: parent.width; height: 1; color: theme.line }
                    Text { text: "输入参数"; color: theme.text; font.pixelSize: 12; font.bold: true }
                    Column {
                        width: parent.width; spacing: 7
                        Repeater {
                            model: ["logits  [B, T, C]", "targets [B, T]", "mask    [B, T]"]
                            delegate: Rectangle {
                                width: details.width; height: 28; radius: 6
                                color: theme.raised; border.color: theme.line
                                Text {
                                    anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                                    text: modelData; color: theme.codeText; font.family: "Cascadia Mono"; font.pixelSize: 11
                                }
                            }
                        }
                    }
                    Text { text: "约束"; color: theme.text; font.pixelSize: 12; font.bold: true }
                    Column {
                        width: parent.width; spacing: 5
                        Repeater {
                            model: ["不调用框架 CrossEntropyLoss", "忽略 mask 的位置不计入平均", "极端 logits 仍需返回有限值"]
                            delegate: Row {
                                width: details.width; spacing: 7
                                Text { text: "·"; color: theme.accent; font.pixelSize: 14 }
                                Text { width: details.width - 18; text: modelData; color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
                            }
                        }
                    }
                    Text { text: "示例"; color: theme.text; font.pixelSize: 12; font.bold: true }
                    Rectangle {
                        width: parent.width; height: 78; radius: 8
                        color: theme.codeSurface; border.color: theme.line
                        Column {
                            anchors.fill: parent; anchors.margins: 11; spacing: 5
                            Text { text: "mask = [[1, 1, 0], [1, 1, 1]]"; color: theme.codeText; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                            Text { text: "loss 只聚合 5 个有效位置"; color: theme.codeMuted; font.pixelSize: 11 }
                        }
                    }
                    Rectangle { width: parent.width; height: 1; color: theme.line }
                    Row {
                        width: parent.width
                        Text { text: "提示"; color: theme.text; font.pixelSize: 12; font.bold: true }
                        Item { width: parent.width - 110; height: 1 }
                        Text { text: "H1  H2  H3"; color: theme.accent; font.pixelSize: 11; font.bold: true }
                    }
                    Text { width: parent.width; text: "先写出 log-sum-exp 的数值稳定形式，再决定 mask 的归一化分母。"; color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    Text { text: "相关题"; color: theme.text; font.pixelSize: 12; font.bold: true }
                    Row {
                        spacing: 8
                        Rectangle { width: 104; height: 26; radius: 6; color: theme.raised; Text { anchors.centerIn: parent; text: "LOSS-007 Softmax"; color: theme.muted; font.pixelSize: 10 } }
                        Rectangle { width: 96; height: 26; radius: 6; color: theme.raised; Text { anchors.centerIn: parent; text: "TNS-010 Mask"; color: theme.muted; font.pixelSize: 10 } }
                    }
                }
            }
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 54
                color: theme.chrome; border.color: theme.line
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 18; spacing: 10
                    Text { text: "submission.py"; color: theme.text; font.pixelSize: 13; font.bold: true }
                    Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; color: theme.warning }
                    Text { text: "未保存"; color: theme.muted; font.pixelSize: 11 }
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        Layout.preferredWidth: 94; Layout.preferredHeight: 32; radius: 7; color: theme.accent
                        Text { anchors.centerIn: parent; text: "运行样例"; color: "#ffffff"; font.pixelSize: 12; font.bold: true }
                        MouseArea { anchors.fill: parent; onClicked: window.runState = "已排队" }
                    }
                    Rectangle {
                        Layout.preferredWidth: 94; Layout.preferredHeight: 32; radius: 7; color: "transparent"; border.color: theme.line
                        Text { anchors.centerIn: parent; text: "正式验证"; color: theme.text; font.pixelSize: 12; font.bold: true }
                    }
                    Rectangle {
                        Layout.preferredWidth: 90; Layout.preferredHeight: 32; radius: 7; color: theme.raised; border.color: theme.line
                        Text { anchors.centerIn: parent; text: "AI 解析"; color: theme.muted; font.pixelSize: 12 }
                    }
                    Text { text: "⌘S"; color: theme.faint; font.pixelSize: 11 }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                color: theme.codeSurface; border.color: theme.accent; border.width: 2
                ColumnLayout {
                    anchors.fill: parent; spacing: 0
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 34
                        color: theme.chrome; border.color: theme.line
                        Text { anchors.left: parent.left; anchors.leftMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: "Python  ·  代码编辑器"; color: theme.muted; font.pixelSize: 11 }
                        Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: "revision  —"; color: theme.faint; font.pixelSize: 10; font.family: "Cascadia Mono" }
                    }
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                        Rectangle {
                            Layout.preferredWidth: 48; Layout.fillHeight: true; color: theme.codeSurface
                            Column {
                                anchors.top: parent.top; anchors.topMargin: 17; anchors.right: parent.right; anchors.rightMargin: 12; spacing: 6
                                Repeater { model: 13; delegate: Text { text: String(index + 1).padStart(2, "0"); color: index === 5 ? theme.accent : theme.codeMuted; font.family: "Cascadia Mono"; font.pixelSize: 12 } }
                            }
                        }
                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: theme.line }
                        Flickable {
                            Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: code.implicitWidth + 26; contentHeight: code.implicitHeight + 30; clip: true
                            Text {
                                id: code; x: 20; y: 16; textFormat: Text.PlainText
                                text: "def masked_cross_entropy(logits, targets, mask):\n    # logits: [B, T, C], targets/mask: [B, T]\n    shifted = logits - logits.amax(dim=-1, keepdim=True)\n    log_norm = shifted - shifted.exp().sum(dim=-1, keepdim=True).log()\n    token_logp = log_norm.gather(-1, targets.unsqueeze(-1)).squeeze(-1)\n    valid = mask.to(dtype=token_logp.dtype)\n    denom = valid.sum()\n    if denom.item() == 0:\n        raise ValueError(\"mask must contain a valid token\")\n    return -(token_logp * valid).sum() / denom"
                                color: theme.codeText; font.family: "Cascadia Mono"; font.pixelSize: 13; lineHeight: 1.32; wrapMode: Text.NoWrap
                            }
                        }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 232
                color: theme.surface; border.color: theme.line
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "测试用例"; color: theme.text; font.pixelSize: 13; font.bold: true }
                        Text { text: "公开样例 · 不形成正式掌握证据"; color: theme.faint; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                        Text { text: runState; color: theme.muted; font.pixelSize: 11 }
                    }
                    Row {
                        spacing: 8
                        Repeater {
                            model: ["Case 01", "Case 02", "边界：全 Padding"]
                            delegate: Rectangle {
                                width: index === 2 ? 132 : 76; height: 28; radius: 6
                                color: index === selectedCase ? theme.accentSoft : "transparent"
                                border.color: index === selectedCase ? theme.accent : theme.line
                                Text { anchors.centerIn: parent; text: modelData; color: index === selectedCase ? theme.text : theme.muted; font.pixelSize: 11; font.bold: index === selectedCase }
                                MouseArea { anchors.fill: parent; onClicked: window.selectCase(index) }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; radius: 7
                            color: theme.codeSurface; border.color: theme.line
                            Column {
                                anchors.fill: parent; anchors.margins: 11; spacing: 6
                                Text { text: "输入"; color: theme.faint; font.pixelSize: 10; font.bold: true }
                                Text { text: selectedCase === 2 ? "mask = [[0, 0, 0]]" : selectedCase === 1 ? "B=1, T=2, C=3" : "B=2, T=3, C=4"; color: theme.codeText; font.family: "Cascadia Mono"; font.pixelSize: 11 }
                                Text { text: "targets = [[1, 0, 2], ...]"; color: theme.codeMuted; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; radius: 7
                            color: theme.codeSurface; border.color: theme.line
                            Column {
                                anchors.fill: parent; anchors.margins: 11; spacing: 6
                                Text { text: "期望"; color: theme.faint; font.pixelSize: 10; font.bold: true }
                                Text { text: selectedCase === 2 ? "ValueError" : "有限标量 loss"; color: theme.codeText; font.family: "Cascadia Mono"; font.pixelSize: 11 }
                                Text { text: selectedCase === 2 ? "明确拒绝无有效 Token" : "与参考实现对齐"; color: theme.codeMuted; font.pixelSize: 10 }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; radius: 7
                            color: theme.raised; border.color: theme.line
                            Column {
                                anchors.fill: parent; anchors.margins: 11; spacing: 6
                                Text { text: "执行结果"; color: theme.faint; font.pixelSize: 10; font.bold: true }
                                Text { text: runState; color: theme.warning; font.pixelSize: 12; font.bold: true }
                                Text { text: "修改代码后结果会标记为 Stale"; color: theme.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            }
                        }
                    }
                }
            }
        }
    }
}
