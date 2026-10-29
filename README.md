# Claude Permission Playground

Paste a proposed tool call and see which Claude Code permission rules match it. The tool explains deny/ask/allow precedence, highlights broad Bash grants, and never executes the command.

This is an independent, read-only learning aid. It is not affiliated with Anthropic and does not replace Claude Code's own permission engine.

## Why this exists

Permission rules can look deceptively simple: a wildcard before a command subcommand may grant far more than intended, while a matching deny rule takes precedence over a more specific allow. This simulator makes that behavior easier to inspect before you edit a real settings file.

## Requirements

Python 3.10+. No dependencies.

## Quick start

```bash
python3 permission_playground.py .claude/settings.json \
  --tool Bash \
  --input '{"command":"git push origin main"}'
```

For a file rule:

```bash
python3 permission_playground.py .claude/settings.json \
  --tool Read \
  --input '{"file_path":"./.env"}'
```

The result is JSON with each configured rule, whether it matched, why it matched or missed, and the first matching rule under deny → ask → allow precedence.

## Supported rule examples

- `Bash` and `Bash(*)`
- Bash command patterns such as `Bash(git *)`, `Bash(git log *)`, and `Bash(npm run build)`
- Tool names such as `Read`, `Write`, and `WebFetch`
- Glob-style path/domain specifiers for file tools and `WebFetch`
- Tool-name wildcards for deny/ask rules

Rules that depend on Claude Code's live tool catalog, managed policy, session flags, or newer matching semantics cannot be fully simulated here. The tool labels those cases as outside its supported subset where possible.

## Safety and limits

- The command in `--input` is treated only as text; it is never run.
- The settings file is read only.
- This is a documented-behavior approximation, not a drop-in replica of Claude Code. It cannot see organization managed settings, CLI flags, trusted-folder state, session context, or installed tools.
- Consult the current [permission documentation](https://code.claude.com/docs/en/permissions) before changing important rules.

## License

MIT. See [LICENSE](LICENSE).
