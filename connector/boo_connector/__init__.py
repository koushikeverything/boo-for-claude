"""Boo for Claude — Mode B multi-account remote MCP connector.

Built ONLY because the capability matrix shows native Google connectors cannot expose multiple
Google accounts to a single Claude task (docs/PLATFORM-CAPABILITIES.md). It lets one Boo identity
connect several Google accounts, keeps every result attributed to a stable account id, and never
returns tokens to Claude.

The live OAuth/hosting path is gated PENDING real credentials; everything here is fully exercised
against fixtures. See connector/README.md.
"""

__version__ = "0.1.0"
