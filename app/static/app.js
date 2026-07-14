// app/static/app.js

document.addEventListener("DOMContentLoaded", () => {
    // Configurações e Estado do App
    const session_id = "sess_" + Math.random().toString(36).substring(2, 9);
    let systemStatus = {};
    let creditScoreData = {};
    let alertsList = [];
    let graphData = { nodes: [], edges: [] };
    let overviewChart = null;

    // Elementos DOM
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const statusIndicator = document.getElementById("status-indicator");
    const statusText = document.getElementById("status-text");
    const aiModeBadge = document.getElementById("ai-mode-badge");

    // ==========================================
    // 1. GERENCIAMENTO DE ABAS (TABS TRANSITION)
    // ==========================================
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            // Troca classes active nos botões
            navButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Exibe o painel correspondente com animação
            tabPanels.forEach(panel => {
                panel.classList.remove("active");
                if (panel.id === `tab-${targetTab}`) {
                    panel.classList.add("active");
                }
            });

            // Ações específicas de carregamento de abas
            if (targetTab === "overview") {
                loadOverviewData();
            } else if (targetTab === "alerts") {
                loadAlerts();
            } else if (targetTab === "credit") {
                loadCreditProfile();
            } else if (targetTab === "graph") {
                loadGraphNetwork();
            } else if (targetTab === "chat") {
                loadChatHistory();
            }
        });
    });

    // ==========================================
    // 2. TOAST NOTIFICATIONS (TRANSIÇÃO ELÁSTICA)
    // ==========================================
    const toastContainer = document.getElementById("toast-container");
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "ℹ️";
        if (type === "success") icon = "✅";
        if (type === "error") icon = "❌";
        
        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        toastContainer.appendChild(toast);

        // Força reflow para ativar animação
        setTimeout(() => toast.classList.add("show"), 10);

        // Remove após 4 segundos
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    }

    // ==========================================
    // 3. ANIMAÇÃO DE CONTADORES NUMÉRICOS
    // ==========================================
    function animateCounter(elementId, targetVal, isFloat = false, duration = 1200) {
        const el = document.getElementById(elementId);
        if (!el) return;

        let start = 0;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function: easeOutExpo
            const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
            const currentVal = start + (targetVal - start) * easeProgress;

            el.innerText = isFloat ? currentVal.toFixed(2) : Math.floor(currentVal).toString();

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        requestAnimationFrame(update);
    }

    // ==========================================
    // 4. GAUGE DO CREDIT SCORE (SWEEP RADIAL)
    // ==========================================
    function animateGauge(score) {
        const circle = document.getElementById("gauge-fill-circle");
        const scoreVal = document.getElementById("gauge-score");
        if (!circle || !scoreVal) return;

        // Comprimento da circunferência: 2 * PI * r = 2 * 3.14 * 80 ≈ 502
        const maxOffset = 502;
        // Mapeia score 0-100 para offset de 502 a 0 (onde 0 offset = preenchido)
        const targetOffset = maxOffset - (score / 100) * maxOffset;

        // Animação numérica do score central
        animateCounter("gauge-score", score, false, 1200);

        // Animação SVG sweep radial
        circle.style.strokeDashoffset = targetOffset;
    }

    // ==========================================
    // 5. CARREGAMENTO DOS DADOS DO OVERVIEW
    // ==========================================
    async function loadOverviewData() {
        try {
            // Busca status
            const statusRes = await fetch("/api/system/status");
            systemStatus = await statusRes.json();
            
            // Atualiza sidebar
            statusIndicator.className = `status-indicator ${systemStatus.status}`;
            statusText.innerText = systemStatus.status === "healthy" ? "Online" : "Instável";
            aiModeBadge.innerText = `${systemStatus.ai_mode.toUpperCase()} Mode`;

            // Busca score recente
            const scoreRes = await fetch("/api/credit/score");
            creditScoreData = await scoreRes.json();

            // Roda animações de contadores
            animateCounter("kpi-score-val", creditScoreData.score || 0);
            document.getElementById("kpi-rating-val").innerText = `Rating: ${creditScoreData.rating || "N/A"}`;
            
            animateCounter("kpi-dscr-val", creditScoreData.dscr || 0, true);
            animateCounter("kpi-dso-val", creditScoreData.dso_days || 30.0, true);

            // Busca quantidade de alertas ativos
            const alertsRes = await fetch("/api/alerts?status=open");
            const alertsData = await alertsRes.json();
            animateCounter("kpi-alerts-val", alertsData.total || 0);
            
            // Atualiza feeds de alertas recentes com fade-in
            const alertsListContainer = document.getElementById("recent-alerts-list");
            alertsListContainer.innerHTML = "";
            
            if (alertsData.items && alertsData.items.length > 0) {
                alertsData.items.slice(0, 4).forEach((alert, index) => {
                    const alertCard = document.createElement("div");
                    alertCard.className = `alert-item-card ${alert.severity}`;
                    alertCard.style.animationDelay = `${index * 50}ms`;
                    alertCard.innerHTML = `
                        <div class="alert-item-content">
                            <div class="alert-item-title">${alert.description}</div>
                            <div class="alert-item-desc">Severidade: ${alert.severity.toUpperCase()} | Status: ${alert.status.toUpperCase()}</div>
                        </div>
                        <span class="badge ${alert.severity === 'critical' ? 'badge-red' : (alert.severity === 'high' ? 'badge-orange' : 'badge-blue')}">
                            Score: ${alert.score_value.toFixed(0)}
                        </span>
                    `;
                    alertsListContainer.appendChild(alertCard);
                });
            } else {
                alertsListContainer.innerHTML = '<p class="empty-state">Nenhum alerta de risco pendente.</p>';
            }

            // Plota gráficos no canvas
            renderOverviewChart(creditScoreData);
        } catch (e) {
            loggingError("Erro ao carregar visão geral", e);
        }
    }

    function renderOverviewChart(scoreData) {
        const ctx = document.getElementById("overview-chart");
        if (!ctx) return;

        if (overviewChart) {
            overviewChart.destroy();
        }

        // Dados de radar de risco com base nos scores calculados
        const dscr_val = scoreData.dscr ? Math.min((scoreData.dscr / 2.0) * 100, 100) : 0;
        const current_val = scoreData.current_ratio ? Math.min((scoreData.current_ratio / 2.0) * 100, 100) : 0;
        const profit_val = scoreData.net_profit_margin ? Math.min((scoreData.net_profit_margin / 0.2) * 100, 100) : 0;
        const dso_val = scoreData.dso_days ? Math.max(100 - (scoreData.dso_days / 90) * 100, 0) : 100;
        const concentration_val = scoreData.ar_concentration ? Math.max(100 - (scoreData.ar_concentration * 100), 0) : 100;

        overviewChart = new Chart(ctx, {
            type: "radar",
            data: {
                labels: ["DSCR", "Liquidez", "Margem", "DSO (Inverso)", "Diversificação"],
                datasets: [{
                    label: "Saúde Financeira PME",
                    data: [dscr_val, current_val, profit_val, dso_val, concentration_val],
                    backgroundColor: "rgba(147, 51, 234, 0.2)",
                    borderColor: "rgba(147, 51, 234, 0.8)",
                    borderWidth: 2,
                    pointBackgroundColor: "rgba(147, 51, 234, 1)"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: "rgba(255, 255, 255, 0.1)" },
                        grid: { color: "rgba(255, 255, 255, 0.1)" },
                        pointLabels: { color: "#94a3b8", font: { size: 10 } },
                        ticks: { display: false },
                        min: 0,
                        max: 100
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // ==========================================
    // 6. ABA DE ALERTAS (SCAN & TABLE STAGGER)
    // ==========================================
    const btnScan = document.getElementById("btn-scan");
    const filterSeverity = document.getElementById("filter-severity");
    const filterStatus = document.getElementById("filter-status");
    const alertsTbody = document.getElementById("alerts-tbody");

    async function loadAlerts() {
        const severity = filterSeverity.value;
        const status = filterStatus.value;
        
        let url = `/api/alerts?limit=50`;
        if (severity) url += `&severity=${severity}`;
        if (status) url += `&status=${status}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            
            alertsTbody.innerHTML = "";
            if (data.items && data.items.length > 0) {
                data.items.forEach((alert, index) => {
                    const row = document.createElement("tr");
                    // Adiciona delay para animação stagger por linha
                    row.style.animation = `fadeInTab 0.3s ease-out forwards`;
                    row.style.animationDelay = `${index * 40}ms`;
                    row.style.opacity = "0";

                    const dateStr = new Date(alert.created_at).toLocaleDateString("pt-BR");
                    const severityClass = alert.severity === 'critical' ? 'badge-red' : (alert.severity === 'high' ? 'badge-orange' : 'badge-blue');
                    
                    row.innerHTML = `
                        <td>${dateStr}</td>
                        <td><span class="badge badge-purple">${alert.alert_type}</span></td>
                        <td><span class="badge ${severityClass}">${alert.severity.toUpperCase()}</span></td>
                        <td>${alert.description}</td>
                        <td style="font-weight:600;">${alert.score_value.toFixed(1)}</td>
                        <td>
                            ${alert.status === 'open' 
                              ? `<button class="btn btn-small btn-secondary btn-resolve-trigger" data-id="${alert.id}">Revisar</button>` 
                              : `<span class="badge badge-green">${alert.status}</span>`}
                        </td>
                    `;
                    alertsTbody.appendChild(row);
                });

                // Adiciona listeners para os botões de revisão
                document.querySelectorAll(".btn-resolve-trigger").forEach(btn => {
                    btn.addEventListener("click", () => {
                        openResolveModal(btn.getAttribute("data-id"));
                    });
                });
            } else {
                alertsTbody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum alerta registrado com os filtros atuais.</td></tr>';
            }
        } catch (e) {
            showToast("Erro ao buscar alertas", "error");
        }
    }

    // Varredura de Risco
    btnScan.addEventListener("click", async () => {
        btnScan.disabled = True;
        btnScan.innerText = "Executando Varredura...";
        showToast("Iniciando varredura contábil e de faturas...", "info");

        try {
            const res = await fetch("/api/alerts/scan", { method: "POST" });
            const data = await res.json();
            showToast(`Varredura concluída! ${data.alerts_created} novos alertas identificados.`, "success");
            loadAlerts();
        } catch (e) {
            showToast("Falha ao rodar varredura", "error");
        } finally {
            btnScan.disabled = False;
            btnScan.innerText = "Disparar Varredura de Risco";
        }
    });

    // Modal de Resolução
    const resolveModal = document.getElementById("resolve-modal");
    const closeModal = document.getElementById("close-modal");
    const btnConfirmResolve = document.getElementById("btn-confirm-resolve");
    let currentResolveId = null;

    function openResolveModal(id) {
        currentResolveId = id;
        resolveModal.classList.add("active");
    }

    closeModal.addEventListener("click", () => {
        resolveModal.classList.remove("active");
    });

    btnConfirmResolve.addEventListener("click", async () => {
        const status = document.getElementById("resolve-status").value;
        const notes = document.getElementById("resolve-notes").value;

        try {
            const res = await fetch(`/api/alerts/${currentResolveId}/resolve`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: json.stringify({ status: status, resolution_notes: notes })
            });

            if (res.ok) {
                showToast("Alerta resolvido com sucesso", "success");
                resolveModal.classList.remove("active");
                loadAlerts();
            } else {
                showToast("Erro ao processar resolução", "error");
            }
        } catch (e) {
            showToast("Erro de rede", "error");
        }
    });

    filterSeverity.addEventListener("change", loadAlerts);
    filterStatus.addEventListener("change", loadAlerts);

    // ==========================================
    // 7. ABA DE CRÉDITO (SHAP BARS + GAUGES)
    // ==========================================
    const btnCalcScore = document.getElementById("btn-calc-score");
    const btnGenerateReport = document.getElementById("btn-generate-report");
    const lenderReportCard = document.getElementById("lender-report-card");
    const lenderReportBody = document.getElementById("lender-report-body");
    const btnDownloadReport = document.getElementById("btn-download-report");

    async function loadCreditProfile() {
        try {
            const res = await fetch("/api/credit/score");
            const data = await res.json();
            
            // Plota o Gauge
            animateGauge(data.score);
            document.getElementById("gauge-rating").innerText = data.rating;

            // Plota os valores nas tabelas
            document.getElementById("credit-metric-dscr").innerText = data.dscr ? data.dscr.toFixed(2) : "0.00";
            document.getElementById("credit-metric-current").innerText = data.current_ratio ? data.current_ratio.toFixed(2) : "0.00";
            document.getElementById("credit-metric-quick").innerText = data.quick_ratio ? data.quick_ratio.toFixed(2) : "0.00";
            document.getElementById("credit-metric-margin").innerText = data.net_profit_margin ? `${(data.net_profit_margin * 100).toFixed(1)}%` : "0.0%";
            document.getElementById("credit-metric-concentration").innerText = data.ar_concentration ? `${(data.ar_concentration * 100).toFixed(1)}%` : "0.0%";

            // Plota as Barras SHAP
            const shapContainer = document.getElementById("shap-container");
            shapContainer.innerHTML = "";
            
            if (data.shap_explanations && Object.keys(data.shap_explanations).length > 0) {
                const featureNames = {
                    "dscr": "DSCR (Capacidade de Pagamento)",
                    "liquidity": "Liquidez Corrente (Ativos/Passivos)",
                    "margin": "Margem de Lucro",
                    "dso": "DSO (Tempo de Recebimento)",
                    "concentration": "Concentração de Recebíveis"
                };

                Object.entries(data.shap_explanations).forEach(([key, val]) => {
                    const name = featureNames[key] || key;
                    const isPositive = val >= 0;
                    const absPct = Math.min((Math.abs(val) / 30.0) * 100, 100); // normaliza escala

                    const row = document.createElement("div");
                    row.className = "shap-row";
                    row.innerHTML = `
                        <div class="shap-info">
                            <span>${name}</span>
                            <span style="font-weight:600; color:${isPositive ? 'var(--color-success)' : 'var(--color-danger)'};">
                                ${isPositive ? '+' : '-'}${Math.abs(val).toFixed(0)} pts
                            </span>
                        </div>
                        <div class="shap-bar-wrapper">
                            <div class="shap-bar ${isPositive ? 'positive' : 'negative'}" style="width: ${absPct}%"></div>
                        </div>
                    `;
                    shapContainer.appendChild(row);
                });
            } else {
                shapContainer.innerHTML = '<p class="empty-state">Nenhuma explicabilidade SHAP disponível.</p>';
            }

            // Plota Fatores de Risco
            const factorsList = document.getElementById("risk-factors-list");
            factorsList.innerHTML = "";
            if (data.risk_factors && data.risk_factors.length > 0) {
                data.risk_factors.forEach(factor => {
                    const card = document.createElement("div");
                    card.className = "factor-card";
                    card.innerText = factor;
                    factorsList.appendChild(card);
                });
            } else {
                factorsList.innerHTML = '<p class="empty-state" style="color:var(--color-success);">Nenhum risco de enquadramento identificado.</p>';
            }
        } catch (e) {
            showToast("Erro ao obter perfil de crédito", "error");
        }
    }

    btnCalcScore.addEventListener("click", async () => {
        btnCalcScore.disabled = True;
        showToast("Calculando credit score com SHAP...", "info");
        try {
            const res = await fetch("/api/credit/calculate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: json.stringify({ year: new Date().getFullYear() })
            });
            if (res.ok) {
                showToast("Cálculo do Score concluído!", "success");
                loadCreditProfile();
            } else {
                showToast("Erro no cálculo", "error");
            }
        } catch (e) {
            showToast("Falha de rede", "error");
        } finally {
            btnCalcScore.disabled = False;
        }
    });

    btnGenerateReport.addEventListener("click", async () => {
        btnGenerateReport.disabled = True;
        btnGenerateReport.innerText = "Analisando SBA Rules...";
        showToast("Gerando laudo com o Underwriting Agent...", "info");
        
        try {
            const res = await fetch("/api/credit/lender-report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: json.stringify({ year: new Date().getFullYear() })
            });
            const data = await res.json();
            
            lenderReportBody.innerText = data.summary;
            btnDownloadReport.href = data.download_url;
            lenderReportCard.style.display = "block";
            
            showToast("Laudo Lender Readiness gerado!", "success");
            
            // Animação de rolagem até o laudo
            lenderReportCard.scrollIntoView({ behavior: 'smooth' });
        } catch (e) {
            showToast("Erro ao gerar dossiê", "error");
        } finally {
            btnGenerateReport.disabled = False;
            btnGenerateReport.innerText = "Gerar Laudo Lender Readiness";
        }
    });

    // ==========================================
    // 8. RENDERIZAÇÃO DO GRAFO EM CANVAS
    // ==========================================
    function loadGraphNetwork() {
        fetch("/api/graph/connections")
            .then(res => res.json())
            .then(data => {
                graphData = data;
                drawGraph();
            })
            .catch(() => showToast("Erro ao carregar grafo de conexões", "error"));
    }

    function drawGraph() {
        const canvas = document.getElementById("graph-canvas");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        
        // Limpa canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const nodes = graphData.nodes || [];
        const edges = graphData.edges || [];

        if (nodes.length === 0) {
            ctx.fillStyle = "#64748b";
            ctx.font = "14px Inter";
            ctx.fillText("Nenhum dado contábil mapeado para o grafo.", canvas.width / 2 - 120, canvas.height / 2);
            return;
        }

        const width = canvas.width;
        const height = canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;

        // Atribui posições circulares aos nós ao redor da SME central
        const partnerNodes = nodes.filter(n => n.id !== "SME_CORE");
        nodes.forEach(node => {
            if (node.id === "SME_CORE") {
                node.x = centerX;
                node.y = centerY;
            }
        });

        partnerNodes.forEach((node, index) => {
            const angle = (index / partnerNodes.length) * 2 * Math.PI;
            // Clientes dispostos em um raio e fornecedores em outro
            const radius = node.type === "customer" ? 140 : 160;
            node.x = centerX + radius * Math.cos(angle);
            node.y = centerY + radius * Math.sin(angle);
        });

        // 1. Desenha as Arestas (Linhas)
        edges.forEach(edge => {
            const sourceNode = nodes.find(n => n.id === edge.source);
            const targetNode = nodes.find(n => n.id === edge.target);

            if (sourceNode && targetNode) {
                ctx.beginPath();
                ctx.moveTo(sourceNode.x, sourceNode.y);
                ctx.lineTo(targetNode.x, targetNode.y);
                
                // Espessura baseada no volume da aresta
                ctx.lineWidth = Math.min(Math.max(edge.volume / 20000, 1), 5);
                ctx.strokeStyle = edge.type === "receivable" ? "rgba(59, 130, 246, 0.4)" : "rgba(16, 185, 129, 0.4)";
                ctx.stroke();
            }
        });

        // 2. Desenha os Nós (Círculos)
        nodes.forEach(node => {
            ctx.beginPath();
            let radius = 12;
            let color = "var(--color-primary-light)";

            if (node.id === "SME_CORE") {
                radius = 18;
                color = "#a855f7"; // Roxo da empresa core
            } else if (node.type === "customer") {
                color = "#3b82f6"; // Azul cliente
            } else {
                color = "#10b981"; // Verde fornecedor
            }

            // Se for nó de risco crítico, desenha borda vermelha pulsando ou cor de destaque
            if (node.risk_level === "critical" || node.risk_level === "high") {
                ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI);
                ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
                ctx.fill();
                ctx.beginPath();
                color = "var(--color-danger)";
            }

            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
            
            // Borda branca fina nos nós
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = "#ffffff";
            ctx.stroke();

            // Texto/Legenda
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 10px Inter";
            ctx.textAlign = "center";
            ctx.fillText(node.label, node.x, node.y - radius - 5);
        });
    }

    // ==========================================
    // 9. ADVISOR CHAT (SSE STREAMING + BADGES)
    // ==========================================
    const chatInput = document.getElementById("chat-input");
    const btnSendChat = document.getElementById("btn-send-chat");
    const chatMessages = document.getElementById("chat-messages");
    const suggestedBtns = document.querySelectorAll(".suggested-btn");

    async function loadChatHistory() {
        try {
            const res = await fetch(`/api/chat/history/${session_id}`);
            const history = await res.json();
            
            if (history && history.length > 0) {
                chatMessages.innerHTML = "";
                history.forEach(msg => {
                    appendChatMessage(msg.role, msg.content, msg.citations);
                });
            }
        } catch (e) {
            loggingError("Falha ao puxar histórico do chat", e);
        }
    }

    function appendChatMessage(role, content, citations = []) {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        
        let formattedContent = content;
        
        // Formata as citações SBA na mensagem como badges
        if (citations && citations.length > 0) {
            formattedContent += '<div class="citations-container" style="margin-top: 8px; display:flex; gap:6px; flex-wrap:wrap;">';
            citations.forEach(cite => {
                formattedContent += `<span class="badge badge-purple" style="font-size:10px;">${cite}</span>`;
            });
            formattedContent += '</div>';
        }

        bubble.innerHTML = `
            <p>${formattedContent}</p>
            <span class="timestamp">${role === 'user' ? 'Você' : 'ARIA Advisor'}</span>
        `;
        
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function sendChatMessage(message) {
        if (!message.trim()) return;

        appendChatMessage("user", message);
        chatInput.value = "";

        // Adiciona o typing indicator
        const typingBubble = document.createElement("div");
        typingBubble.className = "chat-bubble assistant typing-indicator-bubble";
        typingBubble.innerHTML = `
            <div class="typing-indicator" style="display:flex; gap:4px; align-items:center; height:18px;">
                <span class="dot" style="width:6px; height:6px; border-radius:50%; background-color:#94a3b8; animation: pulse 0.8s infinite alternate;"></span>
                <span class="dot" style="width:6px; height:6px; border-radius:50%; background-color:#94a3b8; animation: pulse 0.8s infinite alternate 0.2s;"></span>
                <span class="dot" style="width:6px; height:6px; border-radius:50%; background-color:#94a3b8; animation: pulse 0.8s infinite alternate 0.4s;"></span>
            </div>
        `;
        chatMessages.appendChild(typingBubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // SSE Streaming Call
        try {
            const response = await fetch("/api/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: json.stringify({ session_id: session_id, message: message })
            });

            // Remove o typing indicator
            typingBubble.remove();

            if (!response.body) {
                appendChatMessage("assistant", "Não foi possível conectar ao fluxo da IA.");
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            // Adiciona balão vazio para receber o stream
            const responseBubble = document.createElement("div");
            responseBubble.className = "chat-bubble assistant";
            
            const textEl = document.createElement("p");
            // Cursor piscante ativo
            textEl.className = "streaming-text";
            responseBubble.appendChild(textEl);
            
            const senderEl = document.createElement("span");
            senderEl.className = "timestamp";
            senderEl.innerText = "ARIA Advisor";
            responseBubble.appendChild(senderEl);

            chatMessages.appendChild(responseBubble);
            
            let fullText = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split("\n");
                
                lines.forEach(line => {
                    if (line.trim().startsWith("data:")) {
                        try {
                            const data = json.parse(line.substring(5).trim());
                            if (data.text) {
                                fullText += data.text;
                                textEl.innerText = fullText;
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                        } catch (err) {
                            // Ignora erros parciais de parsing de chunks cortados
                        }
                    }
                });
            }

            // Remove o cursor ativo de digitação
            textEl.classList.remove("streaming-text");

        } catch (e) {
            typingBubble.remove();
            appendChatMessage("assistant", "Erro na rede ao conectar com a IA.");
        }
    }

    btnSendChat.addEventListener("click", () => {
        sendChatMessage(chatInput.value);
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            sendChatMessage(chatInput.value);
        }
    });

    // Suggested queries triggers
    suggestedBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            sendChatMessage(btn.innerText);
        });
    });

    // Logging helpers
    function loggingError(message, error) {
        console.error(`${message}:`, error);
    }

    // Inicialização
    loadOverviewData();
});


