import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var app
    required property var palette
    property var theme: null
    readonly property bool dynamicInterview: app.interview.delivery_mode === "dynamic_ai"
    property bool showVoiceOptions: false
    property var activeQuestion: app.interview.question || null
    property var rubricScores: ({})
    property var aiPreview: ({"parts": [], "estimated_tokens": 0})
    property var planContext: ({"parts": [], "estimated_tokens": 0, "context_sha256": ""})
    // A Codex plan click connects the dedicated interviewer thread first.
    // Keep that intent so the first click continues into the context preview.
    property bool codexPlanPending: false
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
    // The context confirmation is a single, synchronous hand-off to the
    // controller.  Keep a local gate as well as ``app.busy`` so keyboard
    // activation and a mouse click in the same event loop cannot create two
    // sessions.
    property bool startingDynamicInterview: false
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
    onActiveQuestionKeyChanged: Qt.callLater(root.resetQuestionEditors)
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

    function resetQuestionEditors() {
        root.rubricScores = ({})
        root.answerDraft = ""
        root.pendingLockAnswer = ""
        evidence.text = ""
        followupAnswer.text = ""
        root.syncQuestionEditors()
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

    function openPersonalizedPlanContext() {
        if (root.startingDynamicInterview || app.busy)
            return
        root.planContext = app.dynamicInterviewContextPreview(
            role.currentValue,
            seniority.currentValue,
            difficulty.currentValue,
            useMaterial.checked ? material.currentValue : "",
            useMaterial.checked ? consent.checked : false
        )
        if ((root.planContext.parts || []).length > 0)
            planContextDialog.open()
    }

    // Keep long material titles and hashes out of the layout's primary row.
    // The context preview is a confirmation surface, not a raw diagnostic
    // dump: show a short human label first and put the integrity hash on its
    // own bounded line.
    function previewPartLabel(part) {
        var id = String((part && part.id) || "")
        var value = String((part && (part.label || part.id)) || "")
        // The preview is a consent surface, not a raw context dump.  Keep
        // stable human labels in the first line and put sensitive/hash
        // metadata on their own bounded lines below it.
        if (id === "policy")
            return "面试流程与 AI 使用规则"
        if (id === "question")
            return "本轮问题、岗位技能与评分要求"
        if (id === "candidate_answer")
            return "你已提交并锁定的回答"
        if (id === "interview_contract" || id === "blueprint")
            return "岗位技能与面试流程"
        if (id === "profile_context")
            return "求职意向与能力自评"
        // Match the semantic marker itself instead of relying on a particular
        // full-width/ASCII parenthesis spelling.  Values can come through a
        // QVariant bridge where punctuation is normalized.
        var hashMarker = value.indexOf("SHA-256")
        if (hashMarker >= 0)
            value = value.slice(0, hashMarker)
        var consentMarker = value.indexOf("本场确认后发送")
        if (consentMarker >= 0)
            value = value.slice(0, consentMarker)
        value = value.replace(/[（(\s]+$/, "").trim()
        if (id.indexOf("material:") === 0) {
            var colon = value.indexOf(":")
            if (colon < 0)
                colon = value.indexOf("：")
            if (colon >= 0)
                value = value.slice(colon + 1).trim()
            return "授权材料：" + value
        }
        return value.trim()
    }

    function previewPartSha(part) {
        // The context digest shown at the bottom is the integrity proof for
        // the whole request.  Per-part hashes are useful only for an
        // explicitly authorised material; showing hashes for policy and role
        // metadata makes this confirmation surface look like a log dump.
        var id = String((part && part.id) || "")
        if (id.indexOf("material:") !== 0)
            return ""
        var value = String((part && part.sha256) || "")
        if (!value) {
            var label = String((part && part.label) || "")
            var match = label.match(/SHA-256\s+([0-9a-fA-F]+)/)
            value = match ? match[1] : ""
        }
        return value ? "已校验 · SHA-256 " + value.slice(0, 8) : ""
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
        function onAiStateChanged() {
            // Continue the original button action once the Codex interviewer
            // thread is ready; do not make the user click a second time.
            if (root.codexPlanPending
                    && root.visible
                    && aiMode.currentValue === "codex"
                    && app.aiStatusVariant === "connected") {
                root.codexPlanPending = false
                Qt.callLater(root.openPersonalizedPlanContext)
            }
        }
        function onInterviewPlanReady() {
            // The legacy full-plan signal is retained for old API clients,
            // but it is intentionally not rendered here.  A dynamic session
            // starts with one local opening question; exposing a frozen list
            // would contradict the one-question-at-a-time contract and can
            // leave users waiting for a provider response.
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
        anchors.fill: parent
        anchors.margins: root.compactInterviewLayout ? 12 : 26
        spacing: 12
        clip: true

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
                    ComboBox { visible: leftPanel.setupVisible; id: role; objectName: "interviewRoleSelector"; width: parent.width; textRole: "title"; valueRole: "id"; model: app.roles; currentIndex: -1; onActivated: root.refreshConfiguration() }
                    Text { visible: leftPanel.setupVisible; text: "求职阶段"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: seniority; objectName: "interviewSenioritySelector"; width: parent.width; model: [{id:"intern", label:"实习"}, {id:"new_grad", label:"校招"}, {id:"mid", label:"有经验"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.refreshConfiguration() }
                    Text { visible: leftPanel.setupVisible; text: "难度"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox { visible: leftPanel.setupVisible; id: difficulty; objectName: "interviewDifficultySelector"; width: parent.width; model: [{id:"easy", label:"基础"}, {id:"medium", label:"标准"}, {id:"hard", label:"高压"}]; textRole: "label"; valueRole: "id"; currentIndex: 1; onActivated: root.refreshConfiguration() }
                    Text {
                        objectName: "interviewDifficultyHint"
                        visible: leftPanel.setupVisible
                        width: parent.width
                        text: {
                            if (!role.currentValue)
                                return "请选择这次准备面试的岗位。"
                            if (aiMode.currentValue !== "disabled")
                                return "难度用于调整 AI 追问强度；不要求该档位有完整固定题单。"
                            return "选择面试官后即可开始；不连接 AI 仍可继续刷题。"
                        }
                        color: root.palette.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text { visible: leftPanel.setupVisible; text: "面试官"; color: root.palette.muted; font.pixelSize: 12 }
                    ComboBox {
                        visible: leftPanel.setupVisible
                        id: aiMode
                        objectName: "interviewAiModeSelector"
                        width: parent.width
                        model: [{id:"disabled", label:"手动 / 无 AI"}, {id:"provider", label:"普通 LLM API"}, {id:"codex", label:"Codex"}]
                        textRole: "label"
                        valueRole: "id"
                        onActivated: {
                            if (currentValue === "codex"
                                    && !app.codexAvailable
                                    && !app.codexProbeRunning)
                                app.refreshCodexAvailability()
                        }
                    }
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
                        objectName: "personalizedInterviewCodexStatus"
                        text: app.aiStatusVariant === "connected"
                              ? "Codex 面试官已连接。确认后立即进入本地开场题；提交回答后再由 Codex 根据证据逐步追问。"
                              : (app.codexAvailable
                                 ? "确认后会先进入本地开场题；提交回答时再调用 Codex。你也可以先在设置中选择模型和推理强度。"
                                 : "尚未发现 Codex。请在 AI 连接页检查安装/登录状态；普通 LLM API 也可单独使用。")
                        color: app.aiStatusVariant === "connected" ? root.palette.success : root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    ColumnLayout {
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue === "codex"
                        spacing: 8
                        Text {
                            objectName: "personalizedInterviewCodexPreferences"
                            Layout.fillWidth: true
                            text: "本场 Codex：" + (app.codexModel || "默认模型")
                                  + " · 推理强度：" + (app.codexReasoningEffort || "默认")
                            color: root.palette.muted
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                        LabButton {
                            objectName: "openCodexPreferencesFromInterview"
                            theme: root.theme
                            variant: "secondary"
                            text: "设置模型与推理强度"
                            onClicked: app.navigate("settings")
                        }
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
                        text: "使用求职材料（可选）"
                        contentItem: Text {
                            text: useMaterial.text
                            font: useMaterial.font
                            color: useMaterial.enabled ? root.palette.text : root.palette.muted
                            leftPadding: useMaterial.indicator.width + useMaterial.spacing
                            wrapMode: Text.Wrap
                            verticalAlignment: Text.AlignVCenter
                        }
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
                    Text {
                        objectName: "personalizedInterviewMaterialAccessNotice"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && useMaterial.checked
                                 && material.currentIndex >= 0
                                 && !app.materials[material.currentIndex].ai_access
                        text: "这份材料尚未允许 AI 使用。点击下方按钮后，系统会在本机重新提取 PDF/DOCX 文本并绑定当前文件 SHA；提取失败时仍保持本地保存。"
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Button {
                        objectName: "openMaterialsForInterviewAuthorization"
                        visible: leftPanel.setupVisible
                                 && useMaterial.checked
                                 && material.currentIndex >= 0
                                 && !app.materials[material.currentIndex].ai_access
                        text: "允许此材料供 AI 使用"
                        flat: true
                        enabled: !app.busy
                        onClicked: app.setMaterialAiAccess(material.currentValue, true)
                    }
                    CheckBox {
                        id: consent
                        width: parent.width
                        visible: leftPanel.setupVisible && useMaterial.checked
                        text: "允许本场面试使用所选材料"
                        contentItem: Text {
                            text: consent.text
                            font: consent.font
                            color: root.palette.text
                            leftPadding: consent.indicator.width + consent.spacing
                            wrapMode: Text.Wrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Text {
                        objectName: "personalizedInterviewConsentNotice"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && useMaterial.checked
                                 && material.currentIndex >= 0
                                 && app.materials[material.currentIndex].ai_access
                                 && !consent.checked
                        text: "请勾选上方授权后，Codex 才会读取这份材料；未勾选不会发送。"
                        color: root.palette.warning
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "interviewConfigurationMessage"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && aiMode.currentValue !== "provider"
                                 && aiMode.currentValue !== "codex"
                                 && root.configuration.available === false
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
                                 && aiMode.currentValue !== "provider"
                                 && aiMode.currentValue !== "codex"
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
                                 && aiMode.currentValue !== "provider"
                                 && aiMode.currentValue !== "codex"
                                 && (root.configuration.missing_environment || []).indexOf("pytorch") >= 0
                        text: "<a href=\"https://github.com/ComistryMo/llm_interview_lab/blob/main/docs/desktop-app.md\">查看源码环境说明</a>"
                        textFormat: Text.RichText
                        color: root.palette.accent
                        font.pixelSize: 11
                        onLinkActivated: Qt.openUrlExternally(link)
                    }
                    LabButton {
                        objectName: "startConfiguredInterview"
                        theme: root.theme
                        variant: "primary"
                        width: parent.width
                        visible: leftPanel.setupVisible
                        text: app.busy ? "正在进入面试……" : "开始动态模拟面试"
                        enabled: !!role.currentValue
                                 && !app.busy
                                 && ((aiMode.currentValue === "provider"
                                      && planConnection.currentIndex >= 0
                                      && root.providerIsReady(planConnection.currentValue))
                                      || aiMode.currentValue === "codex")
                                 && (!useMaterial.checked
                                     || (material.currentIndex >= 0
                                         && app.materials[material.currentIndex].ai_access
                                         && consent.checked))
                        // Confirm only the explicit first-turn context. Future
                        // questions are generated after the current answer.
                        onClicked: root.openPersonalizedPlanContext()
                    }
                    Text {
                        objectName: "dynamicInterviewStatus"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && aiMode.currentValue !== "disabled"
                                 && app.interviewPlanPreview.status === "starting"
                        text: app.interviewPlanPreview.user_message || "正在进入面试……"
                        color: root.palette.accent
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "dynamicInterviewError"
                        width: parent.width
                        visible: leftPanel.setupVisible
                                 && app.interviewPlanPreview.status === "error"
                        text: (app.interviewPlanPreview.user_message || "第一问生成失败。")
                              + "\n" + (app.interviewPlanPreview.recommended_action || "请检查连接后重试。")
                        color: root.palette.danger
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                    }
                    Text {
                        objectName: "personalizedInterviewAlphaScope"
                        width: parent.width
                        visible: false
                        text: "AI 会依据岗位蓝图、canonical skills、求职级别和难度生成结构化问题；材料是可选上下文。Coding 环节只使用当前环境可运行的已验证本地题，不满足时会在计划中明确省略。"
                        color: root.palette.muted
                        wrapMode: Text.Wrap
                        font.pixelSize: 11
                    }
                    Text {
                        objectName: "dynamicInterviewScope"
                        width: parent.width
                        visible: leftPanel.setupVisible && aiMode.currentValue !== "disabled"
                        text: "确认后先自我介绍。提交回答后，AI 读取当前问题、已锁定回答、岗位与难度及本次确认的材料，再生成一条追问。当前动态模式尚未自动衔接代码题。"
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
                                + (root.dynamicInterview
                                   ? "\n已展示 " + (app.interview.total_questions || 0) + " 问 · 后续逐问生成"
                                   : "\n进度  " + (app.interview.completed_questions || 0)
                                     + " / " + (app.interview.total_questions || 0))
                              : "暂无进行中的面试"
                        color: root.palette.muted
                        font.family: root.theme ? root.theme.uiFontFamily : ""
                        font.pixelSize: root.theme ? root.theme.fontCaption : 12
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
            Layout.minimumWidth: 0
            Layout.fillHeight: true
            clip: true
            cardColor: root.palette.surface
            borderColor: root.palette.border
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
                    theme: root.theme
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
                    objectName: "interviewTimerPill"
                    theme: root.theme
                    visible: !!app.interview.interview_id
                    text: app.interview.status === "active"
                          ? root.timerText(app.interview.remaining_seconds)
                          : root.statusText(app.interview.status)
                    tone: app.interview.status === "active" ? root.palette.warning : root.palette.muted
                }
                LabButton {
                    theme: root.theme
                    variant: "ghost"
                    visible: app.interview.status === "active" || app.interview.status === "paused"
                    text: app.interview.status === "paused" ? "恢复计时" : "暂停"
                    enabled: !app.busy
                    onClicked: app.interview.status === "paused"
                               ? app.resumeInterview() : pauseInterviewDialog.open()
                }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: root.palette.border }
                ScrollView {
                id: questionScroll
                objectName: "interviewQuestionScroll"
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
                    Text {
                        width: parent.width
                        text: activeQuestion ? activeQuestion.prompt : "选择岗位、求职阶段与难度，先完成自我介绍，再由 AI 根据回答逐步追问。"
                        color: root.palette.text
                        font.family: root.theme ? root.theme.uiFontFamily : ""
                        font.pixelSize: root.theme ? root.theme.fontBody : 14
                        wrapMode: Text.Wrap
                        textFormat: Text.MarkdownText
                        lineHeight: 1.4
                    }
                    LabTextArea {
                        id: answer
                        objectName: "interviewAnswerEditor"
                        theme: root.theme
                        width: parent.width
                        height: root.compactInterviewLayout ? 140 : 180
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                        text: root.answerLocked ? (app.interview.answer_text || "") : root.answerDraft
                        readOnly: root.answerLocked || !root.interviewCanEdit
                        onTextChanged: if (!root.answerLocked && !root.syncingQuestionEditors) root.answerDraft = text
                        placeholderText: root.answerLocked ? "回答已锁定" : !root.interviewCanEdit ? "面试已暂停或结束" : "输入你的回答……"
                    }
                    LabButton {
                        theme: root.theme
                        variant: "ghost"
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && !root.answerLocked
                        text: root.showVoiceOptions ? "收起语音回答" : "语音回答（可选）"
                        onClicked: root.showVoiceOptions = !root.showVoiceOptions
                    }
                    LabCard {
                        objectName: "interviewVoiceCard"
                        visible: !!activeQuestion && activeQuestion.kind !== "coding"
                                 && !root.answerLocked && root.interviewCanEdit && root.showVoiceOptions
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
                        height: phaseActions.implicitHeight + 24
                        radius: 8
                        color: root.palette.surfaceAlt
                        border.color: root.answerLocked ? root.palette.accent : root.palette.border
                        GridLayout {
                            id: phaseActions
                            anchors.fill: parent
                            anchors.margins: 12
                            columns: width < 600 ? 1 : 2
                            rowSpacing: 12
                            columnSpacing: 16
                            Text {
                                objectName: "interviewAnswerActionHint"
                                text: root.answerLocked
                                      ? (root.dynamicInterview ? "回答已保存。请点击下方按钮，让 AI 根据本轮回答继续提问。" : "回答已锁定；先记录证据，再选择评分来源。")
                                      : (root.dynamicInterview ? "完成回答后提交，再由 AI 根据你的回答继续提问。" : "完成回答后提交并锁定，评分维度才会显示。")
                                color: root.palette.muted
                                font.family: root.theme ? root.theme.uiFontFamily : ""
                                font.pixelSize: root.theme ? root.theme.fontCaption : 12
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                            }
                            LabButton {
                                objectName: "lockInterviewAnswer"
                                theme: root.theme
                                variant: "primary"
                                topInset: 0
                                bottomInset: 0
                                visible: !root.answerLocked
                                text: "提交并锁定回答"
                                enabled: root.interviewCanEdit && answer.text.trim().length > 0 && !app.busy
                                Layout.alignment: Qt.AlignRight
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
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted && !root.dynamicInterview
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
                                 && root.answerLocked && !app.interview.answer_corrupted && !root.dynamicInterview
                        text: "回答证据 · 必填"
                        color: root.palette.text
                        font.bold: true
                        font.pixelSize: 13
                        width: parent.width
                    }
                    LabTextArea {
                        id: evidence
                        objectName: "interviewEvidenceEditor"
                        theme: root.theme
                        width: parent.width
                        height: 86
                        visible: !!activeQuestion && activeQuestion.kind !== "coding" && root.answerLocked && !app.interview.answer_corrupted && !root.dynamicInterview
                        enabled: root.interviewCanEdit
                        placeholderText: root.interviewCanEdit ? "请引用回答中的具体证据（必填）" : "面试已暂停或结束"
                    }
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
                                 && app.interview.ai_mode === "provider"
                                 && providerConnection.currentIndex >= 0
                                 && !root.providerIsReady(providerConnection.currentValue)
                        width: parent.width
                        text: root.dynamicInterview
                              ? "当前连接尚未测试通过。请到“AI 连接”完成测试，再返回生成下一问。"
                              : "当前连接尚未测试通过。请到“AI 连接”测试后再请求评估，或改用人工评分。"
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
                        text: root.dynamicInterview
                              ? "还没有可用的已测试连接。请到“AI 连接”保存并测试服务，再返回继续面试。"
                              : "还没有可用的已测试连接；可以去 AI 连接页配置，或直接记录人工评分。"
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
                            visible: !root.dynamicInterview
                            text: "记录自评结果"
                            enabled: root.interviewCanEdit && root.rubricComplete() && evidence.text.trim().length > 0
                                     && !app.busy && !app.interview.assessment_recorded
                            onClicked: app.answerInterviewDetailed(answer.text, JSON.stringify(root.rubricScores), evidence.text)
                        }
                        LabButton {
                            theme: root.theme
                            variant: "primary"
                            topInset: 0
                            bottomInset: 0
                            visible: app.interview.ai_mode === "provider"
                            enabled: root.interviewCanEdit && providerConnection.currentIndex >= 0
                                     && root.providerIsReady(providerConnection.currentValue)
                                     && !app.busy
                                     && !app.interview.assessment_recorded
                            text: root.dynamicInterview ? "生成下一问" : "预览 AI 评分上下文"
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
                                      && app.aiStatusVariant !== "connected"
                            enabled: root.interviewCanEdit && !app.busy && !app.interview.assessment_recorded
                            text: "连接 Codex 面试官"
                            onClicked: app.connectCodex("interviewer")
                        }
                        LabButton {
                            theme: root.theme
                            variant: "primary"
                            topInset: 0
                            bottomInset: 0
                            objectName: "continueCodexInterview"
                            visible: app.interview.ai_mode === "codex" && app.aiStatusVariant === "connected"
                            enabled: root.interviewCanEdit && !app.busy && !app.interview.assessment_recorded
                            text: root.dynamicInterview ? "让 Codex 继续提问" : "请求 Codex 评分"
                            onClicked: root.previewAI("codex", "")
                        }
                        LabButton {
                            objectName: "stopCodexInterviewRequest"
                            theme: root.theme
                            variant: "secondary"
                            visible: app.interview.ai_mode === "codex" && app.busy
                                     && (app.interview.ai_assessment_state === "streaming"
                                         || app.interview.ai_assessment_state === "retrying")
                            text: "停止请求"
                            onClicked: app.cancelCodex()
                        }
                        LabButton {
                            theme: root.theme
                            variant: "secondary"
                            visible: app.interview.ai_mode === "codex"
                                     && app.interview.ai_assessment_state === "error" && !app.busy
                            text: "检查 Codex 设置"
                            onClicked: app.navigate("settings")
                        }
                    }
                    Text {
                        visible: !!app.interview.ai_assessment_state
                                 && app.interview.ai_assessment_state !== "complete"
                        width: parent.width
                        text: app.interview.ai_assessment_state === "streaming"
                              ? (root.dynamicInterview ? "AI 正在阅读你的回答并生成下一问……" : "AI 正在根据回答生成评分证据……")
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
                        LabTextArea { id: followupAnswer; objectName: "interviewFollowupEditor"; theme: root.theme; width: parent.width; height: 100; enabled: root.interviewCanEdit; placeholderText: root.interviewCanEdit ? "回答这一个追问" : "面试已暂停或结束" }
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
                        LabTextArea {
                            id: codingEditor
                            theme: root.theme
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
        objectName: "interviewAnswerContextDialog"
        modal: true
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.45) }
        anchors.centerIn: parent
        width: Math.min(560, Math.max(360, root.width - 48))
        height: Math.min(420, Math.max(300, root.height - 40))
        padding: 20
        title: "上下文预览（只读）"
        standardButtons: Dialog.NoButton
        header: Item {
            implicitHeight: 46
            Text {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                verticalAlignment: Text.AlignVCenter
                text: contextDialog.title
                color: root.palette.text
                font.pixelSize: 20
                font.bold: true
                elide: Text.ElideRight
            }
        }
        background: Rectangle {
            color: root.palette.surface
            radius: 12
            border.color: root.palette.border
            border.width: 1
        }
        footer: DialogButtonBox {
            spacing: 8
            alignment: Qt.AlignRight
            background: Rectangle { color: root.palette.surface }
            LabButton {
                theme: root.theme
                variant: "ghost"
                text: "取消"
                onClicked: contextDialog.reject()
            }
            LabButton {
                objectName: "confirmInterviewAnswerContext"
                theme: root.theme
                variant: "primary"
                topInset: 0
                bottomInset: 0
                text: "确认发送"
                onClicked: contextDialog.accept()
            }
        }
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
                text: "只会发送下面标记为“发送”的内容。取消后不会发送任何内容。"
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "以下列出本次请求的内容范围；授权材料另显示短 SHA 以供核对。"
                color: root.palette.muted
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            ListView {
                id: contextPartsView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: root.aiPreview.parts || []
                delegate: Item {
                    required property var modelData
                    width: contextPartsView.width
                    height: 30 + ((modelData.sensitive || root.previewPartSha(modelData) !== "") ? 18 : 0)

                    RowLayout {
                        width: parent.width
                        height: 30
                        spacing: 8
                        StatusPill {
                            Layout.preferredWidth: 56
                            Layout.minimumWidth: 56
                            Layout.preferredHeight: 22
                            Layout.alignment: Qt.AlignTop
                            compact: true
                            showDot: false
                            text: modelData.selected ? "发送" : "不发送"
                            tone: modelData.selected ? root.palette.accent : root.palette.muted
                        }
                        Text {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.alignment: Qt.AlignVCenter
                            text: root.previewPartLabel(modelData)
                            color: root.palette.text
                            wrapMode: Text.NoWrap
                            maximumLineCount: 1
                            elide: Text.ElideRight
                        }
                    }
                    Text {
                        visible: modelData.sensitive || root.previewPartSha(modelData) !== ""
                        x: 64
                        y: 27
                        width: Math.max(0, parent.width - 64)
                        text: modelData.sensitive
                              ? (root.previewPartSha(modelData) || "本场确认后发送")
                              : root.previewPartSha(modelData)
                        color: modelData.sensitive ? root.palette.warning : root.palette.muted
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: contextPartsView.count === 0
                    text: "没有可发送的上下文"
                    color: root.palette.muted
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
        Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.45) }
        anchors.centerIn: parent
        width: Math.min(600, Math.max(380, root.width - 40))
        height: Math.min(460, Math.max(320, root.height - 36))
        padding: 20
        title: "确认设置并进入面试"
        standardButtons: Dialog.NoButton
        property bool submitting: false
        onOpened: {
            submitting = false
            root.startingDynamicInterview = false
        }
        onRejected: {
            submitting = false
            root.startingDynamicInterview = false
        }
        header: Item {
            implicitHeight: 52
            Text {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                verticalAlignment: Text.AlignVCenter
                text: planContextDialog.title
                color: root.palette.text
                font.pixelSize: 21
                font.bold: true
                elide: Text.ElideRight
            }
        }
        background: Rectangle {
            color: root.palette.surface
            radius: 12
            border.color: root.palette.border
            border.width: 1
        }
        footer: DialogButtonBox {
            implicitHeight: 64
            spacing: 8
            alignment: Qt.AlignRight
            background: Rectangle {
                color: root.palette.surface
                border.width: 0
            }
            Button {
                id: cancelPlanContextButton
                text: "取消"
                flat: true
                Layout.preferredWidth: 76
                Layout.preferredHeight: 40
                background: Rectangle {
                    radius: 8
                    color: cancelPlanContextButton.hovered
                           ? root.palette.surfaceAlt
                           : root.palette.surface
                }
                contentItem: Text {
                    text: cancelPlanContextButton.text
                    color: root.palette.text
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: planContextDialog.reject()
            }
            Button {
                id: confirmPlanContextButton
                text: "确认进入面试"
                highlighted: true
                enabled: !planContextDialog.submitting && !app.busy
                Layout.preferredWidth: 140
                Layout.preferredHeight: 40
                background: Rectangle {
                    radius: 8
                    color: confirmPlanContextButton.enabled
                           ? root.palette.accent
                           : root.palette.border
                }
                contentItem: Text {
                    text: confirmPlanContextButton.text
                    color: confirmPlanContextButton.enabled ? "white" : root.palette.muted
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: planContextDialog.accept()
            }
        }
        onAccepted: {
            if (planContextDialog.submitting)
                return
            planContextDialog.submitting = true
            root.startingDynamicInterview = true
            app.startDynamicPersonalizedInterview(
                role.currentValue,
                seniority.currentValue,
                difficulty.currentValue,
                aiMode.currentValue === "codex" ? "codex" : planConnection.currentValue,
                useMaterial.checked ? material.currentValue : "",
                useMaterial.checked ? consent.checked : false,
                root.planContext.context_sha256 || ""
            )
            // The current first-turn use case is synchronous: it persists the
            // real opening question before returning.  Release the local gate
            // after the call so a validation error remains retryable as well.
            root.startingDynamicInterview = false
        }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                Layout.fillWidth: true
                text: "确认后立即进入开场题。面试流程、岗位技能、难度和你明确授权的材料会作为后续 AI 请求的上下文；不会在开始时等待模型，也不会提前生成整场计划。"
                color: root.palette.text
                wrapMode: Text.Wrap
            }
            Text {
                Layout.fillWidth: true
                text: "开场题由本地面试流程提供。提交回答后，Codex / 普通 LLM 才会根据你的证据评分并生成下一问。"
                color: root.palette.muted
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            ListView {
                id: planContextPartsView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: root.planContext.parts || []
                delegate: Item {
                    required property var modelData
                    width: planContextPartsView.width
                    // Do not use StatusPill here.  Its implicit width is
                    // intentionally content-driven and can paint over the
                    // label when a narrow dialog applies a fixed layout
                    // width.  This consent list uses explicit geometry.
                    height: modelData.sensitive || root.previewPartSha(modelData) !== "" ? 54 : 42
                    Rectangle {
                        x: 2
                        y: 10
                        width: 8
                        height: 8
                        radius: 4
                        color: modelData.selected ? root.palette.accent : root.palette.muted
                    }
                    Text {
                        x: 20
                        y: 2
                        width: Math.max(0, parent.width - 20)
                        height: 24
                        text: (modelData.selected ? "发送 · " : "不发送 · ")
                              + root.previewPartLabel(modelData)
                        color: root.palette.text
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.NoWrap
                        elide: Text.ElideRight
                    }
                    Text {
                        visible: modelData.sensitive || root.previewPartSha(modelData) !== ""
                        x: 20
                        y: 27
                        width: Math.max(0, parent.width - 20)
                        height: 18
                        text: modelData.sensitive
                              ? (root.previewPartSha(modelData) || "本场确认后发送")
                              : root.previewPartSha(modelData)
                        color: modelData.sensitive ? root.palette.warning : root.palette.muted
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: planContextPartsView.count === 0
                    text: "没有可发送的上下文"
                    color: root.palette.muted
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
                                         || modelData.source.kind === "process_opening"
                                         ? root.palette.accent : root.palette.border
                            Text {
                                width: parent.width
                                text: modelData.source.kind === "catalog_problem"
                                      ? "已验证题库 Coding"
                                      : modelData.source.kind === "process_opening"
                                        ? "本地流程开场题"
                                        : "AI 生成 · " + root.roundTypeText(modelData.kind)
                                      + " · " + modelData.timebox_minutes + " 分钟"
                                color: modelData.source.kind === "catalog_problem"
                                       || modelData.source.kind === "process_opening"
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
