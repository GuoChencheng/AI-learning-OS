# Provider Setup

`ai-learning-os` is prompt-only by default. You can use the whole project without an API key.

Connected mode is optional. It runs only when you explicitly execute an AI command or choose a provider action in the UI.

## Configuration

Copy the example config for local use:

```bash
cp config.example.yaml config.yaml
```

Keep `config.yaml` local. It is ignored by Git.

Store secrets in environment variables:

```bash
export OPENROUTER_API_KEY="..."
```

Do not put real API keys in `config.yaml`, issues, pull requests, or screenshots.

## OpenAI-Compatible Providers

Any provider with a Chat Completions-compatible endpoint can be configured:

```yaml
providers:
  openrouter:
    type: openai_compatible
    base_url: "https://openrouter.ai/api/v1"
    api_key_env: "OPENROUTER_API_KEY"
    default_model: "openai/gpt-4.1"
```

The app posts to `/chat/completions` under `base_url`.

## Ollama

For local Ollama:

```yaml
providers:
  local_ollama:
    type: ollama
    base_url: "http://127.0.0.1:11434"
    default_model: "llama3.1"
```

No API key is required by default.

## CLI

```bash
learn provider list
learn provider show openrouter
learn provider test openrouter
learn ai run-prompt --provider openrouter --prompt-file prompt.md
learn ai run-context --provider local_ollama --context-pack data/context_packs/example.md
```

Before sending data, the CLI previews what will be sent and asks for confirmation unless `--yes` is passed.

## Privacy Implications

Connected mode sends selected prompt/context text to the configured provider. It does not send all local records, all references, all sessions, or all Deep Research imports.
