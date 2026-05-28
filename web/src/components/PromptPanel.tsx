import { Clipboard, Download, FileText, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import type { ProviderSummary } from "../types";

export function PromptPanel({
  title,
  prompt,
  description,
  relatedRecordIds = []
}: {
  title: string;
  prompt: string;
  description?: string;
  relatedRecordIds?: string[];
}) {
  const { mode, providerAvailable, t } = useI18n();
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [runStatus, setRunStatus] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [responseText, setResponseText] = useState("");

  useEffect(() => {
    api.providerSettings()
      .then((settings) => {
        setProviders(settings.providers);
        setSelectedProvider(settings.default_provider || settings.providers[0]?.id || "");
      })
      .catch(() => setProviders([]));
  }, []);

  const copy = async () => {
    if (prompt) await navigator.clipboard.writeText(prompt);
  };
  const download = () => {
    if (!prompt) return;
    const blob = new Blob([prompt], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "prompt"}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };
  const runWithProvider = async () => {
    if (!prompt || !selectedProvider) return;
    const ok = window.confirm(t("confirmApiRun"));
    if (!ok) return;
    setRunStatus("Running provider...");
    setResponseText("");
    try {
      const result = await api.aiRunText({
        provider_id: selectedProvider,
        prompt,
        prompt_type: title,
        related_record_ids: relatedRecordIds,
        confirmed: true
      });
      setRunStatus(`${t("aiRunSaved")}: ${result.item.id}`);
      setResponseText(result.response);
    } catch (err) {
      setRunStatus(err instanceof Error ? err.message : t("providerRunFailed"));
    }
  };

  const canRunApi = mode === "api" && providerAvailable && !!providers.length && !!selectedProvider;
  const selected = providers.find((provider) => provider.id === selectedProvider);
  const promptBytes = prompt ? new Blob([prompt]).size : 0;

  return (
    <section className="prompt-panel">
      <div className="panel-title-row">
        <div>
          <h3>{title || t("generatedPrompt")}</h3>
          {description && <p className="prompt-purpose">{description}</p>}
          {!!relatedRecordIds.length && <p className="prompt-related">Related: {relatedRecordIds.join(", ")}</p>}
        </div>
        <span className={`mode-pill ${canRunApi ? "api" : "prompt"}`}>
          {canRunApi ? t("apiModeStatus") : t("promptModeStatus")}
        </span>
      </div>

      {!prompt ? (
        <div className="prompt-empty">
          <FileText size={16} />
          <span>{t("generatePrompt")}</span>
        </div>
      ) : (
        <>
          {!providerAvailable && <p className="prompt-related">{t("noProviderFallback")}</p>}
          <div className="prompt-actions">
            {canRunApi ? (
              <button onClick={runWithProvider}>
                <Play size={16} />
                {t("runWithApi")}
              </button>
            ) : (
              <button onClick={copy}>
                <Clipboard size={16} />
                {t("copyPrompt")}
              </button>
            )}
            {canRunApi && (
              <button className="secondary" onClick={copy}>
                <Clipboard size={16} />
                {t("copyPrompt")}
              </button>
            )}
            <button className="secondary" onClick={() => setShowPreview(!showPreview)}>
              {t("contextPreview")}
            </button>
            <button className="icon-button" onClick={download} title={t("savePrompt")}>
              <Download size={16} />
              {t("savePrompt")}
            </button>
            <button className="secondary" onClick={() => setShowPrompt(!showPrompt)}>
              {showPrompt ? t("details") : t("generatedPrompt")}
            </button>
          </div>

          {canRunApi && (
            <div className="provider-run-row compact">
              <select value={selectedProvider} onChange={(event) => setSelectedProvider(event.target.value)}>
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.id} ({provider.default_model || provider.type})
                  </option>
                ))}
              </select>
            </div>
          )}

          {showPreview && (
            <dl className="context-preview">
              <div><dt>{t("provider")}</dt><dd>{selectedProvider || "none"}</dd></div>
              <div><dt>{t("model")}</dt><dd>{selected?.default_model || "provider default"}</dd></div>
              <div><dt>{t("promptType")}</dt><dd>{title}</dd></div>
              <div><dt>{t("includedRecords")}</dt><dd>{relatedRecordIds.join(", ") || "none"}</dd></div>
              <div><dt>{t("contextSize")}</dt><dd>{promptBytes} bytes</dd></div>
              <div><dt>{t("rawReferences")}</dt><dd>no</dd></div>
              <div><dt>{t("rawSessions")}</dt><dd>no</dd></div>
            </dl>
          )}

          {runStatus && <p className="prompt-related">{runStatus}</p>}
          {responseText && (
            <details className="ai-response-panel" open>
              <summary>Review output</summary>
              <pre>{responseText}</pre>
              <p className="prompt-related">Apply manually. AI output is an artifact, not source-of-truth learning state.</p>
            </details>
          )}
          {showPrompt && <pre>{prompt}</pre>}
        </>
      )}
    </section>
  );
}
