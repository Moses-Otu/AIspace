#!/usr/bin/env python3
"""Strip secrets and client identifiers out of an n8n workflow export.

Usage:
    python sanitise_export.py raw-export.json out/workflow.json ["Optional New Name"]

The input may be either a bare workflow object or the ``{"workflow": {...}}``
envelope returned by the n8n MCP server. The output is an importable workflow
with credentials, webhook IDs and instance metadata removed.

Add project-specific substitutions to REPLACE before running, and always read
the output back before committing it.
"""

import json
import re
import sys

# Instance-specific metadata that should never be committed.
DROP_TOP = {
    "scopes", "versionId", "activeVersionId", "activeVersion", "isArchived",
    "triggerCount", "canExecute", "parentFolderId", "tags", "meta", "nodeGroups",
}

# (pattern, replacement) applied to the serialised JSON.
REPLACE = [
    (r"https://[a-z0-9-]+\.app\.n8n\.cloud", "https://YOUR-N8N-HOST"),
    (r"[\w.+-]+@(?:gmail|outlook|yahoo|hotmail)\.com", "someone@example.com"),
]


def scrub_node(node):
    node.pop("credentials", None)
    node.pop("webhookId", None)
    return node


def sanitise(src, dst, name=None):
    payload = json.load(open(src, encoding="utf-8"))
    wf = payload.get("workflow", payload)

    for key in list(wf):
        if key in DROP_TOP:
            wf.pop(key)
    wf.pop("id", None)

    out = {
        "name": name or wf.get("name"),
        "nodes": [scrub_node(n) for n in wf.get("nodes", [])],
        "connections": wf.get("connections", {}),
        "settings": wf.get("settings", {}),
        "description": wf.get("description"),
    }

    text = json.dumps(out, indent=2, ensure_ascii=False)
    for pattern, replacement in REPLACE:
        text = re.sub(pattern, replacement, text)

    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")

    print(f"wrote {dst} ({len(out['nodes'])} nodes)")


if __name__ == "__main__":
    if not 3 <= len(sys.argv) <= 4:
        sys.exit(__doc__)
    sanitise(*sys.argv[1:])
