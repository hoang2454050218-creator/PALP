# `.ruler/` — Single source of truth for AI agent rules

Quản lý tập trung instructions, MCP servers, và skills cho ~30 AI coding agents qua [Ruler](https://github.com/intellectronica/ruler).

## Cấu trúc

```
.ruler/
├── AGENTS.md                       # Primary entry point - executive summary
├── ruler.toml                      # Master config: agents, MCP, skills, gitignore
├── README.md                       # File này
├── 01-project-architecture.md      # Module map, 9 apps, technical decisions
├── 02-django-backend.md            # Django/DRF/Celery patterns
├── 03-nextjs-frontend.md           # Next.js 14, Tailwind, Radix
├── 04-api-conventions.md           # REST, RBAC, throttling, OpenAPI
├── 05-testing-standards.md         # pytest, Vitest, Playwright
├── 06-privacy-security.md          # PII, consent, audit, RBAC, 15-item checklist
├── 07-docker-ops.md                # Docker, monitoring, backup
├── 08-coding-standards.md          # Universal: clean code, SRP, no hardcode
└── skills/                         # Progressive-disclosure playbooks
    ├── bkt-engine/SKILL.md
    ├── privacy-gate/SKILL.md
    ├── release-gate/SKILL.md
    ├── event-taxonomy/SKILL.md
    └── migration-runbook/SKILL.md
```

## Lệnh thường dùng

```bash
npm run ruler:apply    # Sync .ruler/ -> tất cả agent configs
npm run ruler:check    # Dry-run: preview thay đổi không ghi file
npm run ruler:revert   # Undo: khôi phục state trước khi apply
```

Hoặc trực tiếp:

```bash
npx -y @intellectronica/ruler apply --verbose
npx -y @intellectronica/ruler apply --dry-run --verbose
npx -y @intellectronica/ruler revert
```

## Workflow khi sửa rule

1. Edit file `.md` trong `.ruler/` (hoặc `ruler.toml`).
2. Chạy `npm run ruler:apply` để sync sang ~30 agent configs.
3. `git add .ruler/ .pre-commit-config.yaml ...` (Ruler-generated files đã trong `.gitignore`).
4. Commit. Pre-commit hook `ruler-apply` sẽ tự re-sync nếu bạn chỉ commit `.ruler/*`.
5. CI workflow `ruler-check.yml` fail nếu PR có drift.

## Thêm skill mới

```bash
mkdir -p .ruler/skills/my-skill
cat > .ruler/skills/my-skill/SKILL.md <<'EOF'
# My Skill

Khi nào dùng skill này. Bước cụ thể.
EOF
npm run ruler:apply
```

Skill tự được copy sang `.cursor/skills/my-skill/`, `.claude/skills/my-skill/`, `.codex/skills/my-skill/`, v.v.

## Agent được hỗ trợ

Toàn bộ ~30 agent Ruler hỗ trợ (bật trong `default_agents` của `ruler.toml`). Để tắt 1 agent:

```toml
[agents.windsurf]
enabled = false
```

Tham khảo bảng đầy đủ: <https://github.com/intellectronica/ruler#supported-ai-agents>

## File sinh tự động (không commit)

Ruler tự thêm khối `# START Ruler Generated Files ... # END` vào `.gitignore`. Các file điển hình bị ignore:

- `AGENTS.md`, `CLAUDE.md`, `CRUSH.md`, `WARP.md` (root)
- `.aider.conf.yml`, `.clinerules`, `.goosehints`
- `.codex/`, `.gemini/`, `.junie/`, `.windsurf/`, `.zed/`, ...
- `.cursor/skills/`, `.claude/skills/`, ...
- `.cursor/rules/ruler_cursor_instructions.mdc`
- `.cursor/mcp.json`, `.mcp.json`, `.vscode/mcp.json`, ...

Nếu bạn cần commit 1 file cho team (ví dụ `AGENTS.md` cho onboarding GitHub), thêm `!AGENTS.md` ngoài khối Ruler.
