"""The AI layer: a tool-using assistant over the semantic layer.

Two rules define this module:

1. **The assistant never computes.** Every number in an answer comes from a tool
   call against the same functions the UI and the API use.
2. **Unsupported numbers are rejected.** After generation the answer is scanned;
   any figure that does not appear in the tool output is treated as a defect and
   the deterministic answer is served instead.

It runs with no model configured — a deterministic planner routes the question to
a tool and the answer is composed from the tool result. Set ``IAA_LLM_BASE_URL`` /
``IAA_LLM_API_KEY`` / ``IAA_LLM_MODEL`` (any OpenAI-compatible endpoint) and the
model is used for planning and phrasing, still on top of the same tools.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from .fleet import MetricRegistry, assess_policy, group_metrics, impact_trace, load_fleet, policy_metrics

DEFAULT_AS_OF = date(2026, 12, 31)
POLICY_RE = re.compile(r"\bP\d{3}\b", re.IGNORECASE)
VEHICLE_RE = re.compile(r"\bV\d{3}\b", re.IGNORECASE)
GROUP_RE = re.compile(r"\bG\d\b", re.IGNORECASE)


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------
@dataclass
class Tool:
    name: str
    description: str
    params: dict[str, str]
    fn: Callable[..., Any]


class Toolbox:
    """The only surface the assistant is allowed to touch."""

    def __init__(self, store: Any = None, registry: MetricRegistry | None = None) -> None:
        self.store = store or load_fleet()
        self.registry = registry or MetricRegistry()
        self.tools: dict[str, Tool] = {
            "assess_policy": Tool(
                "assess_policy",
                "Full renewal assessment for one policy: metrics, rule findings, decision, evidence.",
                {"policy_id": "string", "as_of": "YYYY-MM-DD (optional)", "version": "v1|v2 (optional)"},
                self.assess_policy,
            ),
            "policy_metrics": Tool(
                "policy_metrics",
                "The three governed metrics for a policy: loss ratio, frequency, severity.",
                {"policy_id": "string", "as_of": "YYYY-MM-DD (optional)", "version": "v1|v2 (optional)"},
                self.policy_metrics,
            ),
            "group_metrics": Tool(
                "group_metrics",
                "Aggregate metrics for a group: vehicles, policies, loss ratio, claims.",
                {"group_id": "string", "as_of": "YYYY-MM-DD (optional)", "version": "v1|v2 (optional)"},
                self.group_metrics,
            ),
            "vehicle_history": Tool(
                "vehicle_history",
                "Which policies covered a vehicle and when, plus its claims.",
                {"vehicle_id": "string"},
                self.vehicle_history,
            ),
            "transfers": Tool(
                "transfers",
                "Vehicles that moved between policies in the group, with the effective date.",
                {},
                self.transfers,
            ),
            "impact_trace": Tool(
                "impact_trace",
                "Which decisions change when the loss ratio definition moves v1 to v2.",
                {"as_of": "YYYY-MM-DD (optional)"},
                self.impact_trace,
            ),
            "reserve_development": Tool(
                "reserve_development",
                "Claims reserving: ultimate movement between the two valuations, its drivers, IBNR and the alert.",
                {},
                self.reserve_development,
            ),
            "reserve_position": Tool(
                "reserve_position",
                "Reserve position at one valuation: paid, case, incurred, ultimate, IBNR, by segment.",
                {"valuation_id": "2026-12 | 2027-03"},
                self.reserve_position,
            ),
            "pricing_indication": Tool(
                "pricing_indication",
                "Rate adequacy: projected claims, loss ratio, indicated premium and the sensitivity of each assumption.",
                {"severity_trend": "float (optional)", "frequency_trend": "float (optional)",
                 "target_loss_ratio": "float (optional)"},
                self.pricing_indication,
            ),
        }

    # --- implementations --------------------------------------------
    def assess_policy(self, policy_id: str, as_of: str | date | None = None, version: str | None = None) -> dict:
        day = _day(as_of)
        result = assess_policy(self.store, self.registry, policy_id.upper(), day, version or "v2")
        if result is None:
            raise KeyError(f"unknown policy {policy_id}")
        return _compact_assessment(result)

    def policy_metrics(self, policy_id: str, as_of: str | date | None = None, version: str | None = None) -> dict:
        day = _day(as_of)
        if self.store.policy(policy_id.upper()) is None:
            raise KeyError(f"unknown policy {policy_id}")
        return policy_metrics(self.store, self.registry, policy_id.upper(), day, version or "v2")

    def group_metrics(self, group_id: str, as_of: str | date | None = None, version: str | None = None) -> dict:
        return group_metrics(self.store, self.registry, group_id.upper(), _day(as_of), version or "v2")

    def vehicle_history(self, vehicle_id: str) -> dict:
        vehicle_id = vehicle_id.upper()
        history = self.store.vehicle_history(vehicle_id)
        if not history:
            raise KeyError(f"unknown vehicle {vehicle_id}")
        claims = self.store.claims_for_vehicle(vehicle_id)
        return {
            "vehicle_id": vehicle_id,
            "assignments": [
                {"policy_id": h["policy_id"], "from": h["valid_from"].isoformat(),
                 "to": h["valid_to"].isoformat(), "reason": h.get("transfer_reason", "")}
                for h in history
            ],
            "claims": [
                {"claim_id": c["claim_id"], "date": c["loss_date"].isoformat(), "peril": c["peril"],
                 "incurred": c["incurred"], "alae": c.get("alae", 0), "policy_at_loss": c["policy_id"]}
                for c in claims
            ],
        }

    def transfers(self) -> dict:
        rows = self.store.transfers(date(2025, 12, 31), date(2026, 6, 30))
        return {
            "count": len(rows),
            "effective": rows[0]["effective"].isoformat() if rows else None,
            "from_policy": sorted({r["from_policy"] for r in rows}),
            "to_policy": sorted({r["to_policy"] for r in rows}),
            "vehicles": [r["vehicle_id"] for r in rows],
        }

    def impact_trace(self, as_of: str | date | None = None) -> dict:
        return impact_trace(self.store, self.registry, _day(as_of), "v1", "v2")

    def reserve_position(self, valuation_id: str = "2027-03") -> dict:
        from .reserving import load_book, position

        book = load_book()
        return position(book, valuation_id)

    def reserve_development(self) -> dict:
        from .reserving import assess, load_book

        result = assess(load_book())
        return {
            "baseline": {k: result["baseline"][k] for k in ("valuation_id", "ultimate", "ibnr", "incurred", "paid", "case")},
            "revised": {k: result["revised"][k] for k in ("valuation_id", "ultimate", "ibnr", "incurred", "paid", "case")},
            "change": result["change"],
            "change_pct": result["change_pct"],
            "threshold": result["threshold"],
            "alert": result["alert"],
            "drivers": result["drivers"],
            "decision": result["decision"],
        }

    def pricing_indication(self, severity_trend: float | None = None,
                           frequency_trend: float | None = None,
                           target_loss_ratio: float | None = None) -> dict:
        from .pricing import indication

        return indication(severity_trend=severity_trend, frequency_trend=frequency_trend,
                          target_loss_ratio=target_loss_ratio)

    # --- plumbing ----------------------------------------------------
    def call(self, name: str, **args: Any) -> dict:
        tool = self.tools.get(name)
        if tool is None:
            raise KeyError(f"unknown tool {name}")
        try:
            return {"ok": True, "tool": name, "args": args, "result": tool.fn(**args)}
        except TypeError as exc:
            return {"ok": False, "tool": name, "args": args, "error": f"bad arguments: {exc}"}
        except KeyError as exc:
            return {"ok": False, "tool": name, "args": args, "error": str(exc).strip("'\"")}

    def catalogue(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "params": t.params} for t in self.tools.values()]


def _day(value: str | date | None) -> date:
    if value is None or value == "":
        return DEFAULT_AS_OF
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _compact_assessment(result: dict) -> dict:
    """Trim to what an answer can legitimately cite."""
    return {
        "policy_id": result["policy_id"],
        "as_of": result["as_of"],
        "entity": result["entity_name"],
        "group": result["group_name"],
        "renewal_date": result["renewal_date"],
        "metrics": result["metrics"],
        "group_metrics": result["group_metrics"],
        "findings": [
            {"rule_id": f["rule_id"], "name": f["name"], "actual": f["actual"],
             "threshold": f["threshold"], "breached": f["breached"], "decision": f["decision"],
             "evidence": f["evidence"]}
            for f in result["findings"]
        ],
        "decision": result["decision"],
        "evidence": result["evidence"],
        "vehicles": len(result["vehicles"]),
    }


# --------------------------------------------------------------------------
# planning (deterministic)
# --------------------------------------------------------------------------
def plan(question: str, toolbox: Toolbox) -> tuple[str, dict]:
    """Route a question to one tool. No model required."""
    q = question.lower()
    policy = POLICY_RE.search(question)
    vehicle = VEHICLE_RE.search(question)
    group = GROUP_RE.search(question)
    policy_id = policy.group(0).upper() if policy else "P205"

    if vehicle:
        return "vehicle_history", {"vehicle_id": vehicle.group(0).upper()}
    if any(w in q for w in ("reserve", "ibnr", "ultimate", "development", "adverse", "sign-off")):
        return "reserve_development", {}
    if any(w in q for w in ("premium", "price", "pricing", "rate", "indicated", "adequacy")):
        return "pricing_indication", {}
    if any(w in q for w in ("impact", "definition", "v1", "v2", "alae", "what changed", "trace")):
        return "impact_trace", {}
    if any(w in q for w in ("transfer", "moved", "left the policy", "migrat")):
        return "transfers", {}
    if any(w in q for w in ("group", "aggregate", "150", "whole book")):
        return "group_metrics", {"group_id": (group.group(0).upper() if group else "G1")}
    if any(w in q for w in ("why", "refer", "declin", "decision", "reason", "rule")):
        return "assess_policy", {"policy_id": policy_id}
    if any(w in q for w in ("loss ratio", "frequency", "severity", "metric")):
        return "policy_metrics", {"policy_id": policy_id}
    return "assess_policy", {"policy_id": policy_id}


# --------------------------------------------------------------------------
# answering (deterministic templates)
# --------------------------------------------------------------------------
def _money(value: float) -> str:
    return f"{value:,.0f}"


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _cr(value: float) -> str:
    return f"{value / 1e7:.2f}"


def answer_from_tool(tool: str, result: dict) -> str:
    if tool == "assess_policy":
        m, g = result["metrics"], result["group_metrics"]
        lines = [
            f"{result['policy_id']} ({result['entity']}, group {result['group']}) is **{result['decision']}** as at {result['as_of']}.",
            f"Loss ratio {_pct(m['loss_ratio'])} on the {m['loss_ratio_version']} definition "
            f"({_money(m['numerator'])} over {_money(m['premium'])} premium), "
            f"frequency {m['frequency']:.1f} per 100 vehicle-years, severity {_money(m['severity'])} per claim.",
        ]
        fired = [f for f in result["findings"] if f["breached"]]
        if fired:
            lines.append("Rules breached:")
            for f in fired:
                lines.append(f"· {f['rule_id']} — {f['evidence']} → {f['decision']}")
        if g:
            lines.append(f"Group position: {g['vehicles']} vehicles across {g['policies']} policies, "
                         f"group loss ratio {_pct(g['loss_ratio'])}.")
        if result["evidence"]:
            prior = [e for e in result["evidence"] if e["kind"] == "prior_claim"][:2]
            for e in prior:
                lines.append(f"Evidence (not scored): {e['text']}.")
        lines.append("The underwriter retains the final decision.")
        return "\n".join(lines)

    if tool == "policy_metrics":
        return (
            f"{result['policy_id']} as at {result['as_of']}: loss ratio {_pct(result['loss_ratio'])} "
            f"({result['loss_ratio_version']}, threshold 60%), frequency {result['frequency']:.1f} per 100 vehicle-years, "
            f"severity {_money(result['severity'])} per claim. Exposure {result['vehicles']} vehicles "
            f"({result['vehicle_years']} vehicle-years), {result['claim_count']} claims, "
            f"premium {_money(result['premium'])}."
        )

    if tool == "group_metrics":
        return (
            f"Group {result['group_id']}: {result['vehicles']} vehicles across {result['policies']} policies. "
            f"Loss ratio {_pct(result['loss_ratio'])} ({result['loss_ratio_version']}) on premium {_money(result['premium'])}, "
            f"incurred {_money(result['incurred'])}, ALAE {_money(result['alae'])}, {result['claim_count']} claims."
        )

    if tool == "vehicle_history":
        parts = [f"{result['vehicle_id']} cover history:"]
        for a in result["assignments"]:
            parts.append(f"· {a['policy_id']} from {a['from']} to {a['to']} ({a['reason']})")
        for c in result["claims"]:
            parts.append(
                f"· claim {c['claim_id']} on {c['date']}: {c['peril']}, incurred {_money(c['incurred'])} "
                f"plus ALAE {_money(c['alae'])}, recorded against {c['policy_at_loss']}"
            )
        if not result["claims"]:
            parts.append("· no claims on record")
        return "\n".join(parts)

    if tool == "transfers":
        return (
            f"{result['count']} vehicles moved from {'/'.join(result['from_policy'])} to "
            f"{'/'.join(result['to_policy'])} effective {result['effective']}: "
            f"{', '.join(result['vehicles'][:6])} and {max(result['count'] - 6, 0)} more."
        )

    if tool == "impact_trace":
        rows = result["policies"]
        detail = "; ".join(
            f"{r['policy_id']} {_pct(r['loss_ratio_before'])} → {_pct(r['loss_ratio_after'])}, "
            f"{r['decision_before']} → {r['decision_after']}"
            for r in rows
        )
        return (f"Moving the loss ratio definition {result['from_version']} → {result['to_version']} "
                f"changes {result['changed']} of {result['total']} decisions. {detail}.")

    if tool == "reserve_development":
        base, rev = result["baseline"], result["revised"]
        drivers = "; ".join(f"{d['driver']} {d['impact']/1e7:+.2f} Cr" for d in result["drivers"])
        return (
            f"Ultimate moved from {_cr(base['ultimate'])} Cr at {base['valuation_id']} to "
            f"{_cr(rev['ultimate'])} Cr at {rev['valuation_id']} — {result['change_pct']:+.1%}, "
            f"{'above' if result['alert'] else 'within'} the {result['threshold']:.0%} tolerance.\n"
            f"Drivers: {drivers}.\n"
            f"IBNR is {_cr(rev['ibnr'])} Cr at the revised valuation. {result['decision']}."
        )

    if tool == "reserve_position":
        return (
            f"{result['valuation_id']}: paid {_cr(result['paid'])} Cr, case {_cr(result['case'])} Cr, "
            f"incurred {_cr(result['incurred'])} Cr, ultimate {_cr(result['ultimate'])} Cr, "
            f"IBNR {_cr(result['ibnr'])} Cr across {result['claims']} claims."
        )

    if tool == "pricing_indication":
        return (
            f"Current premium {_money(result['current_premium'])} on claims of {_money(result['incurred_claims'])} "
            f"— a {result['current_ratio']:.1%} loss ratio. Trending claims by "
            f"{result['severity_trend']:+.0%} severity and {result['frequency_trend']:+.0%} frequency gives "
            f"{_money(result['projected_claims'])}, a {result['projected_ratio']:.1%} projected ratio. "
            f"At a {result['target_loss_ratio']:.0%} target the indicated premium is "
            f"{_money(result['indicated_premium'])} ({result['indicated_change']:+.1%}); "
            f"rate adequacy {result['adequacy_ratio']:.1%}. {result['decision']}."
        )

    return json.dumps(result, default=str)


# --------------------------------------------------------------------------
# guardrail
# --------------------------------------------------------------------------
def _numbers(text: str) -> set[str]:
    found = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    out = set()
    for f in found:
        out.add(f.replace(",", ""))
        out.add(f.replace(",", "").rstrip("0").rstrip("."))
    return {n for n in out if n}


def fact_sheet(tool: str, result: dict) -> set[str]:
    """Every number the tool actually produced, in the forms an answer may cite."""
    allowed = _numbers(json.dumps(result, default=str))
    allowed |= _numbers(answer_from_tool(tool, result))

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            allowed.update(_numbers(f"{value:,.0f}"))
            allowed.update(_numbers(f"{value:.1%}"))
            allowed.update(_numbers(f"{value:.1f}"))
            allowed.update(_numbers(f"{value:.2f}"))

    walk(result)
    return allowed


def unsupported_numbers(text: str, allowed: set[str]) -> list[str]:
    bad = []
    for token in _numbers(text):
        if token in allowed:
            continue
        # tolerate thousands-separated variants and trailing zeros
        if token.rstrip("0").rstrip(".") in allowed:
            continue
        bad.append(token)
    return sorted(bad)


# --------------------------------------------------------------------------
# optional model layer
# --------------------------------------------------------------------------
def llm_configured() -> bool:
    return bool(os.getenv("IAA_LLM_BASE_URL") and os.getenv("IAA_LLM_MODEL"))


def _llm(messages: list[dict], temperature: float = 0.0) -> str:
    base = os.getenv("IAA_LLM_BASE_URL", "").rstrip("/")
    key = os.getenv("IAA_LLM_API_KEY", "")
    model = os.getenv("IAA_LLM_MODEL", "")
    body = json.dumps({"model": model, "messages": messages, "temperature": temperature}).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    req = urllib.request.Request(f"{base}/chat/completions", data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        payload = json.load(resp)
    return payload["choices"][0]["message"]["content"]


def _llm_plan(question: str, toolbox: Toolbox) -> tuple[str, dict] | None:
    system = (
        "You route insurance questions to one tool. Reply with JSON only: "
        '{"tool": "<name>", "args": {...}}. Tools: '
        + json.dumps(toolbox.catalogue())
    )
    try:
        raw = _llm([{"role": "system", "content": system}, {"role": "user", "content": question}])
        match = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(match.group(0)) if match else {}
        name = data.get("tool")
        args = data.get("args") or {}
        if name not in toolbox.tools or not isinstance(args, dict):
            return None
        return name, args
    except Exception:
        return None


def _llm_answer(question: str, tool: str, result: dict) -> str | None:
    system = (
        "Answer using ONLY the JSON result. Never introduce a number that is not in it. "
        "Be concise, plain English, and mention that the underwriter decides."
    )
    try:
        return _llm([
            {"role": "system", "content": system},
            {"role": "user", "content": f"Question: {question}\n\nResult: {json.dumps(result, default=str)}"},
        ])
    except Exception:
        return None


# --------------------------------------------------------------------------
# public entry point
# --------------------------------------------------------------------------
@dataclass
class Answer:
    text: str
    tool: str
    args: dict
    result: Any
    mode: str
    guardrail: str | None = None
    trace: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "text": self.text, "tool": self.tool, "args": self.args, "mode": self.mode,
            "guardrail": self.guardrail, "trace": self.trace, "detail": self.result,
        }


def ask(question: str, toolbox: Toolbox | None = None, use_model: bool | None = None) -> Answer:
    toolbox = toolbox or Toolbox()
    use_model = llm_configured() if use_model is None else use_model

    planned = _llm_plan(question, toolbox) if use_model else None
    mode = "model-planned" if planned else "deterministic"
    tool, args = planned or plan(question, toolbox)

    call = toolbox.call(tool, **args)
    trace = [{"step": "plan", "tool": tool, "args": args, "mode": mode},
             {"step": "execute", "ok": call["ok"]}]

    if not call["ok"]:
        text = f"I can't answer that from the model: {call['error']}. Ask about a policy, a vehicle, the group, or a metric definition."
        return Answer(text, tool, args, None, mode, trace=trace)

    result = call["result"]
    allowed = fact_sheet(tool, result)
    dialogue = _llm_answer(question, tool, result) if use_model else None
    guardrail = None

    if dialogue:
        bad = unsupported_numbers(dialogue, allowed)
        trace.append({"step": "verify", "unsupported": bad})
        if bad:
            guardrail = f"rejected model answer: unsupported numbers {', '.join(bad)}"
            dialogue = None

    text = dialogue or answer_from_tool(tool, result)
    return Answer(text, tool, args, result, mode, guardrail, trace)
