-- app/database/schema.sql

-- Alertas de Risco gerados pelo sistema
CREATE TABLE IF NOT EXISTS risk_alerts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type          TEXT NOT NULL,             -- transaction_anomaly | high_dso | counterparty_risk | credit_drop
    severity            TEXT NOT NULL,             -- low | medium | high | critical
    description         TEXT NOT NULL,             -- Resumo detalhado do alerta
    status              TEXT DEFAULT 'open',       -- open | investigating | resolved | false_positive
    transaction_id      INTEGER,                   -- ID de referência da transação no AFIS (opcional)
    invoice_id          INTEGER,                   -- ID de referência da fatura no APEX (opcional)
    counterparty_name   TEXT,                      -- Entidade relacionada
    score_value         REAL,                      -- Score de anomalia associado
    resolved_by         TEXT,                      -- Usuário ou ação automática que resolveu
    resolution_notes    TEXT,                      -- Comentários de resolução
    resolved_at         DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_risk_alerts_status ON risk_alerts(status);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_severity ON risk_alerts(severity);

-- Histórico de Credit Scores calculados para a SME
CREATE TABLE IF NOT EXISTS sme_credit_scores (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_year                INTEGER NOT NULL,
    calculated_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    score                   INTEGER NOT NULL,          -- Score final 0 a 100
    rating                  TEXT NOT NULL,             -- AAA | AA | A | BBB | BB | B | CCC | D
    dscr                    REAL,                      -- Debt Service Coverage Ratio
    current_ratio           REAL,                      -- Liquidez Corrente
    quick_ratio             REAL,                      -- Liquidez Seca
    net_profit_margin       REAL,                      -- Margem de lucro líquido
    dso_days                REAL,                      -- Days Sales Outstanding extraído do APEX
    ar_concentration        REAL,                      -- Concentração de recebíveis
    shap_explanations       TEXT,                      -- Explicações em formato JSON
    risk_factors            TEXT                       -- Fatores chaves (JSON array de strings)
);

CREATE INDEX IF NOT EXISTS idx_sme_credit_scores_year ON sme_credit_scores(tax_year);

-- Relatórios Lender Readiness gerados
CREATE TABLE IF NOT EXISTS lender_reports (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_year            INTEGER NOT NULL,
    overall_score       INTEGER NOT NULL,
    lender_decision     TEXT NOT NULL,             -- approved | conditional | declined
    summary             TEXT NOT NULL,             -- Resumo executivo da decisão
    report_path         TEXT,                      -- Caminho do PDF gerado
    generated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de mensagens do Advisor Chat (Tax/Risk Strategy)
CREATE TABLE IF NOT EXISTS risk_chat_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT NOT NULL,
    role                TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content             TEXT NOT NULL,
    citations           TEXT,                      -- JSON array com trechos/regras citadas
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_risk_chat_history_session ON risk_chat_history(session_id);

-- Configurações Gerais do Módulo ARIA
CREATE TABLE IF NOT EXISTS aria_settings (
    key                 TEXT PRIMARY KEY,
    value               TEXT NOT NULL,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Logs de Auditoria NIST AI RMF
CREATE TABLE IF NOT EXISTS nist_audit_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type          TEXT NOT NULL,             -- model_inference | risk_alert_trigger | human_override | database_sync
    component           TEXT NOT NULL,             -- orchestrator | transaction_monitor | credit_scoring
    actor               TEXT NOT NULL,             -- system | agent | human_user
    description         TEXT NOT NULL,
    metadata_json       TEXT,                      -- Metadados detalhados (JSON)
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Inserir configurações padrão iniciais
INSERT OR IGNORE INTO aria_settings (key, value) VALUES
    ('anomaly_sensitivity', '0.05'),               -- Fração de contaminação para Isolation Forest
    ('critical_alert_threshold', '0.75'),          -- Score acima disso vira alerta imediato
    ('target_debt_service_ratio', '1.25'),         -- DSCR ideal exigido por bancos
    ('experian_mock_rating', 'good');              -- Rating mock do bureau de crédito


