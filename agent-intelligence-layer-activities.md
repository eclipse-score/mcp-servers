# Agent Intelligence Layer: Aktivitäten "Hintertür" (v3)

Prinzip: Es kommt keine Datei und kein PR in Repos, die Du nicht kontrollierst (baselibs, communication, ...). Alles läuft zentral: Graphen baut CI in mcp-servers, ausgeliefert wird per Devcontainer-Feature auf User-Ebene. Der `git status` im Ziel-Repo bleibt sauber.

## Hebel und wer sie kontrolliert (geprüft)

| Hebel | Reichweite | Kontrolle |
|---|---|---|
| mcp-servers | zentral | Du (CODEOWNERS leer, Commits von Dir) |
| Central CI in mcp-servers, Matrix aus `reference_integration/known_good.json`, öffentliche Repos klonen | alle known-good-Module, ohne deren Zutun | Du |
| needs.json auf GitHub Pages (`eclipse-score.github.io/<repo>/main/needs.json`) | baselibs, score = 200; communication = 404 (TRLC) | lesend, keine Erlaubnis nötig |
| Devcontainer-Feature, aus mcp-servers nach GHCR publiziert | jeder Dev, der es aktiviert | Du |
| VS Code User-Setting `dev.containers.defaultFeatures` | hängt das Feature an *jeden* Devcontainer des Users, ohne Repo-Änderung (offiziell dokumentiert) | Developer selbst |
| `apm install -g` (User-Scope `~/.apm/`) | Copilot CLI, Claude Code, Codex CLI, Gemini CLI, Windsurf, JetBrains Copilot. **Nicht** VS Code Copilot Chat und nicht opencode | Du |
| tooling `score-*` Skills → `//:sync_skills` | communication (einziger Konsument), dort weichen 3/4 Kopien schon ab | Du schreibst, communication zieht irgendwann nach |
| s-core devcontainer Image | 24 Repos automatisch | opajonk, lurtz (nicht Du) → erst später |
| cicd-workflows | 25+ Repos | 9 Owner (nicht Du) → nicht nötig |

## Aktivitäten

### A. mcp-servers: Supply-Chain zuerst (Blocker, High)
1. MCP-Server-Quellen pinnen: `git+https://github.com/eclipse-score/mcp-servers@v<version>#subdirectory=…` in `packages/*/apm.yml` (heute ohne Ref = HEAD main).
2. Release-Tags `v<version>` einführen (`tagPattern` ist schon in `apm.yml`), dazu Release-Workflow.
3. graphify-Version an einer Stelle pinnen (heute hart in `apm-setup/src/apm_setup/serve.py`).

### B. mcp-servers: zentrale Graph Registry (ersetzt "CI in jedem Repo")
4. `.github/workflows/graphs.yml`: nightly + on dispatch. Matrix aus `known_good.json` (Repo + gepinnter Commit) plus `main`-Heads. Pro Repo: `git clone --depth 1`, `graphify extract --code-only`, needs.json von Pages laden (falls vorhanden), Overlay bauen (`requirements_lookup.py` existiert schon).
5. Publizieren per `oras push ghcr.io/eclipse-score/mcp-servers/graphs/<repo>:<sha>` und `:main`, mit sha256 und `actions/attest-build-provenance`. Größe ~1.1–1.3 MB gzip pro Repo.
6. Cross-Repo-Graph: `graphify merge-graphs` über das known-good-Set → `graphs/_global:<known-good-version>`.
   - Offen: GHCR-Publish aus mcp-servers braucht `packages: write`, und die Package-Visibility "public" muss eventuell über otterdog bzw. Eclipse-Admins gesetzt werden. Muss ich prüfen.

### C. mcp-servers: Lazy Client im MCP-Server
7. `graphify-codegraph`: `ensure_graph()` beim ersten Tool-Call. Repo über `git remote` + `HEAD` erkennen → Registry-Pull (exakter SHA, sonst `main`) → Digest prüfen → sonst lokal `graphify extract --code-only` im Hintergrund (~15 s), bis dahin degradierte Antwort.
8. Graph-Cache und Experience nach `~/.local/share/score-agent/<repo>/` statt `.score-local/` im Repo. So bleibt das Ziel-Repo sauber, und mit einem Volume überlebt der Cache Rebuilds.
9. `apm-setup` wird reine Diagnose (`verify_setup`). Die README sagt dann: "nichts zu tun".

### D. mcp-servers: Devcontainer-Feature "agent-context" (der eigentliche Eintritt)
10. Neues Verzeichnis, z.B. `devcontainer-feature/agent-context/` mit `devcontainer-feature.json` + `install.sh`:
    - installiert gepinntes graphify + die MCP-Server (uv tool, Version aus A).
    - registriert MCP agent-neutral: `apm install -g` für die CLI-Agents; opencode über `~/.config/opencode` (dort gibt es im s-core-Image schon ein Volume); VS Code über `customizations.vscode.mcp` (für devcontainer.json dokumentiert, **ob ein Feature das beitragen darf, prüfe ich noch**).
    - Volume `score-agent-data` für Graph-Cache und Experience.
    - schreibt nichts in den Workspace und bricht den Container-Build nie ab.
11. Publish nach `ghcr.io/eclipse-score/mcp-servers/agent-context:1` (gleiches Muster wie das devcontainer-Repo).
12. Aktivierung pro Developer, einmalig in den VS Code User-Settings:
    `"dev.containers.defaultFeatures": { "ghcr.io/eclipse-score/mcp-servers/agent-context:1": {} }`
    Danach hat jeder S-CORE-Devcontainer (baselibs, communication, ...) den Layer, ohne dass jemand im Repo etwas merkt.

### E. tooling: weiche Steuerung über Skills
13. In `.github/skills/score-architecture|score-requirements|score-testing/SKILL.md` je 2–3 Zeilen: "Wenn die MCP-Tools `query_graph` / `resolve_requirements` verfügbar sind, zuerst nutzen." Ohne Tools bleibt alles wie heute. Das kommt per `sync_skills` nach communication, sobald die synchronisieren (langsamer Kanal).

### F. Beweis für Adoption (vor jedem Gespräch mit Maintainern)
14. Eval-Harness in mcp-servers (`benchmarks/`): ca. 20 echte Fragen je für baselibs und communication, jeweils mit und ohne Graph (Zeit, Tokens, Korrektheit), plus `graphify benchmark`. Läuft gegen die zentralen Graphen aus B, also ohne Zutun der Repos.
15. ~~Champion-Rollout~~ entfällt (zu wenige Champions, skaliert nicht). Der Benchmark aus 14 läuft automatisiert ohne Developer. Gemessen werden Richtigkeit gegen eine Musterlösung, Tool-Calls/Tokens, Zeit und Graph-Overhead. Das Erfolgskriterium wird vorher festgelegt.

### G. Offizieller Weg = einziger Weg mit Reichweite (mit Zahlen aus F)
16. PR in devcontainer (opajonk/lurtz): `agent-context` als `dependsOn` in `s-core-local`. Dann haben es alle 24 Repos beim nächsten Image-Update, ohne Developer-Setting. Das Feature ist passiv (ohne installierten Agent: no-op), auf einen SHA gepinnt und per `SCORE_AGENT_GRAPH=off` abschaltbar.
17. Repo-Opt-in für Maintainer, die mehr wollen (eigene Overlays, Pakete). Dafür gibt es in `eclipse-score/.github` schon `.github/references/repo-manifest.schema.json` mit einer `mcp`-Sektion ("SCORE governance overlay"). Diese würde ich erweitern statt `graph-stack.yml` neu zu erfinden. Wer das pflegt, kläre ich noch.

### H. mcp-servers: Metamodel-Export (statt docs-as-code#878)
Die docs-as-code-Maintainer wollen den Export nicht in docs-as-code (#878: "this logic can easily be done in the MCP server itself"). Gebraucht wird `metamodel-data.json` von `metamodel-flow` (#22).
18. `tools/schema_export/export_data.py` aus #878 nach `packages/metamodel-flow/src/export_metamodel.py` übernehmen. Das Skript ist eigenständig, ~345 Zeilen, einzige Abhängigkeit `ruamel.yaml` (docs-as-code nutzt 0.19.1). Das ist eine neue Dependency für mcp-servers und muss vorher geprüft werden (CVE, Lizenz). Die Tests aus #878 kommen mit.
19. Quelle: `src/extensions/score_metamodel/metamodel.yaml` von docs-as-code main HEAD. Die Datei ist öffentlich und wird schon heute als Bazel-Filegroup `metamodel_yaml` exportiert, docs-as-code muss also nichts ändern. Der Commit wird in `model/source.txt` festgehalten. Das ersetzt `refresh_metamodel_schema.py`, das heute nur Anweisungen ausgibt.
20. Erzeugen in CI, ohne Bot-Commits: Der central-graphs-Workflow (B) baut `metamodel-data.json` aus docs-as-code HEAD und publiziert es als `ghcr.io/eclipse-score/mcp-servers/graphs/_metamodel:<sha>` / `:main`. `metamodel-flow` lädt es lazy wie C. Die committete Datei in `model/` bleibt als Offline-Fallback. Damit entfällt das Muster aus #22 (`refresh-process-graph.yml` committet als `github-actions[bot]` und öffnet PRs), das vermutlich am ECA-Check scheitert und Actions-PR-Rechte braucht.
21. #22 aufteilen. Der Branch ist 49 Commits voraus, 19 hinter main und hat Konflikte (+49k Zeilen). Zuerst `metamodel-flow` + Export als eigener PR, danach die `context-discipline`-Erweiterungen.
22. #878 mit einem kurzen Verweis auf mcp-servers schließen.

## Reihenfolge
A ✓ → B (4–5) → C → D → Release 0.2.0 → H (18–22) → F(14) → G(16) → E → B(6).
A–D und H liegen komplett in mcp-servers, dafür braucht es keine Fremd-Approvals. Fremd-Approval braucht nur G (devcontainer).
