"""SAP documentation ingestion stub — parses markdown to SAPComponent/SAPService nodes."""

import logging
import uuid
from typing import Optional

from ui.models import SAPComponent, SAPService

logger = logging.getLogger(__name__)


class SAPDocParser:
    def parse_component_markdown(self, markdown: str) -> Optional[SAPComponent]:
        lines = markdown.strip().split("\n")
        name = ""
        library = ""
        comp_type = "control"
        properties = []
        events = []
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                name = line[2:].strip()
            elif line.startswith("Library:"):
                library = line.split(":", 1)[1].strip()
            elif line.startswith("Type:"):
                comp_type = line.split(":", 1)[1].strip()
            elif line.startswith("## "):
                current_section = line[3:].strip().lower()
            elif line.startswith("- ") and current_section:
                item = line[2:].strip()
                if "propert" in current_section:
                    properties.append(item)
                elif "event" in current_section:
                    events.append(item)

        if not name:
            return None

        return SAPComponent(
            component_id=f"sc_parsed_{uuid.uuid4().hex[:8]}",
            name=name,
            library=library or (name.rsplit(".", 1)[0] if "." in name else "unknown"),
            component_type=comp_type,
            properties=properties,
            events=events,
            complexity=2,
        )

    def parse_service_markdown(self, markdown: str) -> Optional[SAPService]:
        lines = markdown.strip().split("\n")
        name = ""
        service_type = ""
        capabilities = []
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                name = line[2:].strip()
            elif line.startswith("Type:"):
                service_type = line.split(":", 1)[1].strip()
            elif line.startswith("## "):
                current_section = line[3:].strip().lower()
            elif line.startswith("- ") and "capabilit" in current_section:
                capabilities.append(line[2:].strip())

        if not name:
            return None

        return SAPService(
            service_id=f"ss_parsed_{uuid.uuid4().hex[:8]}",
            name=name,
            service_type=service_type,
            capabilities=capabilities,
        )
