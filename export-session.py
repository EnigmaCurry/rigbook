#!/usr/bin/env python3
"""Export a Claude Code session JSONL to styled HTML with diffs."""

import json
import sys
import html
import difflib
from pathlib import Path


def escape(text):
    return html.escape(text or "")


def render_diff(old_string, new_string):
    old_lines = (old_string or "").splitlines(keepends=True)
    new_lines = (new_string or "").splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, lineterm="")
    lines = []
    for line in diff:
        stripped = line.rstrip("\n")
        cls = ""
        if stripped.startswith("+++") or stripped.startswith("---"):
            cls = "diff-header"
        elif stripped.startswith("@@"):
            cls = "diff-range"
        elif stripped.startswith("+"):
            cls = "diff-add"
        elif stripped.startswith("-"):
            cls = "diff-del"
        lines.append(f'<div class="{cls}">{escape(stripped)}</div>')
    return (
        "\n".join(lines)
        if lines
        else f'<pre class="diff-add">{escape(new_string)}</pre>'
    )


def render_tool_use(block):
    name = block.get("name", "")
    inp = block.get("input", {})
    parts = [f'<div class="tool-header">{escape(name)}</div>']

    if name == "Edit":
        fp = inp.get("file_path", "")
        parts.append(f'<div class="tool-file">{escape(fp)}</div>')
        parts.append('<div class="diff-block">')
        parts.append(render_diff(inp.get("old_string", ""), inp.get("new_string", "")))
        parts.append("</div>")
    elif name == "Write":
        fp = inp.get("file_path", "")
        content = inp.get("content", "")
        parts.append(f'<div class="tool-file">{escape(fp)}</div>')
        parts.append(f'<pre class="code-block">{escape(content)}</pre>')
    elif name == "Read":
        fp = inp.get("file_path", "")
        parts.append(f'<div class="tool-file">{escape(fp)}</div>')
    elif name == "Bash":
        cmd = inp.get("command", "")
        desc = inp.get("description", "")
        if desc:
            parts.append(f'<div class="tool-desc">{escape(desc)}</div>')
        parts.append(f'<pre class="code-block bash">$ {escape(cmd)}</pre>')
    elif name == "Grep":
        pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        parts.append(
            f'<div class="tool-desc">grep {escape(pattern)} {escape(path)}</div>'
        )
    elif name == "Glob":
        pattern = inp.get("pattern", "")
        parts.append(f'<div class="tool-desc">glob {escape(pattern)}</div>')
    elif name == "Agent":
        desc = inp.get("description", "")
        prompt = inp.get("prompt", "")
        parts.append(f'<div class="tool-desc">{escape(desc)}</div>')
        if prompt:
            parts.append(f'<pre class="code-block">{escape(prompt[:500])}</pre>')
    else:
        parts.append(
            f'<pre class="code-block">{escape(json.dumps(inp, indent=2)[:1000])}</pre>'
        )

    return "\n".join(parts)


def render_tool_result(block):
    content = block.get("content", "")
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif isinstance(c, str):
                parts.append(c)
        content = "\n".join(parts)
    if not content or len(content.strip()) == 0:
        return ""
    # Truncate very long results
    if len(content) > 3000:
        content = content[:3000] + "\n... (truncated)"
    return f'<pre class="tool-result">{escape(content)}</pre>'


def main():
    if len(sys.argv) < 2:
        # Find most recent session
        claude_dir = Path.home() / ".claude" / "projects"
        sessions = sorted(claude_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime)
        if not sessions:
            print("No sessions found", file=sys.stderr)
            sys.exit(1)
        session_file = sessions[-1]
        print(f"Using most recent session: {session_file}", file=sys.stderr)
    else:
        session_file = Path(sys.argv[1])

    output_file = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else session_file.with_suffix(".html")
    )

    # Parse messages
    messages = []
    tool_uses = {}  # id -> block

    with open(session_file) as f:
        for line in f:
            entry = json.loads(line)
            msg_type = entry.get("type")
            if msg_type not in ("user", "assistant"):
                continue
            msg = entry.get("message", {})
            role = msg.get("role", msg_type)
            content = msg.get("content", [])
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            messages.append({"role": role, "content": content})
            # Index tool_use blocks
            if role == "assistant":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_uses[block.get("id")] = block

    # Render HTML
    html_parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        role_class = "user" if role == "user" else "assistant"

        blocks = []
        for block in content:
            if isinstance(block, str):
                blocks.append(f'<div class="text">{escape(block)}</div>')
            elif not isinstance(block, dict):
                continue
            elif block.get("type") == "text":
                text = block.get("text", "")
                # Skip system reminders
                if "<system-reminder>" in text:
                    continue
                blocks.append(f'<div class="text">{escape(text)}</div>')
            elif block.get("type") == "tool_use":
                blocks.append(f'<div class="tool-use">{render_tool_use(block)}</div>')
            elif block.get("type") == "tool_result":
                result_html = render_tool_result(block)
                if result_html:
                    blocks.append(f'<div class="tool-result-wrap">{result_html}</div>')
            elif block.get("type") == "thinking":
                # Skip thinking blocks
                continue

        if not blocks:
            continue

        html_parts.append(
            f'<div class="message {role_class}">\n'
            f'  <div class="role-label">{role}</div>\n'
            f'  <div class="content">{"".join(blocks)}</div>\n'
            f"</div>\n"
        )

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guidebook Session Export</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2rem;
    background: #1e1e2e; color: #cdd6f4;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px; line-height: 1.6;
  }}
  .message {{
    margin-bottom: 1.5rem;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    max-width: 960px;
    margin-left: auto; margin-right: auto;
  }}
  .user {{
    background: #313244;
    border-left: 4px solid #89b4fa;
  }}
  .assistant {{
    background: #1e1e2e;
    border-left: 4px solid #a6e3a1;
  }}
  .role-label {{
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
    opacity: 0.6;
    font-weight: bold;
  }}
  .user .role-label {{ color: #89b4fa; }}
  .assistant .role-label {{ color: #a6e3a1; }}
  .text {{
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  .tool-use {{
    background: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 0.75rem;
    margin: 0.5rem 0;
    overflow-x: auto;
  }}
  .tool-header {{
    color: #f9e2af;
    font-weight: bold;
    font-size: 0.85rem;
    margin-bottom: 0.25rem;
  }}
  .tool-file {{
    color: #94e2d5;
    font-family: monospace;
    font-size: 0.8rem;
    margin-bottom: 0.5rem;
  }}
  .tool-desc {{
    color: #a6adc8;
    font-size: 0.8rem;
    font-style: italic;
    margin-bottom: 0.25rem;
  }}
  .diff-block {{
    font-family: 'Fira Code', 'Cascadia Code', monospace;
    font-size: 0.8rem;
    line-height: 1.4;
  }}
  .diff-header {{ color: #cdd6f4; font-weight: bold; }}
  .diff-range {{ color: #89b4fa; }}
  .diff-add {{ color: #a6e3a1; background: rgba(166,227,161,0.1); }}
  .diff-del {{ color: #f38ba8; background: rgba(243,139,168,0.1); }}
  .code-block {{
    background: #11111b;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 0.5rem 0.75rem;
    font-family: 'Fira Code', 'Cascadia Code', monospace;
    font-size: 0.8rem;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  .bash {{ color: #a6e3a1; }}
  .tool-result {{
    background: #11111b;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 0.5rem 0.75rem;
    font-family: monospace;
    font-size: 0.75rem;
    color: #a6adc8;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 300px;
    overflow-y: auto;
  }}
  .tool-result-wrap {{
    margin: 0.5rem 0;
  }}
</style>
</head>
<body>
<h1 style="text-align:center; color:#a6e3a1; max-width:960px; margin:0 auto 2rem;">Guidebook Session</h1>
{"".join(html_parts)}
</body>
</html>"""

    output_file.write_text(html_doc)
    print(f"Exported to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
