"""Audit a .rbxlx place for anything that could reach real game services or the network.

  python roblox-native/tools/audit_place.py <place.rbxlx> [--json out.json]

Lists every script (class, path, enabled/disabled) and flags service use that matters for an
isolated marketing copy: persistent data, cross-server messaging, HTTP, purchases, teleports,
badges, analytics, asset loading by ID, dynamic code, and risky service properties.
Read-only: it never writes the place.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

RISKS = {
    "persistent_data": r"DataStoreService|GetDataStore|GetOrderedDataStore|MemoryStoreService",
    "cross_server": r"MessagingService|PublishAsync|SubscribeAsync",
    "http": r"HttpService\s*[:.]\s*(GetAsync|PostAsync|RequestAsync)|HttpService:RequestAsync|RequestAsync\(",
    "purchases": r"MarketplaceService|PromptPurchase|PromptProductPurchase|ProcessReceipt|PromptGamePass",
    "teleport": r"TeleportService|TeleportAsync|ReserveServer",
    "badges_groups": r"BadgeService|AwardBadge|GroupService",
    "analytics": r"AnalyticsService|LogCustomEvent|LogEconomyEvent|LogFunnelStepEvent",
    "live_config": r"ConfigService",
    "asset_by_id": r"require\s*\(\s*\d{5,}|InsertService|LoadAsset",
    "dynamic_code": r"loadstring\s*\(|getfenv|setfenv",
    "open_cloud": r"apis\.roblox\.com|OpenCloud",
    "notifications_social": r"ExperienceNotificationService|SocialService|PolicyService",
}
SCRIPT_CLASSES = {"Script", "LocalScript", "ModuleScript"}
SERVICE_PROPS = {("HttpService", "HttpEnabled"), ("ServerScriptService", "LoadStringEnabled")}


def props(item):
    p = item.find("Properties")
    return p if p is not None else ET.Element("Properties")


def prop(item, name):
    for child in props(item):
        if child.get("name") == name:
            return child
    return None


def walk(item, path):
    name_el = prop(item, "Name")
    name = name_el.text if name_el is not None and name_el.text else item.get("class")
    here = f"{path}.{name}" if path else name
    yield item, here
    for child in item.findall("Item"):
        yield from walk(child, here)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("place")
    ap.add_argument("--json")
    a = ap.parse_args()
    root = ET.parse(a.place).getroot()
    scripts, findings, settings = [], [], []
    classes = Counter()
    for top in root.findall("Item"):
        for item, path in walk(top, ""):
            cls = item.get("class")
            classes[cls] += 1
            for svc, p in SERVICE_PROPS:
                if cls == svc:
                    el = prop(item, p)
                    settings.append({"service": svc, "property": p, "value": el.text if el is not None else "(default)"})
            if cls in SCRIPT_CLASSES:
                src_el = prop(item, "Source")
                src = (src_el.text or "") if src_el is not None else ""
                dis = prop(item, "Disabled")
                enabled = prop(item, "Enabled")
                disabled = (dis is not None and dis.text == "true") or (enabled is not None and enabled.text == "false")
                scripts.append({"class": cls, "path": path, "disabled": disabled, "lines": src.count("\n") + 1})
                seen = set()
                for risk, pat in RISKS.items():
                    for m in re.finditer(pat, src):
                        line = src.count("\n", 0, m.start()) + 1
                        if (risk, line) in seen:  # one finding per risk per line
                            continue
                        seen.add((risk, line))
                        snippet = src.splitlines()[line - 1].strip()[:140]
                        findings.append({"risk": risk, "path": path, "class": cls, "line": line,
                                         "disabled": disabled, "match": m.group(0), "code": snippet})
    report = {"place": a.place, "instances": sum(classes.values()), "scripts": len(scripts),
              "script_classes": {k: classes[k] for k in SCRIPT_CLASSES}, "service_settings": settings,
              "findings": findings, "script_list": scripts}
    print(f"{a.place}: {report['instances']} instances, {len(scripts)} scripts {report['script_classes']}")
    for s in settings:
        print(f"setting  {s['service']}.{s['property']} = {s['value']}")
    by_risk = Counter(f["risk"] for f in findings)
    print("findings:", dict(by_risk) or "none")
    for f in findings:
        print(f"  [{f['risk']}] {f['path']}:{f['line']} {'(disabled) ' if f['disabled'] else ''}{f['code']}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
    sys.exit(0)


if __name__ == "__main__":
    main()
