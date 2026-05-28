import { ClipboardList } from "lucide-react";

export function AgentTaskCard({
  title,
  context,
  prompt,
  targetFiles,
  expectedOutput
}: {
  title: string;
  context: string;
  prompt: string;
  targetFiles: string[];
  expectedOutput: string[];
}) {
  const text = [
    `Task: ${title}`,
    `Context: ${context}`,
    `Prompt:\n${prompt}`,
    `Likely target files:\n${targetFiles.map((file) => `- ${file}`).join("\n")}`,
    `Expected output fields:\n${expectedOutput.map((field) => `- ${field}`).join("\n")}`
  ].join("\n\n");
  return (
    <section className="task-card">
      <div className="panel-title-row">
        <h3>
          <ClipboardList size={16} />
          Agent Task
        </h3>
        <button className="icon-button" onClick={() => navigator.clipboard.writeText(text)}>
          Copy task
        </button>
      </div>
      <strong>{title}</strong>
      <p>{context}</p>
      <small>{targetFiles.join(", ")}</small>
    </section>
  );
}
