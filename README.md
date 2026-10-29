# Claude Permission Playground

Preview which Claude Code permission rules match a proposed tool call. The local CLI explains deny/ask/allow precedence, supports a documented subset of Bash, file-path, and WebFetch domain rules, and flags broad matching grants. It never executes a command.

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

Try the included example settings file:

```bash
python3 permission_playground.py settings.json \
  --tool Bash \
  --input '{"command":"git push origin main"}'
```

The example shows a deny rule winning over a broader allow rule. Change the command to `git status` to see the more specific allow rule win over the broader ask rule.

## Supported rule examples

- `Bash` and `Bash(*)`
- Bash command patterns such as `Bash(git *)`, `Bash(git log * main)`, and `Bash(npm run build)`; `*` can appear more than once
- Tool names such as `Read`, `Write`, and `WebFetch`
- Glob-style path patterns for `Read`, `Edit`, `Write`, and `NotebookEdit`
- `WebFetch(domain:example.com)`, `WebFetch(domain:*.example.com)`, and `WebFetch(domain:*)`
- Tool-name wildcards for deny/ask rules

Rules that depend on Claude Code's live tool catalog, managed policy, session flags, compound-command parsing, wrappers, or newer matching semantics cannot be fully simulated here. In particular, this tool does not decide whether a proposed call will actually be allowed by a running Claude Code session. Unsupported rule forms may be reported as outside the supported subset.

## Safety and limits

- The command in `--input` is treated only as text; it is never run.
- The settings file is read only.
- This is a documented-behavior approximation, not a drop-in replica of Claude Code. It cannot see organization managed settings, CLI flags, trusted-folder state, session context, or installed tools.
- Bash wildcards are matched against the supplied command string as a glob; shell parsing, wrapper removal, and compound-command analysis are out of scope.
- Path matching is a portable glob approximation and does not resolve paths, symlinks, or Claude Code's path anchors.
- Consult the current [permission documentation](https://code.claude.com/docs/en/permissions) before changing important rules.

## License

MIT. See [LICENSE](LICENSE).
