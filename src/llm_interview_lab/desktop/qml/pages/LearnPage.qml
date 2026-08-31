import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    objectName: "learnPage"

    required property var app
    required property var palette
    property var theme: null
    property string layoutMode: "standard"
    property string section: "courses"
    property string filterMode: "recommended"
    property string query: ""
    property var filteredProblems: []
    property var selectedProblem: ({})
    property bool compactDetail: false
    property bool compactKnowledgeDetail: false
    readonly property bool compactLayout: layoutMode === "compact" || width < 1040
    readonly property bool drillDownLayout: layoutMode !== "wide" || width < 1400

    function statusText(value) {
        return ({not_started: "待开始", in_progress: "进行中", implemented: "已实现",
                 reviewed: "已审查", retained_d2: "已完成 D+2", retained_d7: "已完成 D+7",
                 mastered: "已掌握"})[value] || value || "待开始"
    }
    function validationText(value) {
        return ({oracle: "已验证", field: "已实测", stable: "稳定",
                 contract: "实验性"})[value] || value || "未验证"
    }
    function searchable(card) {
        var values = [card.problem_id, card.title].concat(card.skills || [], card.keywords || [])
        return values.join(" ").toLowerCase()
    }
    function retentionDueFor(card) {
        var due = (app.dashboard && app.dashboard.due_retention) || []
        for (var i = 0; i < due.length; ++i) {
            if (due[i].problem_id === card.problem_id && due[i].actionable !== false)
                return true
        }
        return false
    }
    function isRunnable(card) {
        return !!card
               && !card.locked
               && card.asset_status !== "planned"
               && card.environment_available !== false
               && card.status !== "mastered"
               && card.validation !== "contract"
    }
    function blockingReason(card) {
        if (!card || !card.problem_id)
            return "请先从左侧选择一道题。"
        if (card.asset_status === "planned")
            return "该节点仍在规划中，当前没有可运行资产。"
        if (card.environment_available === false)
            return card.environment_reason || "当前安装缺少这道题需要的运行环境。"
        if (card.locked)
            return card.blocked_reason || "先完成前置能力后即可解锁。"
        if (card.validation === "contract")
            return "该题仍处于实验性契约阶段，暂不从普通训练入口启动。"
        if (card.status === "mastered")
            return "这道题已经掌握，可在复测到期时再次训练。"
        return ""
    }
    function actionText(card) {
        if (!card || !card.problem_id)
            return "选择题目"
        if (!isRunnable(card))
            return card.validation === "contract" ? "实验性"
                   : card.locked ? "尚未解锁"
                   : card.environment_available === false ? "环境不可用"
                   : card.asset_status === "planned" ? "尚未开放"
                   : card.status === "mastered" ? "已掌握" : "暂不可用"
        return card.status === "in_progress" ? "继续训练" : "开始训练"
    }
    function emptyMessage() {
        if (query.trim().length > 0)
            return "没有匹配“" + query.trim() + "”的题目。试试标题、技能或 Problem ID。"
        if (filterMode === "experimental")
            return "当前没有已登记的实验性题目。"
        if (filterMode === "available")
            return "当前没有可直接开始的题目。可能是前置尚未完成，或运行环境暂不可用。"
        return "当前没有新的推荐题。先完成进行中的任务或到期复测。"
    }
    function refreshList() {
        var source = app.problems || []
        var needle = query.trim().toLowerCase()
        var result = []
        for (var i = 0; i < source.length; ++i) {
            var card = source[i]
            var validation = card.validation || "contract"
            var available = !card.locked
                            && card.asset_status !== "planned"
                            && card.environment_available !== false
                            && card.status !== "mastered"
            var matches = !needle || searchable(card).indexOf(needle) >= 0
            var include = false
            if (filterMode === "recommended")
                include = available
                          && card.recommendable
                          && card.recommended_rank >= 0
                          && ["oracle", "field", "stable"].indexOf(validation) >= 0
            else if (filterMode === "available")
                include = available && ["oracle", "field", "stable"].indexOf(validation) >= 0
            else if (filterMode === "experimental")
                include = validation === "contract"
            if (include && matches)
                result.push(card)
        }
        result.sort(function(a, b) {
            var rank = function(card) {
                if (card.status === "in_progress") return 0
                if (root.retentionDueFor(card)) return 1
                if (card.status === "not_started") return 2
                return 3
            }
            var learningOrder = filterMode === "recommended"
                              ? (a.recommended_rank - b.recommended_rank) : 0
            return rank(a) - rank(b)
                   || learningOrder
                   || String(a.problem_id).localeCompare(String(b.problem_id))
        })
        filteredProblems = result

        var keepSelection = false
        for (var j = 0; j < result.length; ++j) {
            if (result[j].problem_id === selectedProblem.problem_id) {
                selectedProblem = result[j]
                keepSelection = true
                break
            }
        }
        if (!keepSelection) {
            selectedProblem = result.length > 0 ? result[0] : ({})
            compactDetail = false
        }
    }
    function chooseProblem(card) {
        selectedProblem = card || ({})
        if (drillDownLayout)
            compactDetail = true
    }
    function selectSection(value) {
        section = value
        compactDetail = false
        compactKnowledgeDetail = false
        if (value === "knowledge" && !app.knowledgeLoaded)
            app.loadKnowledge()
    }
    function listText(value) {
        if (!value)
            return ""
        return typeof value === "string" ? value : value.join("\n• ")
    }
    function kindText(value) {
        return ({eight_stock: "原理 / 推导", experience_pattern: "面试模式",
                 coding_prompt: "手撕题"})[value] || value || "知识卡"
    }
    function sourceText(value) {
        if (!value || !value.length)
            return "暂无来源记录"
        var lines = []
        for (var i = 0; i < value.length; i++) {
            var source = value[i]
            var label = (source.title || source.id || "未命名来源")
                       + (source.publisher ? " · " + source.publisher : "")
            var locator = source.url || source.locator || ""
            lines.push(label + (locator ? "\n" + locator : ""))
        }
        return lines.join("\n")
    }

    Component.onCompleted: refreshList()
    Connections {
        target: app
        function onStateChanged() { root.refreshList() }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.theme ? root.theme.pagePadding : 24
        spacing: root.theme ? root.theme.space3 : 12

        RowLayout {
            Layout.fillWidth: true
            spacing: root.theme ? root.theme.space4 : 16

            SectionHeader {
                objectName: "learnRouteContext"
                theme: root.theme
                Layout.fillWidth: true
                title: root.section === "courses" ? "按能力前置逐步训练" : "面试知识库"
                description: root.section === "courses"
                             ? "优先展示当前真实可做、且已完成验证的训练内容。"
                             : "用结构化知识卡准备口述、追问与项目深挖。"
            }

            LabSurface {
                theme: root.theme
                level: "sunken"
                outlined: false
                padding: 3
                Layout.preferredWidth: 230
                Layout.preferredHeight: root.theme ? root.theme.controlHeight + 6 : 46

                RowLayout {
                    anchors.fill: parent
                    spacing: 2
                    LabButton {
                        theme: root.theme
                        Layout.fillWidth: true
                        compact: true
                        variant: root.section === "courses" ? "primary" : "ghost"
                        text: "课程"
                        onClicked: root.selectSection("courses")
                    }
                    LabButton {
                        objectName: "knowledgeBrowserButton"
                        theme: root.theme
                        Layout.fillWidth: true
                        compact: true
                        variant: root.section === "knowledge" ? "primary" : "ghost"
                        text: "知识库"
                        onClicked: root.selectSection("knowledge")
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.section === "courses" ? 0 : 1

            ColumnLayout {
                spacing: root.theme ? root.theme.space3 : 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: root.theme ? root.theme.space3 : 12
                    LabComboBox {
                        id: filter
                        objectName: "learnFilter"
                        theme: root.theme
                        accessibleLabel: "课程筛选"
                        Layout.preferredWidth: root.compactLayout ? 150 : 172
                        model: ["推荐", "全部可做", "实验性"]
                        onCurrentIndexChanged: {
                            root.filterMode = ["recommended", "available", "experimental"][currentIndex]
                            root.refreshList()
                        }
                    }
                    LabText {
                        id: resultSummary
                        objectName: "learnResultSummary"
                        theme: root.theme
                        Layout.fillWidth: true
                        text: ({recommended: "推荐", available: "全部可做", experimental: "实验性"}[root.filterMode]
                               || "当前") + " · " + root.filteredProblems.length + " 道"
                        tone: "muted"
                        horizontalAlignment: Text.AlignRight
                    }
                }
                LabTextField {
                    id: search
                    objectName: "learnSearch"
                    theme: root.theme
                    accessibleLabel: placeholderText
                    Layout.fillWidth: true
                    placeholderText: "搜索标题、技能、关键词或 Problem ID"
                    onTextChanged: {
                        root.query = text
                        root.refreshList()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: root.theme ? root.theme.space3 : 12

                    LabSurface {
                        readonly property real compactPanelHeight: problemList.count > 0
                            ? Math.min(Math.max(problemList.contentHeight + 16, 112), 520)
                            : 260
                        theme: root.theme
                        level: "base"
                        padding: 0
                        implicitHeight: 1
                        Layout.preferredWidth: root.drillDownLayout ? -1 : 360
                        Layout.maximumWidth: root.drillDownLayout ? 820 : 16777215
                        Layout.preferredHeight: root.drillDownLayout ? compactPanelHeight : -1
                        Layout.maximumHeight: root.drillDownLayout ? compactPanelHeight : 16777215
                        Layout.alignment: root.drillDownLayout
                                          ? Qt.AlignHCenter | Qt.AlignTop : Qt.AlignLeft
                        Layout.fillWidth: root.drillDownLayout
                        Layout.fillHeight: !root.drillDownLayout
                        visible: !root.drillDownLayout || !root.compactDetail

                        EmptyState {
                            objectName: "learnEmptyState"
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 48, 420)
                            visible: problemList.count === 0
                            theme: root.theme
                            title: "这里暂时没有可展示的题目"
                            description: root.emptyMessage()
                            symbol: "○"
                        }

                        ListView {
                            id: problemList
                            objectName: "learnProblemList"
                            anchors.fill: parent
                            anchors.margins: root.theme ? root.theme.space2 : 8
                            visible: count > 0
                            clip: true
                            spacing: 4
                            model: root.filteredProblems
                            ScrollBar.vertical: LabScrollBar { theme: root.theme }

                            delegate: Rectangle {
                                id: problemRow
                                required property var modelData
                                objectName: "learnProblemRow-" + modelData.problem_id
                                width: problemList.width
                                height: Math.max(88, root.theme ? root.theme.scaledPx(88) : 88)
                                radius: root.theme ? root.theme.radiusMedium : 9
                                color: selected || hoverHandler.hovered
                                       ? (root.theme ? root.theme.surfaceHover : root.palette.surfaceAlt)
                                       : "transparent"
                                border.color: selected
                                              ? (root.theme ? root.theme.focusRing : root.palette.accent)
                                              : "transparent"
                                border.width: selected ? 1 : 0
                                activeFocusOnTab: true
                                readonly property bool selected: root.selectedProblem.problem_id === modelData.problem_id
                                Accessible.role: Accessible.ListItem
                                Accessible.name: modelData.title
                                Accessible.selected: selected

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: root.theme ? root.theme.space3 : 12
                                    spacing: 3
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        text: modelData.title
                                        strong: true
                                        wrapMode: Text.Wrap
                                        maximumLineCount: 2
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        text: modelData.skills && modelData.skills.length
                                              ? modelData.skills.slice(0, 3).join(" · ") : "基础能力"
                                        tone: "muted"
                                        variant: "caption"
                                        elide: Text.ElideRight
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        StatusPill {
                                            theme: root.theme
                                            compact: true
                                            text: root.statusText(modelData.status)
                                            tone: modelData.status === "mastered"
                                                  ? root.palette.success : root.palette.accent
                                        }
                                        LabText {
                                            theme: root.theme
                                            Layout.fillWidth: true
                                            text: root.validationText(modelData.validation)
                                                  + (root.drillDownLayout ? " · 查看详情 →" : "")
                                            tone: root.drillDownLayout ? "accent"
                                                  : modelData.validation === "contract" ? "warning" : "success"
                                            variant: "caption"
                                            horizontalAlignment: Text.AlignRight
                                        }
                                    }
                                }
                                HoverHandler { id: hoverHandler; cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: root.chooseProblem(problemRow.modelData) }
                                Keys.onReturnPressed: root.chooseProblem(modelData)
                                Keys.onSpacePressed: root.chooseProblem(modelData)
                            }
                        }
                    }

                    LabSurface {
                        theme: root.theme
                        level: "raised"
                        Layout.fillWidth: true
                        Layout.maximumWidth: root.drillDownLayout ? 920 : 16777215
                        Layout.alignment: root.drillDownLayout ? Qt.AlignHCenter : Qt.AlignLeft
                        Layout.fillHeight: true
                        padding: root.theme ? root.theme.space5 : 20
                        visible: !root.drillDownLayout || root.compactDetail

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: root.theme ? root.theme.space3 : 12

                            LabButton {
                                objectName: "learnCourseBackButton"
                                theme: root.theme
                                visible: root.drillDownLayout
                                compact: true
                                variant: "ghost"
                                text: "← 返回课程列表"
                                onClicked: root.compactDetail = false
                            }

                            EmptyState {
                                Layout.fillWidth: true
                                Layout.maximumWidth: 420
                                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                                visible: !root.selectedProblem.problem_id
                                theme: root.theme
                                title: "选择一道题查看详情"
                                description: "选择不会创建 Attempt；只有点击“开始训练”才会进入练习。"
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                visible: !!root.selectedProblem.problem_id
                                spacing: root.theme ? root.theme.space3 : 12

                                LabText {
                                    theme: root.theme
                                    Layout.fillWidth: true
                                    text: root.selectedProblem.title || ""
                                    variant: "section"
                                    strong: true
                                    wrapMode: Text.Wrap
                                }
                                LabText {
                                    theme: root.theme
                                    Layout.fillWidth: true
                                    text: root.selectedProblem.skills && root.selectedProblem.skills.length
                                          ? root.selectedProblem.skills.join(" · ") : "基础能力"
                                    tone: "muted"
                                    wrapMode: Text.Wrap
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 7
                                    StatusPill {
                                        theme: root.theme
                                        text: root.statusText(root.selectedProblem.status)
                                        tone: root.selectedProblem.status === "mastered"
                                              ? root.palette.success : root.palette.accent
                                    }
                                    StatusPill {
                                        theme: root.theme
                                        text: root.validationText(root.selectedProblem.validation)
                                        tone: root.selectedProblem.validation === "contract"
                                              ? root.palette.warning : root.palette.success
                                    }
                                    StatusPill {
                                        theme: root.theme
                                        text: root.selectedProblem.environment || "当前可运行"
                                        tone: root.selectedProblem.environment_available === false
                                              ? root.palette.warning : root.palette.muted
                                    }
                                }
                                InlineNotice {
                                    theme: root.theme
                                    Layout.fillWidth: true
                                    visible: root.blockingReason(root.selectedProblem).length > 0
                                    tone: root.selectedProblem.environment_available === false ? "warning" : "info"
                                    title: root.isRunnable(root.selectedProblem) ? "" : "当前暂不能开始"
                                    message: root.blockingReason(root.selectedProblem)
                                }
                                LabDivider { Layout.fillWidth: true; theme: root.theme }
                                LabText {
                                    theme: root.theme
                                    Layout.fillWidth: true
                                    text: root.selectedProblem.prerequisites && root.selectedProblem.prerequisites.length
                                          ? "前置能力：" + root.selectedProblem.prerequisites.join(" · ")
                                          : "前置能力：无硬前置"
                                    tone: "muted"
                                    wrapMode: Text.Wrap
                                }
                                LabButton {
                                    objectName: "learnOpenProblemButton"
                                    theme: root.theme
                                    Layout.alignment: Qt.AlignLeft
                                    variant: "primary"
                                    text: root.actionText(root.selectedProblem)
                                    enabled: root.isRunnable(root.selectedProblem)
                                    onClicked: root.app.openProblem(root.selectedProblem.problem_id)
                                }
                                Item { Layout.fillHeight: true }
                                LabText {
                                    theme: root.theme
                                    Layout.fillWidth: true
                                    text: "技术详情 · " + (root.selectedProblem.problem_id || "")
                                          + " · 资产"
                                          + (root.selectedProblem.asset_status === "ready" ? "可用" : "未开放")
                                    tone: "subtle"
                                    variant: "caption"
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                id: knowledgeBrowser
                objectName: "knowledgeBrowser"
                spacing: root.theme ? root.theme.space3 : 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: root.theme ? root.theme.space3 : 12
                    LabTextField {
                        id: knowledgeQuery
                        objectName: "knowledgeSearch"
                        theme: root.theme
                        accessibleLabel: placeholderText
                        Layout.fillWidth: true
                        placeholderText: "搜索主题、概念或关键词，例如 GRPO reward / RoPE / KV cache"
                        onTextChanged: {
                            root.compactKnowledgeDetail = false
                            knowledgeSearchTimer.restart()
                        }
                    }
                    LabButton {
                        theme: root.theme
                        compact: true
                        variant: "ghost"
                        text: "清除"
                        enabled: knowledgeQuery.text.length > 0
                        onClicked: knowledgeQuery.clear()
                    }
                    LabButton {
                        objectName: "knowledgeRetryButton"
                        theme: root.theme
                        compact: true
                        variant: "secondary"
                        text: "刷新"
                        onClicked: {
                            root.compactKnowledgeDetail = false
                            app.loadKnowledge()
                        }
                    }
                }
                Timer {
                    id: knowledgeSearchTimer
                    interval: 180
                    repeat: false
                    onTriggered: app.searchKnowledge(knowledgeQuery.text)
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: root.theme ? root.theme.space3 : 12

                    LabSurface {
                        theme: root.theme
                        padding: 0
                        implicitHeight: 1
                        Layout.preferredWidth: root.drillDownLayout ? -1 : 360
                        Layout.maximumWidth: root.drillDownLayout ? 820 : 16777215
                        Layout.alignment: root.drillDownLayout ? Qt.AlignHCenter : Qt.AlignLeft
                        Layout.fillWidth: root.drillDownLayout
                        Layout.fillHeight: true
                        visible: !root.drillDownLayout || !root.compactKnowledgeDetail

                        EmptyState {
                            objectName: "knowledgeEmptyState"
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 48, 400)
                            visible: !app.knowledgeLoaded || knowledgeList.count === 0
                            theme: root.theme
                            title: app.knowledgeLoaded ? "没有匹配的知识卡" : "知识库尚未加载"
                            description: app.knowledgeLoaded
                                         ? "换一个关键词，或清除搜索条件。"
                                         : "点击“刷新”重试；课程训练仍可正常使用。"
                            symbol: "○"
                        }
                        ListView {
                            id: knowledgeList
                            objectName: "knowledgeCardList"
                            anchors.fill: parent
                            anchors.margins: root.theme ? root.theme.space2 : 8
                            clip: true
                            spacing: 4
                            model: app.knowledgeCards
                            ScrollBar.vertical: LabScrollBar { theme: root.theme }
                            delegate: Rectangle {
                                id: knowledgeRow
                                required property var modelData
                                objectName: "knowledgeRow-" + modelData.id
                                width: knowledgeList.width
                                height: Math.max(80, root.theme ? root.theme.scaledPx(80) : 80)
                                radius: root.theme ? root.theme.radiusMedium : 9
                                color: hoverHandlerKnowledge.hovered
                                       ? (root.theme ? root.theme.surfaceHover : root.palette.surfaceAlt)
                                       : "transparent"
                                activeFocusOnTab: true
                                Accessible.role: Accessible.ListItem
                                Accessible.name: modelData.title || "未命名卡片"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: root.theme ? root.theme.space3 : 12
                                    spacing: 3
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        text: modelData.title || "未命名卡片"
                                        strong: true
                                        elide: Text.ElideRight
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        text: root.kindText(modelData.kind)
                                              + (modelData.domain ? " · " + modelData.domain : "")
                                        tone: "muted"
                                        variant: "caption"
                                        elide: Text.ElideRight
                                    }
                                }
                                HoverHandler { id: hoverHandlerKnowledge; cursorShape: Qt.PointingHandCursor }
                                TapHandler {
                                    onTapped: {
                                        app.openKnowledgeCard(knowledgeRow.modelData.id)
                                        if (root.drillDownLayout)
                                            root.compactKnowledgeDetail = true
                                    }
                                }
                                Keys.onReturnPressed: {
                                    app.openKnowledgeCard(modelData.id)
                                    if (root.drillDownLayout)
                                        root.compactKnowledgeDetail = true
                                }
                            }
                        }
                    }

                    LabSurface {
                        theme: root.theme
                        level: "raised"
                        Layout.fillWidth: true
                        Layout.maximumWidth: root.drillDownLayout ? 920 : 16777215
                        Layout.alignment: root.drillDownLayout ? Qt.AlignHCenter : Qt.AlignLeft
                        Layout.fillHeight: true
                        visible: !root.drillDownLayout || root.compactKnowledgeDetail

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: root.theme ? root.theme.space3 : 12
                            LabButton {
                                objectName: "knowledgeBackButton"
                                theme: root.theme
                                visible: root.drillDownLayout
                                compact: true
                                variant: "ghost"
                                text: "← 返回知识卡列表"
                                onClicked: root.compactKnowledgeDetail = false
                            }
                            EmptyState {
                                Layout.fillWidth: true
                                Layout.maximumWidth: 420
                                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                                visible: !app.knowledgeDetail || !app.knowledgeDetail.title
                                theme: root.theme
                                title: "选择一张知识卡"
                                description: "查看 60 秒回答、追问、常见薄弱点和来源。"
                            }
                            ScrollView {
                                id: knowledgeDetailScroll
                                objectName: "knowledgeDetailScroll"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                visible: !!app.knowledgeDetail && !!app.knowledgeDetail.title
                                clip: true
                                contentWidth: availableWidth
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                ColumnLayout {
                                    id: knowledgeDetailContent
                                    objectName: "knowledgeDetailContent"
                                    width: knowledgeDetailScroll.availableWidth
                                    spacing: root.theme ? root.theme.space3 : 12
                                    property var detail: app.knowledgeDetail || ({})
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        text: parent.detail.title || ""
                                        variant: "section"
                                        strong: true
                                        wrapMode: Text.Wrap
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        text: (parent.detail.id || "") + " · "
                                              + root.kindText(parent.detail.kind)
                                              + (parent.detail.priority ? " · " + parent.detail.priority : "")
                                        tone: "accent"
                                        variant: "caption"
                                        wrapMode: Text.Wrap
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        visible: !!parent.detail.one_liner
                                        text: "60 秒回答\n" + (parent.detail.one_liner || "")
                                        wrapMode: Text.Wrap
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        visible: !!parent.detail.prompt
                                        text: "面试提示\n" + (parent.detail.prompt || "")
                                        wrapMode: Text.Wrap
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        visible: (parent.detail.core_answer || []).length > 0
                                        text: "核心回答\n• " + root.listText(parent.detail.core_answer)
                                        wrapMode: Text.Wrap
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        visible: (parent.detail.follow_ups || []).length > 0
                                        text: "高频追问\n• " + root.listText(parent.detail.follow_ups)
                                        wrapMode: Text.Wrap
                                    }
                                    LabText {
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        visible: (parent.detail.pitfalls || []).length > 0
                                        text: "常见薄弱点\n• " + root.listText(parent.detail.pitfalls)
                                        tone: "warning"
                                        wrapMode: Text.Wrap
                                    }
                                    LabDivider { Layout.fillWidth: true; theme: root.theme }
                                    LabText {
                                        objectName: "knowledgeSourceText"
                                        theme: root.theme
                                        Layout.fillWidth: true
                                        visible: (parent.detail.source_records || []).length > 0
                                        text: "来源（链接与事实性转述）\n" + root.sourceText(parent.detail.source_records)
                                        tone: "muted"
                                        variant: "caption"
                                        wrapMode: Text.WrapAnywhere
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
