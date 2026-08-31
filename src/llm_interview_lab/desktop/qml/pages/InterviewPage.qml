import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property var activeQuestion: app.interview.question || null
    property var rubricScores: ({})
    property var aiPreview: ({"parts": [], "estimated_tokens": 0})
    property var planContext: ({"parts": [], "estimated_tokens": 0, "context_sha256": ""})
    property string pendingAIAction: ""
    property string pendingConnection: ""
    property bool answerLocked: !!app.interview.answer_locked
    property string phase: app.interview.phase || (answerLocked ? "assessment" : "answering")
    property var interviewResult: app.interview.result || ({})
    property string answerDraft: ""
    // Keep a confirmation snapshot so an accidental click cannot lock a
    // changing editor value.  The backend remains the source of truth for
    // the actual frozen answer.
    property string pendingLockAnswer: ""
    property string activeQuestionId: activeQuestion ? activeQuestion.question_id : ""
    property string activeQuestionKey: String(app.interview.interview_id || "")
                                  + "::" + String(activeQuestion ? activeQuestion.question_id : "")
    property bool showSessionDetails: false
    property bool syncingQuestionEditors: false
    // A coding round can only be recorded when the visible editor still
    // matches the revision that the local Grader tested. TextArea bindings are
    // intentionally broken after typing, so track edits explicitly.
    property bool codingEditorDirty: false
    property bool interviewCanEdit: app.interview.status === "active"
                                    && app.interview.expired !== true
    // A short viewport needs to keep the answer action visible before asking
    // the learner to scroll.  This is a presentation breakpoint only; it does
    // not change interview timing or answer semantics.
    // The page width excludes the shell/sidebar.  Keep the full interview
    // layout at a normal 1280×800 window; only genuinely narrow/short views
    // switch to the compact editor sizing.
    property bool compactInterviewLayout: width < 900 || height < 600
    property var configuration: ({"available": true, "user_message": "", "missing_rounds": [], "missing_environment": []})
    property string codeFontFamily: Qt.platform.os === "windows" ? "Cascadia Mono"
                                    : Qt.platform.os === "osx" ? "Menlo" : "monospace"
    onActiveQuestionKeyChanged: {
        rubricScores = ({})
        answerDraft = ""
        Qt.callLater(root.syncQuestionEditors)
    }
    onAnswerLockedChanged: Qt.callLater(root.syncQuestionEditors)
    onVisibleChanged: if (visible && leftPanel.setupVisible) Qt.callLater(root.initializeSetup)

    function statusText(value) {
        return ({active: "进行中", paused: "已暂停", ready: "待开始", completed: "已完成", incomplete: "未完成", timed_out: "已超时"})[value] || value || "未知"
    }

    function finishDialogMessage() {
        var completed = Number(app.interview.completed_questions || 0)
        var total = Number(app.interview.total_questions || 0)
        var unanswered = Number(app.interview.unanswered_questions || 0)
        var unscored = Number(app.interview.unscored_questions || 0)
        var codingIncomplete = Number(app.interview.coding_incomplete || 0)
        var complete = total > 0 && completed >= total && unanswered === 0
                       && unscored === 0 && codingIncomplete === 0
        if (app.interview.expired === true || app.interview.status === "timed_out")
            return "计时已到；确认后会按现有证据生成超时/未完成报告。"
        if (complete)
            return "所有固定问题都已有回答和评分证据。确认后会生成完整报告并结束本场。"
        if (app.interview.status === "paused")
            return "本场目前已暂停。确认后会按现有证据留档为未完成报告。"
        return "当前证据尚未覆盖全部问题。确认后会按现有证据留档为未完成报告。"
    }

    // Answer/coding editors stop honoring their initial `text:` binding as
    // soon as the learner types.  Rehydrate them only when the frozen
    // question or lock state changes; ordinary state updates must never erase
    // in-progress typing.
    function syncQuestionEditors() {
        root.syncingQuestionEditors = true
        if (answer)
            answer.text = root.answerLocked ? (app.interview.answer_text || "") : ""
        if (codingEditor)
            codingEditor.text = app.interview.coding_text || ""
        root.codingEditorDirty = false
        root.syncingQuestionEditors = false
    }

    function providerIsReady(itemOrId) {
        // ``ready`` is a controller-owned boolean set only after a successful
        // connection test.  Presentation strings such as “已连接” must not
        // become a second business-status source in QML.
        var item = itemOrId
        if (typeof itemOrId === "string") {
            var values = app.connections || []
            for (var i = 0; i < values.length; ++i) {
                if (String(values[i].connection_id || "") === itemOrId) {
                    item = values[i]
                    break
                }
            }
        }
        if (!item || typeof item !== "object")
            return false
        return item.ready === true
    }

    function seniorityText(value) {
        return ({intern: "实习", new_grad: "校招", mid: "有经验", senior: "高级"})[value] || value || "未设置"
    }

    function difficultyText(value) {
        return ({easy: "基础", medium: "标准", hard: "高压"})[value] || value || "未设置"
    }

    function timerText(seconds) {
        if (seconds === undefined || seconds === null)
            return "未开始"
        if (seconds <= 0)
            return "已到时"
        var minutes = Math.floor(seconds / 60)
        var rest = seconds % 60
        return (minutes < 10 ? "0" : "") + minutes + ":" + (rest < 10 ? "0" : "") + rest
    }

    function previewAI(action, connectionId) {
        root.aiPreview = app.interviewContextPreview(
            answer.text, includeInterviewMaterials.checked
        )
        if ((root.aiPreview.parts || []).length === 0)
            return
        root.pendingAIAction = action
        root.pendingConnection = connectionId || ""
        contextDialog.open()
    }

    function rubricComplete() {
        if (!activeQuestion || !activeQuestion.rubric)
            return false
        var dimensions = Object.keys(activeQuestion.rubric.dimensions || {})
        if (dimensions.length === 0)
            return false
        for (var i = 0; i < dimensions.length; ++i) {
            if (root.rubricScores[dimensions[i]] === undefined)
                return false
        }
        return true
    }

    // QML does not reliably notify bindings when a JavaScript object stored in
    // a `var` property is mutated in place.  Always publish a new score map so
    // the completion check, score labels and action button update immediately
    // after a learner moves one rubric slider.
    function setRubricScore(dimension, value) {
        var next = {}
        var current = root.rubricScores || {}
        for (var key in current) {
            // The map is created locally and only contains rubric dimensions;
            // copying its enumerable keys is sufficient and Qt's QML JS
            // runtime stays compatible with older desktop builds.
            next[key] = current[key]
        }
        next[dimension] = Math.round(value)
        root.rubricScores = next
    }

    function roleIndex(roleId) {
        var values = app.roles || []
        for (var i = 0; i < values.length; ++i) {
            if (values[i].id === roleId)
                return i
        }
        // Never silently substitute the first role when a stored preference
        // is missing or stale.  An explicit empty selection makes the setup
        // action explain what needs fixing instead of starting the wrong
        // interview blueprint.
        return -1
    }

    function seniorityIndex(value) {
        return value === "intern" ? 0 : value === "mid" ? 2 : 1
    }

    function refreshConfiguration() {
        var roleId = role.currentValue || ""
        if (!roleId) {
            var storedRole = (app.dashboard.role && app.dashboard.role.primary_role) || ""
            root.configuration = ({"available": false,
                                   "user_message": storedRole
                                      ? "档案中的目标岗位已不可用，请重新选择后再开始面试。"
                                      : "请选择一个目标岗位后再开始面试。"})
            return
        }
        if (typeof app.interviewConfiguration === "function")
            root.configuration = app.interviewConfiguration(roleId, seniority.currentValue, difficulty.currentValue)
        else
            root.configuration = ({"available": true, "user_message": "", "missing_rounds": [], "missing_environment": []})
    }

    function initializeSetup() {
        var rolePreference = (app.dashboard.role && app.dashboard.role.primary_role) || ""
        role.currentIndex = root.roleIndex(rolePreference)
        seniority.currentIndex = root.seniorityIndex((app.dashboard.role && app.dashboard.role.seniority) || "new_grad")
        root.refreshConfiguration()
    }

    function configurationMessage() {
        if (root.configuration.available !== false)
            return ""
        var message = root.configuration.user_message || "当前配置暂时无法开始面试。"
        var rounds = root.configuration.missing_rounds || []
        var environment = root.configuration.missing_environment || []
        if (rounds.length > 0) {
            var roundLabels = []
            for (var i = 0; i < rounds.length; ++i)
                roundLabels.push(root.missingRoundLabel(rounds[i]))
            message += "\n缺少环节：" + roundLabels.join("；")
        }
        if (environment.length > 0) {
            var environmentLabels = []
            for (var j = 0; j < environment.length; ++j)
                environmentLabels.push(root.missingEnvironmentLabel(environment[j]))
            message += "\n环境要求：" + environmentLabels.join("；")
        }
        return message
    }

    function nonCodingFallback() {
        if (!root.configuration || !root.configuration.non_coding_fallback)
            return ({"available": false})
        return root.configuration.non_coding_fallback
    }

    function fallbackAvailable() {
        return root.configuration.available === false
               && root.nonCodingFallback().available === true
    }

    function fallbackRoundSummary(items) {
        var values = items || []
        var labels = []
        for (var i = 0; i < values.length; ++i) {
            var item = values[i] || {}
            var label = root.roundTypeText(item.type || item.round || "")
            if (item.duration_minutes !== undefined)
                label += "（" + item.duration_minutes + " 分钟）"
            labels.push(label)
        }
        return labels.length > 0 ? labels.join("、") : "无"
    }

    function fallbackCoveragePercent() {
        return Math.round(Number(root.nonCodingFallback().coverage_weight || 0) * 100)
    }

    function missingRoundLabel(item) {
        if (typeof item === "string")
            return root.roundTypeText(item)
        var label = root.roundTypeText(item.round || item.type || "")
        var reason = ({missing_environment: "当前环境缺少所需依赖",
                       no_strict_candidate: "当前难度没有严格匹配的固定题"})[item.reason]
                     || "当前没有可用的固定题"
        return label + "（" + reason + "）"
    }

    function roundTypeText(value) {
        return ({coding: "代码实现", debugging: "调试分析", product_case: "产品案例",
                 system_design: "系统设计", evaluation_case: "评测案例",
                 project_deep_dive: "项目深挖", behavioral: "行为面试",
                 oral: "口述问答"})[value] || "面试环节"
    }

    function assessmentSourceText(value) {
        return ({self: "自评", human: "人工", ai: "AI", grader: "本地 Grader 客观", peer: "同伴", mentor: "导师"})[value]
               || "未标注"
    }

    function resultAssessmentSources(result) {
        var evidence = result && Array.isArray(result.assessment_evidence)
                       ? result.assessment_evidence : []
        var sources = []
        for (var i = 0; i < evidence.length; ++i) {
            var source = evidence[i].source || ""
            if (source && sources.indexOf(source) < 0)
                sources.push(source)
        }
        return sources
    }

    function resultScoreLabel(result) {
        var sources = root.resultAssessmentSources(result)
        var partial = result && (result.completion_status !== "completed"
                                 || (result.unanswered || []).length > 0
                                 || (result.unscored || []).length > 0)
        if (sources.length === 0)
            return "评分"
        if (partial && sources.length === 1 && sources[0] === "self")
            return "自评（部分证据）"
        if (partial)
            return "部分证据分数"
        if (sources.length === 1 && sources[0] === "self")
            return "自评分数"
        if (sources.length === 1 && sources[0] === "ai")
            return "AI 评估分数"
        if (sources.length === 1 && sources[0] === "human")
            return "人工评估分数"
        if (sources.length === 1 && sources[0] === "grader")
            return "本地 Grader 客观分数"
        if (sources.length > 1)
            return "混合证据分数"
        return root.assessmentSourceText(sources[0]) + "评估分数"
    }

    function resultSourceNote(result) {
        var sources = root.resultAssessmentSources(result)
        if (sources.length === 0)
            return ""
        var labels = []
        for (var i = 0; i < sources.length; ++i)
            labels.push(root.assessmentSourceText(sources[i]))
        var partial = result && (result.completion_status !== "completed"
                                 || (result.unanswered || []).length > 0
                                 || (result.unscored || []).length > 0)
        if (partial)
            return "本场未完整完成；当前数值基于已记录证据，未完成环节按 0 计入，不代表完整面试结果。评分来源："
                   + labels.join("、") + "。"
        if (sources.length === 1 && sources[0] === "self")
            return "本场只包含自评记录；用于复盘，不是面试官结论。"
        if (sources.length === 1 && sources[0] === "grader")
            return "本场代码分数来自本地 Grader 的当前版本公开测试；它不是 AI 或人工主观判断。"
        return "评分来源：" + labels.join("、") + "。请结合下方证据逐条核对。"
    }

    function recordedAtText(value) {
        if (!value)
            return "时间未记录"
        var date = new Date(value)
        if (isNaN(date.getTime()))
            return value
        return Qt.formatDateTime(date, "yyyy-MM-dd HH:mm")
    }

    function followupLabelList(ids) {
        var linked = ids || []
        var records = root.interviewResult.followups || []
        var labels = []
        for (var i = 0; i < linked.length; ++i) {
            var label = linked[i]
            for (var j = 0; j < records.length; ++j) {
                if (records[j].followup_id === linked[i]) {
                    label = "追问 " + (j + 1)
                           + (records[j].parent_title ? "（" + records[j].parent_title + "）" : "")
                    break
                }
            }
            labels.push(label)
        }
        return labels.join("、")
    }

    function confidenceText(value) {
        return ({low: "低", medium: "中", high: "高"})[value] || "未标注"
    }

    function missingEnvironmentLabel(item) {
        if (typeof item === "string")
            return item
        return item.reason || item.requirement || item.name || item.type || "未满足的运行环境"
    }

    function resultScoreText(result) {
        if (!result)
            return "尚未评分"
        if (root.resultAssessmentSources(result).length === 0)
            return "尚未评分"
        var score = result.overall_score
        return score === undefined || score === null ? "尚未评分" : String(score)
    }

    function resultListText(value, emptyText) {
        if (value === undefined || value === null || value === false || value === "")
            return emptyText || ""
        if (!Array.isArray(value))
            return String(value)
        if (value.length === 0)
            return emptyText || ""
        var labels = []
        for (var i = 0; i < value.length; ++i) {
            var item = value[i]
            if (typeof item === "string")
                labels.push(item)
            else
                labels.push(item.title || item.question_id || item.skill || item.reason || JSON.stringify(item))
        }
        return labels.join("、")
    }

    function resultUnscoredText(result) {
        var value = result ? root.resultListText(result.unscored, "") : ""
        return value ? "未评分：" + value : ""
    }

    Component.onCompleted: {
        Qt.callLater(root.initializeSetup)
        Qt.callLater(root.syncQuestionEditors)
    }

    Connections {
        target: app
        function onInterviewPlanReady() {
            personalizedPlanDialog.open()
        }
        function onInterviewTranscriptReady(value) {
            // Transcription is a draft only.  Keep the answer editable and
            // require the normal "submit and lock" action before it becomes
            // interview evidence.
            answer.text = value || ""
            root.answerDraft = answer.text
            answer.forceActiveFocus()
        }
    }

    Timer {
        interval: 1000
        repeat: true
        running: app.interview.status === "active" && app.interview.expired !== true
        onTriggered: app.refreshInterviewClock()
    }

    RowLayout {
        anchors.fill: parent; anchors.margins: root.compactInterviewLayout ? 12 : 26; spacing: 12

        LabCard {
            id: leftPanel
            Layout.preferredWidth: root.compactInterviewLayout ? 220 : 280
            Layout.minimumWidth: 220
            Layout.fillHeight: true
            cardColor: root.palette.surface; borderColor: root.palette.border
            property bool setupVisible: !app.interview.interview_id || app.interview.status === "completed" || app.interview.status === "incomplete"
            padding: 12

            // LabCard's default content column is intentionally lightweight
            // for static cards.  This panel has a viewport plus a persistent
            // footer, so use a local layout to allocate the viewport's
            // remaining height instead of letting its implicit content push
            // the footer below a short window.
            ColumnLayout {
                width: parent.width
                height: parent.height
                spacing: 10

                ScrollView {
                    id: setupScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                Column {
                    width: setupScroll.availableWidth
                    spacing: 9
                    Text { width: parent.width; text: leftPanel.setupVisible ? "面试设置" : "进行中的面试"; color: root.palette.text; font.pixelSize: 19; font.bold: true; wrapMode: Text.Wrap }
                    Text { visible: leftPanel.setupVisible; text: "目标岗位"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: role; width: parent.width; textRole: "title"; valueRole: "id"; model: app.roles; currentIndex: -1; onActivated: root.refreshConfiguration() }
                    Text { visible: leftPanel.setupVisible; text: "求职阶段"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: seniority; width: parent.width; model: [{id:"intern", label:"实习"}, {id:"new_grad", label:"校招"}, {id:"mid", label:"有经验"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.refreshConfiguration() }
                    Text { visible: leftPanel.setupVisible; text: "难度"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: difficulty; width: parent.width; model: [{id:"easy", label:"基础"}, {id:"medium", label:"标准"}, {id:"hard", label:"高压"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.refreshConfiguration() }
                    Text {
                        objectName: "interviewDifficultyHint"
                        visible: leftPanel.setupVisible
                        width: parent.width
                        text: {
                            if (!role.currentValue)
                                return "先选择岗位，系统会检查该难度是否有完整题目。"
                            if (root.configuration.available !== false)
                                return "当前难度可用；开始后题目组合会冻结。"
                            if (root.fallbackAvailable())
                                return "完整蓝图需要 PyTorch 代码环节；当前可开始明确标记的非代码专项。"
                            if ((root.configuration.missing_environment || []).length > 0)
                                return "当前配置无法形成可信的非代码专项；请补齐 PyTorch 环境或切换岗位 / 难度。"
                            return "当前岗位在此难度没有完整固定题；请切换到“标准”或更换岗位。"
                        }
                        color: root.configuration.available === false ? root.palette.warning : root.palette.muted
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        font.pixelSize: 11
                    }
                    Text { visible: leftPanel.setupVisible; text: "面试官"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: aiMode; width: parent.width; model: [{id:"disabled", label:"手动 / 无 AI"}, {id:"provider", label:"普通 LLM API"}, {id:"codex", label:"Codex"}]; textRole: "label"; valueRole: "id" }
                    Text {
                        objectName: "noAiInterviewNotice"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "disabled"
                        text: "模拟面试需要 AI 才能进行真实追问和证据化复盘。No-AI 模式仍可继续刷题、运行测试、复盘和间隔复测；不会创建虚假的 Session、评分或报告。"
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    LabCard {
                        objectName: "noAiInterviewLockPanel"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "disabled"
                        padding: 12
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.border
                        accentColor: root.palette.accent
                        Text {
                            width: parent.width
                            text: "个性化模拟面试已锁定"
                            color: root.palette.text
                            font.bold: true
                            wrapMode: Text.Wrap
                        }
                        Text {
                            width: parent.width
                            text: "接入普通 LLM、配置本地 Ollama 或连接 Codex 后，才能根据你的回答进行追问和证据化复盘。AI 连接不是刷题的前置条件。"
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 11
                        }
                        Flow {
                            width: parent.width
                            spacing: 6
                            Button {
                                objectName: "goToConnectionsFromInterview"
                                text: "打开 AI 连接"
                                onClicked: app.navigate("connections")
                            }
                            Button {
                                objectName: "continueNoAiPractice"
                                text: "继续刷题"
                                onClicked: app.navigate("learn")
                            }
                        }
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "codex"
                        text: "Codex 仍可用于本地 Coach 和仓库协作；Alpha 个性化面试计划当前只支持已测试的普通 LLM API。"
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "provider"
                        text: "AI 连接"
                        color: root.palette.muted
                        font.pixelSize: 12
                    }
                    ComboBox {
                        id: planConnection
                        objectName: "personalizedInterviewConnection"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "provider"
                        model: app.connections
                        textRole: "display_name"
                        valueRole: "connection_id"
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "provider"
                                 && (planConnection.currentIndex < 0
                                     || !root.providerIsReady(planConnection.currentValue))
                        text: planConnection.currentIndex < 0
                              ? "尚未选择 AI 连接。"
                              : "该连接尚未通过测试；请先到 AI 连接页保存并测试。"
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    CheckBox {
                        id: useMaterial
                        width: parent.width
                        visible: leftPanel.setupVisible
                        enabled: aiMode.currentValue !== "disabled" && app.materials.length > 0
                        text: "使用一份逐场授权的求职材料（首版必选）"
                    }
                    ComboBox {
                        id: material
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        model: app.materials
                        textRole: "title"
                        valueRole: "id"
                    }
                    Text {
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked && material.currentIndex >= 0
                        text: material.currentIndex >= 0 ? "材料 ID：" + app.materials[material.currentIndex].id + "\n用途：role_interview\nSHA-256：" + app.materials[material.currentIndex].sha256 : ""
                        color: root.palette.muted
                        font.pixelSize: 10
                        wrapMode: Text.WrapAnywhere
                    }
                    CheckBox {
                        id: consent
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        text: "我同意本场面试读取这个精确 ID / SHA 的材料"
                    }
                    Text {
                        objectName: "interviewConfigurationMessage"
                        width: parent.width
                        visible: leftPanel.setupVisible && root.configuration.available === false
                        text: root.configurationMessage()
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    Button {
                        objectName: "startNonCodingInterview"
                        width: parent.width
                        visible: false
                        text: app.busy ? "正在准备专项面试……" : "开始非代码专项面试"
                        highlighted: true
                        enabled: root.fallbackAvailable()
                                 && !!role.currentValue
                                 && !app.busy
                                 && aiMode.currentValue !== "disabled"
                                 && (!useMaterial.checked || (material.currentIndex >= 0 && app.materials[material.currentIndex].ai_access && consent.checked))
                        onClicked: nonCodingInterviewDialog.open()
                    }
                    Text {
                        objectName: "interviewPyTorchEnvironmentHelp"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && (root.configuration.missing_environment || []).indexOf("pytorch") >= 0
                        text: "完整蓝图需要源码 PyTorch 环境。桌面应用不会自行安装依赖。需先克隆源码并进入仓库根目录，再运行：\npython -m pip install -e \".[torch,dev]\""
                        color: root.palette.muted
                        wrapMode: Text.WrapAnywhere
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "interviewSourceEnvironmentLink"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && (root.configuration.missing_environment || []).indexOf("pytorch") >= 0
                        text: "<a href=\"https://github.com/ComistryMo/llm_interview_lab/blob/main/docs/desktop-app.md\">查看源码环境说明</a>"
                        textFormat: Text.RichText
                        color: root.palette.accent
                        font.pixelSize: 11
                        onLinkActivated: Qt.openUrlExternally(link)
                    }
                    Button {
                        objectName: "startConfiguredInterview"
                        width: parent.width
                        visible: leftPanel.setupVisible
                        text: app.busy ? "正在生成面试计划……" : "预览 AI 个性化面试计划"
                        highlighted: !root.fallbackAvailable()
                        enabled: root.configuration.available !== false
                                 && !!role.currentValue
                                 && !app.busy
                                 && aiMode.currentValue === "provider"
                                 && role.currentValue === "post_training_engineer"
                                 && seniority.currentValue === "new_grad"
                                 && difficulty.currentValue === "medium"
                                 && planConnection.currentIndex >= 0
                                 && root.providerIsReady(planConnection.currentValue)
                                 && useMaterial.checked
                                 && material.currentIndex >= 0
                                 && app.materials[material.currentIndex].ai_access
                                 && consent.checked
                        // Creating a session freezes the public question plan
                        // and starts the authoritative clock.  Require an
                        // explicit review/confirmation so a stray click
                        // cannot create a real interview before the learner
                        // sees the selected role, difficulty and AI policy.
                        onClicked: {
                            root.planContext = app.personalizedInterviewPlanContext(
                                role.currentValue,
                                seniority.currentValue,
                                difficulty.currentValue,
                                material.currentValue,
                                consent.checked
                            )
                            if ((root.planContext.parts || []).length > 0)
                                planContextDialog.open()
                        }
                    }
                    Text {
                        objectName: "personalizedInterviewAlphaScope"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "provider"
                        text: "当前真实 Golden Path：后训练工程师 · 校招 · 标准难度。非代码问题由 AI 基于授权材料生成并先供你确认；Coding 题只从已验证题库选择。"
                        color: root.palette.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Rectangle { width: parent.width; height: 1; color: root.palette.border }
                    Text { text: "本场事实"; color: root.palette.text; font.bold: true }
                    Text {
                        width: parent.width
                        text: app.interview.interview_id
                              ? "状态  " + root.statusText(app.interview.status)
                                + "\n岗位  " + (app.interview.role_title || app.interview.role_id)
                                + "\n求职级别  " + root.seniorityText(app.interview.seniority)
                                + "\n选题档位  " + root.difficultyText(app.interview.difficulty)
                                + (app.interview.delivery_mode === "non_coding_fallback"
                                   ? "\n范围  非代码专项（部分证据）" : "")
                                + "\n进度  " + (app.interview.completed_questions || 0)
                                + " / " + (app.interview.total_questions || 0)
                              : "暂无进行中的面试"
                        color: root.palette.muted
                        wrapMode: Text.Wrap
                        lineHeight: 1.5
                    }
                    Text {
                        objectName: "interviewExpiryNotice"
                        visible: app.interview.expired === true
                        width: parent.width
                        text: "本场计时已到；不能继续回答。请打开面试页并选择“结束本场”生成未完成报告。"
                        color: root.palette.danger
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                        font.bold: true
                    }
                    ToolButton {
                        visible: !!app.interview.interview_id
                        text: root.showSessionDetails ? "收起技术详情" : "查看技术详情"
                        onClicked: root.showSessionDetails = !root.showSessionDetails
                    }
                    Text {
                        visible: root.showSessionDetails && !!app.interview.interview_id
                        width: parent.width
                        text: "会话 ID：" + app.interview.interview_id
                              + (app.interview.blueprint_id ? "\n蓝图：" + app.interview.blueprint_id : "")
                              + "\n本场选题难度：" + root.difficultyText(app.interview.difficulty)
                              + (root.activeQuestionId ? "\n当前问题 ID：" + root.activeQuestionId : "")
                        color: root.palette.muted
                        font.pixelSize: 10
                        wrapMode: Text.WrapAnywhere
                    }
                    Text { width: parent.width; text: "模拟面试分数不会改变刷题训练的掌握状态。"; color: root.palette.warning; wrapMode: Text.Wrap; font.pixelSize: 12; font.bold: true }
                }
            }
        }
        }

        LabCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            cardColor: root.palette.surface
            prominent: !!activeQuestion
            accentColor: activeQuestion ? root.palette.accent : "transparent"
            borderColor: activeQuestion ? root.palette.accent : root.palette.border
            // The question viewport and the persistent finish action need real
            // remaining-space allocation.  LabCard intentionally uses a plain
            // Column for simple cards, so this interview panel owns a local
            // ColumnLayout rather than relying on ignored Layout.fillHeight
            // hints inside that Column.
            ColumnLayout {
                width: parent.width
                height: parent.height
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: activeQuestion ? (activeQuestion.kind === "coding" ? "代码题" : (activeQuestion.kind === "system_design" ? "系统设计" : "结构化问答")) : "模拟面试室"; color: root.palette.accent; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1 }
                    Text { Layout.fillWidth: true; text: activeQuestion ? activeQuestion.title : "按岗位蓝图开始一场面试"; color: root.palette.text; font.pixelSize: 22; font.bold: true; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                }
                StatusPill {
                    // Keep the existing test/accessibility hook while moving
                    // the phase marker next to the question title.
                    objectName: "interviewPhasePill"
                    visible: !!activeQuestion && app.interview.status === "active"
                    text: root.answerLocked
                          ? (app.interview.pending_followup ? "阶段 C · 追问" : "阶段 B · 评估")
                          : "阶段 A · 回答"
                    tone: root.answerLocked ? root.palette.accent : root.palette.muted
                }
                StatusPill {
                    text: app.interview.status === "active"
                          ? root.timerText(app.interview.remaining_seconds)
                          : root.statusText(app.interview.status)
                    tone: app.interview.status === "active" ? root.palette.warning : root.palette.muted
                }
                Button {
                    visible: app.interview.status === "active" || app.interview.status === "paused"
                    text: app.interview.status === "paused" ? "恢复计时" : "暂停"
                    flat: true
                    enabled: !app.busy
                    onClicked: app.interview.status === "paused"
                               ? app.resumeInterview() : pauseInterviewDialog.open()
                }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: root.palette.border }
                ScrollView {
                id: questionScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                // Keep the question column tied to the panel viewport.  Without
                // an explicit content width, Qt sizes the Flickable content to
                // the TextArea's implicit width, leaving the editor as a narrow
                // strip and making the phase controls collide on small screens.
                contentWidth: availableWidth
                Column {
                    width: questionScroll.availableWidth
                    spacing: root.compactInterviewLayout ? 12 : 16
                    Text { width: parent.width; text: activeQuestion ? activeQuestion.prompt : "选择岗位、求职阶段与难度。系统会冻结一份公共面试蓝图，每次只展示一个问题，并将客观代码证据与 Rubric 主观判断分开。"; color: root.palette.text; wrapMode: Text.Wrap; textFormat: Text.MarkdownText; lineHeight: 1.25 }
                    TextArea { id: answer; objectName: "interviewAnswerEditor"; width: parent.width; height: root.compactInterviewLayout ? 140 : 180; visible: !!activeQuestion && activeQuestion.kind !== "coding"; text: root.answerLocked ? (app.interview.answer_text || "") : root.answerDraft; readOnly: root.answerLocked || !root.interviewCanEdit; onTextChanged: if (!root.answerLocked && !root.syncingQuestionEditors) root.answerDraft = text; placeholderText: root.answerLocked ? "回答已锁定" : !root.interviewCanEdit ? "面试已暂停或结束" : "输入你的回答……"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.answerLocked ? root.palette.accent : root.palette.border } }
                    LabCard {
                        objectName: "interviewVoiceCard"
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && !root.answerLocked && root.interviewCanEdit
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: app.interviewVoice.state === "recording"
                                      ? root.palette.warning : root.palette.border
                        ColumnLayout {
                            width: parent.width
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "语音回答（可选）"
                                    color: root.palette.text
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                StatusPill {
                                    objectName: "interviewVoiceState"
                                    text: app.interviewVoice.state === "recording"
                                          ? "录音中"
                                          : app.interviewVoice.transcription_state === "transcribing"
                                            ? "转录中" : app.interviewVoice.audio_ready ? "已录音" : "未开始"
                                    tone: app.interviewVoice.state === "recording"
                                          ? root.palette.warning : root.palette.muted
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "录音保存在当前学习档案；只有勾选本次授权并点击转录时，音频才会发送到所选 AI 服务。转录结果会先放入可编辑回答框。"
                                color: root.palette.muted
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Button {
                                    objectName: "startInterviewRecording"
                                    text: "开始录音"
                                    enabled: app.interviewVoice.state !== "recording"
                                             && app.interviewVoice.transcription_state !== "transcribing"
                                             && !app.busy
                                    onClicked: app.startInterviewRecording()
                                }
                                Button {
                                    objectName: "stopInterviewRecording"
                                    text: "停止录音"
                                    enabled: app.interviewVoice.state === "recording"
                                    onClicked: app.stopInterviewRecording()
                                }
                                Text {
                                    objectName: "interviewVoiceDuration"
                                    text: {
                                        var ms = Number(app.interviewVoice.duration_ms || 0)
                                        var seconds = Math.floor(ms / 1000)
                                        return "时长 " + (seconds < 10 ? "0" : "") + seconds + " 秒"
                                    }
                                    color: root.palette.muted
                                    font.pixelSize: 12
                                }
                                Item { Layout.fillWidth: true }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                ComboBox {
                                    id: voiceConnection
                                    objectName: "interviewVoiceConnection"
                                    Layout.fillWidth: true
                                    model: app.connections
                                    textRole: "display_name"
                                    valueRole: "connection_id"
                                    enabled: app.interviewVoice.audio_ready
                                             && app.interviewVoice.transcription_state !== "transcribing"
                                }
                                CheckBox {
                                    id: voiceConsent
                                    objectName: "interviewVoiceRemoteConsent"
                                    text: "本次允许远程转录"
                                    enabled: app.interviewVoice.audio_ready
                                             && app.interviewVoice.transcription_state !== "transcribing"
                                }
                                Button {
                                    objectName: "transcribeInterviewRecording"
                                    text: app.interviewVoice.transcription_state === "transcribing"
                                          ? "正在转录…" : "转录到回答框"
                                    enabled: app.interviewVoice.audio_ready
                                             && voiceConsent.checked
                                             && voiceConnection.currentValue
                                             && app.interviewVoice.transcription_state !== "transcribing"
                                             && !app.busy
                                    onClicked: app.transcribeInterviewRecording(
                                        voiceConnection.currentValue, voiceConsent.checked
                                    )
                                }
                            }
                            Text {
                                visible: (app.connections || []).length === 0
                                Layout.fillWidth: true
                                text: "尚未配置可用的 AI 连接。你仍可直接输入文字回答；如需转录，请先在 AI 连接页保存并测试。"
                                color: root.palette.muted
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                            Text {
                                visible: !!app.interviewVoice.error
                                Layout.fillWidth: true
                                text: app.interviewVoice.error || ""
                                color: root.palette.danger
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                    LabCard {
                        objectName: "interviewAnswerCorruption"
                        visible: !!app.interview.answer_corrupted
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.danger
                        Text { width: parent.width; text: app.interview.answer_error || "已锁定的回答当前不可读取，评分已暂停。"; color: root.palette.danger; wrapMode: Text.Wrap; font.bold: true }
                    }
                    Rectangle {
                        objectName: "interviewPhaseGuidance"
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                        width: parent.width
                        height: root.compactInterviewLayout ? 48 : 42
                        radius: 8
                        color: root.palette.surfaceAlt
                        border.color: root.answerLocked ? root.palette.accent : root.palette.border
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 10
                            spacing: 10
                            Text {
                                text: root.answerLocked ? "阶段 B · 评估" : "阶段 A · 回答"
                                color: root.answerLocked ? root.palette.accent : root.palette.muted
                                font.bold: true
                                font.pixelSize: 12
                            }
                            Text {
                                text: root.answerLocked
                                      ? "回答已锁定；先记录证据，再选择评分来源。"
                                      : "完成回答后提交并锁定，评分维度才会显示。"
                                color: root.palette.muted
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                                Button {
                                    objectName: "lockInterviewAnswer"
                                    visible: !root.answerLocked
                                    text: "提交并锁定回答"
                                    highlighted: true
                                    enabled: root.interviewCanEdit && answer.text.trim().length > 0 && !app.busy
                                    Layout.preferredHeight: 36
                                onClicked: {
                                    root.pendingLockAnswer = answer.text
                                    lockAnswerDialog.open()
                                }
                            }
                        }
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && !root.answerLocked && answer.text.trim().length === 0
                        text: "先写下回答，提交按钮才会启用。"
                        color: root.palette.muted
                        font.pixelSize: 11
                    }
                    Column {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted
                        width: parent.width
                        spacing: 6
                        Text { text: "候选人自评 Rubric（每个维度 1–5 分）"; color: root.palette.muted; font.bold: true }
                        Text { text: "用于自我校准，不代表客观面试结论。请点击每个滑块选择分数，未评分项不会提交。"; color: root.palette.muted; font.pixelSize: 11; wrapMode: Text.Wrap; width: parent.width }
                        Repeater {
                            model: activeQuestion ? Object.keys(activeQuestion.rubric.dimensions) : []
                            delegate: RowLayout {
                                required property string modelData
                                width: parent.width
                                Text { text: modelData.replace(/_/g, " "); color: root.palette.text; Layout.preferredWidth: 190 }
                                Slider {
                                    id: dimensionScore
                                    // Zero is a presentation-only placeholder.
                                    // A rubric score is published only after an
                                    // explicit drag/click, so an untouched
                                    // slider can never look like a score of 1.
                                    from: 0; to: 5; stepSize: 1; value: 0
                                    Layout.fillWidth: true
                                    Accessible.name: modelData.replace(/_/g, " ") + "自评分数"
                                    Accessible.description: "点击或拖动选择 1 到 5 分"
                                    // A click on the initial value (1) may not
                                    // emit valueChanged. Record the press too,
                                    // so choosing the lowest score is still an
                                    // explicit, valid assessment.
                                    onPressedChanged: if (pressed && value >= 1) root.setRubricScore(modelData, Math.round(value))
                                    enabled: root.interviewCanEdit
                                    onValueChanged: if ((pressed || activeFocus) && value >= 1) root.setRubricScore(modelData, Math.round(value))
                                }
                                Text { text: root.rubricScores[modelData] === undefined ? "未评分" : root.rubricScores[modelData] + " / 5"; color: root.palette.text; font.bold: true; Layout.preferredWidth: 54 }
                            }
                        }
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && root.answerLocked && !app.interview.answer_corrupted
                        text: "回答证据 · 必填"
                        color: root.palette.text
                        font.bold: true
                        font.pixelSize: 13
                        width: parent.width
                    }
                    TextArea { id: evidence; width: parent.width; height: 86; visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted; enabled: root.interviewCanEdit; placeholderText: root.interviewCanEdit ? "请引用回答中的具体证据（必填）" : "面试已暂停或结束"; wrapMode: Text.Wrap; padding: 12; clip: true; background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.palette.border } }
                    ComboBox {
                        id: providerConnection
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted && app.interview.ai_mode === "provider"
                        width: parent.width
                        model: app.connections
                        textRole: "display_name"
                        valueRole: "connection_id"
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && root.answerLocked && !app.interview.answer_corrupted
                                 && providerConnection.currentIndex >= 0
                                 && !root.providerIsReady(providerConnection.currentValue)
                        width: parent.width
                        text: "当前连接尚未测试通过。请到“AI 连接”测试后再请求评估，或改用人工评分。"
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && root.answerLocked && !app.interview.answer_corrupted
                                 && app.interview.ai_mode === "provider"
                                 && providerConnection.currentIndex < 0
                        width: parent.width
                        text: "还没有可用的已测试连接；可以去 AI 连接页配置，或直接记录人工评分。"
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    CheckBox {
                        id: includeInterviewMaterials
                        visible: !!activeQuestion && root.answerLocked && !app.interview.answer_corrupted
                                 && activeQuestion.kind !== "coding"
                                 && app.interview.ai_mode !== "disabled"
                                 && (app.interview.material_refs || []).length > 0
                        checked: true
                        text: "在本次 AI 请求中包含已授权材料"
                    }
                    Flow {
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted
                        width: parent.width
                        spacing: 8
                        Button {
                            objectName: "recordSelfAssessment"
                            text: "记录自评结果"
                            enabled: root.interviewCanEdit && root.rubricComplete() && evidence.text.trim().length > 0
                                     && !app.busy && !app.interview.assessment_recorded
                            onClicked: app.answerInterviewDetailed(answer.text, JSON.stringify(root.rubricScores), evidence.text)
                        }
                        Button {
                            visible: app.interview.ai_mode === "provider"
                            enabled: root.interviewCanEdit && providerConnection.currentIndex >= 0
                                     && root.providerIsReady(providerConnection.currentValue)
                                     && !app.busy
                                     && !app.interview.assessment_recorded
                            text: "预览 AI 评分上下文"
                            highlighted: true
                            onClicked: root.previewAI("provider", providerConnection.currentValue)
                        }
                        Button {
                            visible: app.interview.ai_mode === "provider"
                                     && (providerConnection.currentIndex < 0
                                         || !root.providerIsReady(providerConnection.currentValue))
                            text: "去 AI 连接"
                            flat: true
                            onClicked: app.navigate("connections")
                        }
                        Button {
                            visible: app.interview.ai_mode === "codex"
                                     && !(app.aiStatus.indexOf("已连接") >= 0
                                          || app.aiStatus.indexOf("就绪") >= 0)
                            enabled: root.interviewCanEdit && !app.busy && !app.interview.assessment_recorded
                            text: "连接 Codex 面试官"
                            highlighted: true
                            onClicked: app.connectCodex("interviewer")
                        }
                        Button {
                            visible: app.interview.ai_mode === "codex" && (app.aiStatus.indexOf("已连接") >= 0 || app.aiStatus.indexOf("就绪") >= 0)
                            enabled: root.interviewCanEdit && !app.busy && !app.interview.assessment_recorded
                            text: "请求 Codex 评分"
                            onClicked: root.previewAI("codex", "")
                        }
                    }
                    Text {
                        visible: !!app.interview.ai_assessment_state
                                 && app.interview.ai_assessment_state !== "complete"
                        width: parent.width
                        text: app.interview.ai_assessment_state === "streaming"
                              ? "Codex 正在按冻结 Rubric 生成评分证据……"
                              : app.interview.ai_error || "Codex 评分尚未完成；可以检查连接后重试。"
                        color: app.interview.ai_assessment_state === "streaming"
                               ? root.palette.accent : root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    LabCard {
                        visible: !!app.interview.pending_followup
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.accent
                        Text { width: parent.width; text: "自适应追问\n" + (app.interview.pending_followup || ""); color: root.palette.text; wrapMode: Text.Wrap; font.bold: true }
                        TextArea { id: followupAnswer; width: parent.width; height: 100; enabled: root.interviewCanEdit; placeholderText: root.interviewCanEdit ? "回答这一个追问" : "面试已暂停或结束"; wrapMode: Text.Wrap; padding: 12; clip: true }
                        Text {
                            width: parent.width
                            text: "追问回答会留档并关联到本题评估；当前评分仍采用主回答生成的 AI 评估，不会根据这次追问自动重算。"
                            color: root.palette.muted
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                        Button {
                            text: "记录追问回答并采用已有评估"
                            highlighted: true
                            enabled: root.interviewCanEdit && followupAnswer.text.trim().length > 0 && !app.busy
                            onClicked: app.answerAIFollowup(followupAnswer.text)
                        }
                    }
                    LabCard {
                        objectName: "interviewResultCard"
                        visible: Object.keys(root.interviewResult).length > 0
                        width: parent.width
                        cardColor: root.palette.surfaceAlt
                        borderColor: root.palette.border
                        Text { width: parent.width; text: "本场评估"; color: root.palette.text; font.pixelSize: 18; font.bold: true }
                        Text {
                            width: parent.width
                            text: root.resultScoreLabel(root.interviewResult) + "：" + root.resultScoreText(root.interviewResult)
                                  + "\n完成状态：" + root.statusText(root.interviewResult.completion_status)
                            color: root.palette.text
                            wrapMode: Text.Wrap
                            lineHeight: 1.4
                        }
                        Text {
                            objectName: "interviewFallbackResultScope"
                            width: parent.width
                            visible: root.interviewResult.delivery_mode === "non_coding_fallback"
                            text: "非代码专项 · 蓝图证据覆盖 "
                                  + Math.round(Number((root.interviewResult.blueprint_coverage || {}).coverage_weight || 0) * 100)
                                  + "%\n省略代码实现轮次："
                                  + root.fallbackRoundSummary((root.interviewResult.blueprint_coverage || {}).omitted_rounds)
                            color: root.palette.warning
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            visible: root.resultSourceNote(root.interviewResult).length > 0
                            text: root.resultSourceNote(root.interviewResult)
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                        }
                        Text {
                            width: parent.width
                            visible: !!root.interviewResult.summary
                            text: root.interviewResult.summary || ""
                            color: root.palette.text
                            wrapMode: Text.Wrap
                        }
                        Text { width: parent.width; text: "评分证据"; color: root.palette.muted; font.bold: true }
                        Repeater {
                            model: root.interviewResult.assessment_evidence || []
                            delegate: Rectangle {
                                required property var modelData
                                width: parent.width
                                height: evidenceColumn.implicitHeight + 16
                                radius: 8
                                color: root.palette.surface
                                border.color: root.palette.border
                                Column {
                                    id: evidenceColumn
                                    x: 10; y: 8; width: parent.width - 20; spacing: 4
                                    Text {
                                        width: parent.width
                                        text: (modelData.title || modelData.question_id || "未命名问题")
                                              + (modelData.score === undefined || modelData.score === null ? " · 尚未评分" : " · " + modelData.score)
                                        color: root.palette.text
                                        font.bold: true
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        width: parent.width
                                        text: "来源：" + root.assessmentSourceText(modelData.source)
                                              + " · 置信度：" + root.confidenceText(modelData.confidence)
                                        color: root.palette.muted
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        visible: (modelData.followup_ids || []).length > 0
                                        width: parent.width
                                        text: "关联追问：" + root.followupLabelList(modelData.followup_ids)
                                        color: root.palette.accent
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        width: parent.width
                                        text: modelData.evidence || "未记录评分证据。"
                                        color: root.palette.text
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                        Column {
                            visible: (root.interviewResult.followups || []).length > 0
                            width: parent.width
                            spacing: 8
                            Text { width: parent.width; text: "追问记录"; color: root.palette.muted; font.bold: true }
                            Repeater {
                                model: root.interviewResult.followups || []
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    width: parent.width
                                    height: followupColumn.implicitHeight + 16
                                    radius: 8
                                    color: root.palette.surface
                                    border.color: root.palette.border
                                    Column {
                                        id: followupColumn
                                        x: 10; y: 8; width: parent.width - 20; spacing: 4
                                        Text {
                                            width: parent.width
                                            text: "追问 " + (index + 1) + " · "
                                                  + (modelData.parent_title || modelData.parent_question_id || "原问题未记录")
                                            color: root.palette.accent
                                            font.bold: true
                                            wrapMode: Text.Wrap
                                        }
                                        Text { width: parent.width; text: modelData.prompt || ""; color: root.palette.text; wrapMode: Text.Wrap }
                                        Text { width: parent.width; text: "回答：" + (modelData.answer || ""); color: root.palette.text; wrapMode: Text.Wrap }
                                        Text { width: parent.width; text: "来源：" + root.assessmentSourceText(modelData.source); color: root.palette.muted; font.pixelSize: 11; wrapMode: Text.Wrap }
                                        Text {
                                            width: parent.width
                                            text: "记录：" + (modelData.followup_id || "未编号")
                                                  + " · " + root.recordedAtText(modelData.recorded_at)
                                            color: root.palette.muted
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }
                            }
                        }
                        Text {
                            width: parent.width
                            visible: (root.interviewResult.assessment_evidence || []).length === 0
                            text: "本场没有足够证据支持评分。"
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                        }
                        Text {
                            width: parent.width
                            visible: root.resultListText(root.interviewResult.critical_gaps, "").length > 0
                            text: "关键缺口：" + root.resultListText(root.interviewResult.critical_gaps, "")
                            color: root.palette.warning
                            wrapMode: Text.Wrap
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            visible: root.resultUnscoredText(root.interviewResult).length > 0
                            text: root.resultUnscoredText(root.interviewResult)
                            color: root.palette.warning
                            wrapMode: Text.Wrap
                            font.bold: true
                        }
                        Text {
                            width: parent.width
                            text: "该结果只记录模拟面试证据，不会改变刷题训练的掌握状态。"
                            color: root.palette.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                        }
                    }
                    ColumnLayout {
                        visible: !!activeQuestion && activeQuestion.kind === "coding"
                        width: parent.width; spacing: 10
                        Text { text: "本场冻结的代码答案"; color: root.palette.text; font.bold: true }
                        TextArea {
                            id: codingEditor
                            Layout.fillWidth: true; Layout.preferredHeight: root.compactInterviewLayout ? 210 : 260
                            text: app.interview.coding_text || ""
                            readOnly: !root.interviewCanEdit
                            color: root.palette.text
                            font.family: root.codeFontFamily
                            font.pixelSize: 13
                            wrapMode: TextEdit.NoWrap
                            padding: 12
                            clip: true
                            background: Rectangle { color: root.palette.surfaceAlt; radius: 8; border.color: root.palette.border }
                            Accessible.name: "限时代码面试编辑器"
                            onTextChanged: if (!root.syncingQuestionEditors) root.codingEditorDirty = true
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Button {
                                text: "保存"
                                enabled: root.interviewCanEdit && !app.busy
                                onClicked: {
                                    // The controller returns false when the
                                    // immutable interview snapshot cannot be
                                    // written.  Keep the editor dirty so the
                                    // learner can retry instead of implying a
                                    // save that never happened.
                                    if (app.saveInterviewCoding(codingEditor.text))
                                        root.codingEditorDirty = false
                                }
                            }
                            Button {
                                text: "运行 Grader"
                                highlighted: true
                                enabled: root.interviewCanEdit && !app.busy
                                onClicked: {
                                    // The controller saves exactly this
                                    // snapshot before grading. A failed run
                                    // still leaves coding_test_current=false,
                                    // so the record action remains disabled.
                                    if (app.runInterviewCoding(codingEditor.text))
                                        root.codingEditorDirty = false
                                }
                            }
                            Button {
                                objectName: "recordInterviewCodingRound"
                                text: "记录本轮并继续"
                                enabled: root.interviewCanEdit && !app.busy && !root.codingEditorDirty
                                         && app.interview.coding_test_current === true
                                onClicked: app.recordInterviewCodingRound()
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.codingEditorDirty
                                  ? "当前编辑器有未保存修改；请保存并重新运行 Grader。"
                                  : app.interview.coding_test_current === true
                                    ? "当前版本已由本地 Grader 测试，可记录为客观代码证据。"
                                    : "请先运行本地 Grader；未复测的代码不能记录。"
                            color: root.codingEditorDirty
                                   ? root.palette.warning
                                   : app.interview.coding_test_current === true
                                     ? root.palette.success : root.palette.muted
                            wrapMode: Text.Wrap
                            font.pixelSize: 11
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 110; radius: 8
                            color: root.palette.surfaceAlt; border.color: root.palette.border
                            ScrollView {
                                anchors.fill: parent; anchors.margins: 10
                                Text { width: parent.width; text: app.testOutput || "本地 Grader 是代码结果的事实来源。"; color: root.palette.text; wrapMode: Text.Wrap; font.family: root.codeFontFamily; font.pixelSize: 11 }
                            }
                        }
                        Text { text: "面试进行中不会展示教学提示。代码记录只接受当前编辑器已复测的版本。"; color: root.palette.warning; font.pixelSize: 12; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    }
                }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: root.palette.border; opacity: 0.8 }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 40
                    Text {
                        text: activeQuestion ? "一次只完成一个主问题" : ""
                        color: root.palette.muted
                        font.pixelSize: 12
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        objectName: "finishInterviewButton"
                        text: "结束本场"
                        flat: true
                        Layout.preferredWidth: 96
                        Layout.preferredHeight: 36
                        enabled: !!app.interview.interview_id
                                 && (app.interview.status === "active"
                                     || app.interview.status === "paused"
                                     || app.interview.status === "timed_out")
                                 && !app.busy
                        onClicked: finishDialog.open()
                    }
                }
            }
        }
    }

    Dialog {
        id: lockAnswerDialog
        objectName: "lockInterviewAnswerDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(460, root.width - 48)
        implicitHeight: 190
        height: implicitHeight
        title: "锁定本题回答？"
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            if (!root.answerLocked && root.pendingLockAnswer.trim().length > 0)
                app.lockInterviewAnswer(root.pendingLockAnswer)
            root.pendingLockAnswer = ""
        }
        onRejected: root.pendingLockAnswer = ""
        contentItem: Text {
            // Avoid a Dialog implicitHeight ↔ content width binding loop on
            // compact windows; the dialog itself already has a bounded width.
            width: Math.min(400, Math.max(240, root.width - 96))
            text: "提交后回答会冻结，不能再修改；之后才能进入评分和追问阶段。请确认这就是你要留下的最终回答。"
            color: root.palette.text
            wrapMode: Text.Wrap
        }
    }

    Dialog {
        id: pauseInterviewDialog
        objectName: "pauseInterviewDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(420, root.width - 48)
        implicitHeight: 180
        height: implicitHeight
        title: "暂停本场面试？"
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: app.pauseInterview()
        contentItem: Text {
            width: Math.min(360, Math.max(240, root.width - 96))
            text: "暂停会冻结本地计时和当前题目。恢复后从剩余时间继续；暂停期间不能提交回答或运行代码。"
            color: root.palette.text
            wrapMode: Text.Wrap
        }
    }

    Dialog {
        id: contextDialog
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, root.width - 64)
        height: Math.min(520, root.height - 64)
        title: "上下文预览（只读）"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.pendingAIAction === "provider")
                app.assessInterviewWithProvider(
                    answer.text,
                    root.pendingConnection,
                    includeInterviewMaterials.checked
                )
            else if (root.pendingAIAction === "codex")
                app.sendCodexInterviewAnswer(
                    answer.text,
                    includeInterviewMaterials.checked
                )
            root.pendingAIAction = ""
            root.pendingConnection = ""
        }
        onRejected: {
            root.pendingAIAction = ""
            root.pendingConnection = ""
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "只有下面标记为“将发送”的内容会被发送；取消则不会发送任何内容。"
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                Column {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: root.aiPreview.parts || []
                        delegate: RowLayout {
                            required property var modelData
                            width: parent.width
                            StatusPill {
                                text: modelData.selected ? "将发送" : "不发送"
                                tone: modelData.selected ? root.palette.accent : root.palette.muted
                            }
                            Text {
                                text: modelData.label
                                color: root.palette.text
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            StatusPill {
                                visible: modelData.sensitive
                                text: "敏感内容"
                                tone: root.palette.warning
                            }
                        }
                    }
                }
            }
            Text {
                text: "预计上下文：" + (root.aiPreview.estimated_tokens || 0) + " tokens"
                color: root.palette.muted
                font.pixelSize: 12
            }
        }
    }

    Dialog {
        id: planContextDialog
        objectName: "personalizedInterviewContextDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(620, root.width - 48)
        height: Math.min(520, root.height - 48)
        title: "确认发送给 AI 的上下文"
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: app.generatePersonalizedInterviewPlan(
            role.currentValue,
            seniority.currentValue,
            difficulty.currentValue,
            planConnection.currentValue,
            material.currentValue,
            consent.checked,
            root.planContext.context_sha256 || ""
        )
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "只有下列明确列出的内容会发送。本次确认只用于生成计划；Coding 题、Rubric 和计时仍由本地确定性代码决定。"
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                Column {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: root.planContext.parts || []
                        delegate: RowLayout {
                            required property var modelData
                            width: parent.width
                            StatusPill {
                                text: modelData.selected ? "将发送" : "不发送"
                                tone: modelData.selected ? root.palette.accent : root.palette.muted
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.label
                                color: root.palette.text
                                wrapMode: Text.Wrap
                            }
                            StatusPill {
                                visible: modelData.sensitive
                                text: "敏感内容"
                                tone: root.palette.warning
                            }
                        }
                    }
                }
            }
            Text {
                text: "预计上下文：" + (root.planContext.estimated_tokens || 0)
                      + " tokens · SHA " + String(root.planContext.context_sha256 || "").slice(0, 12)
                color: root.palette.muted
                font.pixelSize: 11
            }
        }
    }

    Dialog {
        id: personalizedPlanDialog
        objectName: "personalizedInterviewPlanDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(720, root.width - 48)
        height: Math.min(620, root.height - 48)
        title: "确认冻结 AI 个性化面试计划"
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: app.interviewPlanPreview.user_message || "请检查计划。"
                color: root.palette.text
                wrapMode: Text.Wrap
                font.bold: true
            }
            Text {
                Layout.fillWidth: true
                text: "岗位：" + (app.interviewPlanPreview.role_title || "")
                      + " · 总时长：" + (app.interviewPlanPreview.duration_minutes || 0) + " 分钟"
                      + "\n材料：" + ((app.interviewPlanPreview.material_refs || []).length)
                      + " 份逐场授权 · 上下文 SHA："
                      + String(app.interviewPlanPreview.plan_context_sha256 || "").slice(0, 12)
                color: root.palette.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                Column {
                    width: parent.width
                    spacing: 10
                    Repeater {
                        model: app.interviewPlanPreview.questions || []
                        delegate: LabCard {
                            required property var modelData
                            width: parent.width
                            cardColor: root.palette.surfaceAlt
                            borderColor: modelData.source.kind === "catalog_problem"
                                         ? root.palette.accent : root.palette.border
                            Text {
                                width: parent.width
                                text: (modelData.source.kind === "catalog_problem" ? "已验证题库 Coding" : "AI 生成 · " + root.roundTypeText(modelData.kind))
                                      + " · " + modelData.timebox_minutes + " 分钟"
                                color: modelData.source.kind === "catalog_problem"
                                       ? root.palette.accent : root.palette.muted
                                font.pixelSize: 11
                                font.bold: true
                            }
                            Text {
                                width: parent.width
                                text: modelData.title
                                color: root.palette.text
                                font.pixelSize: 16
                                font.bold: true
                                wrapMode: Text.Wrap
                            }
                            Text {
                                width: parent.width
                                text: modelData.prompt
                                color: root.palette.muted
                                wrapMode: Text.Wrap
                                maximumLineCount: 4
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "取消"
                    onClicked: {
                        app.cancelPersonalizedInterviewPlan()
                        personalizedPlanDialog.close()
                    }
                }
                Button {
                    objectName: "confirmPersonalizedInterviewPlan"
                    text: "确认并开始计时"
                    highlighted: true
                    enabled: app.interviewPlanPreview.status === "ready" && !app.busy
                    onClicked: {
                        if (app.confirmPersonalizedInterviewPlan())
                            personalizedPlanDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: startInterviewDialog
        objectName: "startInterviewConfirmationDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(500, root.width - 48)
        implicitHeight: 300
        height: implicitHeight
        title: "确认冻结本场面试？"
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            // Keep the boundary authoritative even if a stale dialog remains
            // open while the user changes the interviewer selector.  No-AI
            // can run Practice, but must never create a faux interview
            // session from the fixed fallback content.
            if (aiMode.currentValue === "disabled") {
                app.navigate("connections")
                return
            }
            if (useMaterial.checked)
                app.createTailoredInterview(
                    role.currentValue,
                    seniority.currentValue,
                    difficulty.currentValue,
                    material.currentValue,
                    consent.checked,
                    aiMode.currentValue
                )
            else
                app.createConfiguredInterview(
                    role.currentValue,
                    seniority.currentValue,
                    difficulty.currentValue,
                    aiMode.currentValue
                )
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "开始后会创建一份不可静默改题的本地 session，并启动本地计时。"
                color: root.palette.text
                wrapMode: Text.Wrap
                font.bold: true
            }
            Text {
                Layout.fillWidth: true
                text: "岗位：" + (role.currentText || "未选择")
                      + "\n求职阶段：" + root.seniorityText(seniority.currentValue)
                      + "\n难度：" + root.difficultyText(difficulty.currentValue)
                      + "\n面试官：" + (aiMode.currentText || "手动 / 无 AI")
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "固定题目环节：" + ((root.configuration.rounds || []).length || "按岗位蓝图")
                      + " · 题目组合和公开 Rubric 会在创建时冻结。"
                color: root.palette.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
            Text {
                Layout.fillWidth: true
                visible: useMaterial.checked
                text: "材料：仅使用你勾选并同意的精确 ID / SHA；不会读取其他材料。"
                color: root.palette.warning
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
            Text {
                Layout.fillWidth: true
                text: "确认后才会写入当前 Profile；取消不会创建 session。"
                color: root.palette.muted
                wrapMode: Text.Wrap
                font.pixelSize: 12
            }
        }
    }

    Dialog {
        id: nonCodingInterviewDialog
        objectName: "nonCodingInterviewConfirmationDialog"
        modal: true
        anchors.centerIn: parent
        width: Math.min(540, root.width - 48)
        height: Math.min(500, root.height - 48)
        title: "这不是完整岗位蓝图"
        onOpened: fallbackBackButton.forceActiveFocus()
        contentItem: Flickable {
            id: fallbackDialogViewport
            clip: true
            contentWidth: width
            contentHeight: fallbackDialogContent.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: fallbackDialogContent
                width: Math.max(0, fallbackDialogViewport.width - 12)
                spacing: 10
                Text {
                    Layout.fillWidth: true
                    text: "当前环境缺少完整蓝图所需的 PyTorch 代码环节。你可以明确选择只完成其余固定非代码轮次。"
                    color: root.palette.text
                    wrapMode: Text.Wrap
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "包含：" + root.fallbackRoundSummary(root.nonCodingFallback().included_rounds)
                          + "\n省略：" + root.fallbackRoundSummary(root.nonCodingFallback().omitted_rounds)
                          + "\n专项时长：" + Number(root.nonCodingFallback().duration_minutes || 0) + " 分钟"
                          + "\n蓝图证据覆盖：" + root.fallbackCoveragePercent() + "%"
                    color: root.palette.text
                    wrapMode: Text.Wrap
                    lineHeight: 1.4
                }
                Text {
                    Layout.fillWidth: true
                    text: "各轮仍保留原蓝图权重，不会重新归一化。即使所有专项问题都完成，本场也始终标记为未完整，只形成部分面试证据。"
                    color: root.palette.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 12
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: "技术状态：incomplete / partial evidence"
                    color: root.palette.muted
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
                Text {
                    Layout.fillWidth: true
                    text: "专项结果不会改变 Practice mastery。需要完整岗位面试时，需先克隆源码并进入仓库根目录，再运行：python -m pip install -e \".[torch,dev]\""
                    color: root.palette.muted
                    wrapMode: Text.WrapAnywhere
                    font.pixelSize: 12
                }
                Text {
                    objectName: "interviewFallbackSourceEnvironmentLink"
                    Layout.fillWidth: true
                    text: "<a href=\"https://github.com/ComistryMo/llm_interview_lab/blob/main/docs/desktop-app.md\">查看源码环境说明</a>"
                    textFormat: Text.RichText
                    color: root.palette.accent
                    font.pixelSize: 12
                    onLinkActivated: Qt.openUrlExternally(link)
                }
                Text {
                    Layout.fillWidth: true
                    visible: useMaterial.checked
                    text: "材料：仅使用你勾选并同意的精确 ID / SHA；不会读取其他材料。"
                    color: root.palette.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 12
                }
            }
        }
        footer: DialogButtonBox {
            spacing: 8
            alignment: Qt.AlignRight
            Button {
                id: fallbackBackButton
                objectName: "nonCodingInterviewBackButton"
                text: "返回"
                focus: true
                onClicked: nonCodingInterviewDialog.reject()
            }
            Button {
                objectName: "nonCodingInterviewConfirmButton"
                text: "确认开始专项"
                highlighted: true
                enabled: !app.busy
                         && aiMode.currentValue !== "disabled"
                onClicked: {
                    if (aiMode.currentValue === "disabled") {
                        nonCodingInterviewDialog.close()
                        return
                    }
                    nonCodingInterviewDialog.close()
                    app.createNonCodingInterview(
                        role.currentValue,
                        seniority.currentValue,
                        difficulty.currentValue,
                        aiMode.currentValue,
                        useMaterial.checked ? material.currentValue : "",
                        useMaterial.checked ? consent.checked : false
                    )
                }
            }
        }
    }

    Dialog {
        id: finishDialog
        objectName: "interviewFinishDialog"
        modal: true
        anchors.centerIn: parent
        title: "结束本场面试？"
        width: Math.min(440, root.width - 48)
        height: 250
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: app.finishInterview()
        contentItem: Text {
            width: 360
            text: "已完成：" + (app.interview.completed_questions || 0)
                  + " / " + (app.interview.total_questions || 0)
                  + "\n未回答：" + (app.interview.unanswered_questions || 0)
                  + "\n已回答但未评分：" + (app.interview.unscored_questions || 0)
                  + "\n代码环节未完成：" + (app.interview.coding_incomplete || 0)
                  + "\n\n" + root.finishDialogMessage()
            color: root.palette.text
            wrapMode: Text.Wrap
        }
    }
}
