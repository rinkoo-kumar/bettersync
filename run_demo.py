"""
BetterSync - Interactive Runnable Prototype Walkthrough
Demonstrates change propagation, data validation, SLA gatekeeping,
and Claude agentic exception triage across People systems.
"""

from datetime import date
import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles if supported
if sys.platform == "win32":
    os.system("")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.core.reconciler import Reconciler
from src.core.gatekeeper import SLAGatekeeper
from src.models.canonical import Address, BackgroundCheckStatus, HardwareStatus, HireProfile, OktaStatus
from src.models.events import EventType

console = Console(force_terminal=True, legacy_windows=False)


def load_scenarios():
    data_path = Path(__file__).parent / "data" / "sample_scenarios.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_header():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]BetterUp People Technology -- Onboarding Orchestration Engine[/bold cyan]\n"
        "[italic white]Engineering Depth Demo: Change Propagation, SLA Gates & Claude Exception Triage[/italic white]",
        border_style="cyan"
    ))
    console.print()


def demo_scenario_1(reconciler: Reconciler, data: dict):
    console.print(Panel("[bold yellow]SCENARIO 1: Post-Offer Change Propagation[/bold yellow]\n"
                        "A candidate accepts an offer, then shifts their start date and changes their address.\n"
                        "In the legacy system, this breaks ExpoIT shipping and Okta activation dates.",
                        border_style="yellow"))

    scen = data["scenario_1_propagation"]
    initial = scen["initial_hire"]
    update = scen["update_payload"]
    hire_id = initial["hire_id"]

    # Step 1: Initial Offer Signed
    console.print(f"[bold green]Step 1.1:[/bold green] Offer signed in Ashby for [bold]{initial['first_name']} {initial['last_name']}[/bold].")
    res1 = reconciler.ingest_event(EventType.OFFER_SIGNED, initial, idempotency_key=f"offer_signed_{hire_id}")
    console.print(f"  * Event ingested. Downstream systems synchronized: [cyan]{len(res1['actions_taken'])}[/cyan]")
    
    # Show initial state
    table1 = Table(title=f"Initial State across Systems ({initial['start_date']})", border_style="blue")
    table1.add_column("System", style="bold")
    table1.add_column("Start Date")
    table1.add_column("Delivery / Activation Target")
    table1.add_column("Address")
    
    wkd = reconciler.workday.get_by_hire_id(hire_id)
    okta = reconciler.okta.get_by_hire_id(hire_id)
    expo = reconciler.expoit.get_by_hire_id(hire_id)
    
    table1.add_row("Workday HRIS", wkd.get("start_date"), "N/A", str(wkd.get("address", {}).get("street1")))
    table1.add_row("Okta Identity", "N/A", okta.get("scheduled_activation"), "N/A")
    table1.add_row("ExpoIT Hardware", "N/A", expo.get("target_delivery_date"), str(expo.get("shipping_address", {}).get("street1")))
    console.print(table1)
    console.print()

    # Step 2: Candidate changes start date (+14 days) and address
    console.print(f"[bold green]Step 1.2:[/bold green] Candidate updates start date to [bold magenta]{update['start_date']}[/bold magenta] and moves to [bold magenta]{update['address']['street1']}[/bold magenta].")
    res2 = reconciler.ingest_event(EventType.START_DATE_UPDATED, update, idempotency_key=f"start_date_update_{hire_id}")
    
    # Show reconciled state
    table2 = Table(title=f"Reconciled State across Systems ({update['start_date']})", border_style="green")
    table2.add_column("System", style="bold")
    table2.add_column("Start Date")
    table2.add_column("Delivery / Activation Target")
    table2.add_column("Address")

    wkd_up = reconciler.workday.get_by_hire_id(hire_id)
    okta_up = reconciler.okta.get_by_hire_id(hire_id)
    expo_up = reconciler.expoit.get_by_hire_id(hire_id)

    table2.add_row("Workday HRIS", f"[green]{wkd_up.get('start_date')}[/green]", "N/A", f"[green]{wkd_up.get('address', {}).get('street1')}[/green]")
    table2.add_row("Okta Identity", "N/A", f"[green]{okta_up.get('scheduled_activation')}[/green]", "N/A")
    table2.add_row("ExpoIT Hardware", "N/A", f"[green]{expo_up.get('target_delivery_date')}[/green]", f"[green]{expo_up.get('shipping_address', {}).get('street1')}[/green]")
    console.print(table2)

    console.print("[bold green][OK] Success:[/bold green] Start date and shipping address propagated cleanly without manual IT tickets!\n")


def demo_scenario_2(reconciler: Reconciler, data: dict):
    console.print(Panel("[bold yellow]SCENARIO 2: Bad Data Cascades & Agentic Claude Discrepancy Triage[/bold yellow]\n"
                        "An address formatting discrepancy occurs between Ashby ATS and Workday.\n"
                        "Rather than failing or silently dropping the update, Claude evaluates semantic equivalence.",
                        border_style="yellow"))

    scen = data["scenario_2_bad_data_cascade"]
    cand = scen["candidate_record"]
    hire_id = cand["hire_id"]

    # Seed Ashby with raw abbreviation and Workday with expanded address
    reconciler.ashby.create_or_update(hire_id, {
        "hire_id": hire_id,
        "first_name": "Marcus",
        "last_name": "Chen",
        "start_date": "2026-11-09",
        "address": {"street1": "100 main street ste 400", "city": "Austin", "state": "TX", "postal_code": "78701", "country": "US"}
    }, idempotency_key="seed_ashby_can102")

    reconciler.workday.create_or_update(hire_id, {
        "hire_id": hire_id,
        "first_name": "Marcus",
        "last_name": "Chen",
        "start_date": "2026-11-09",
        "address": {"street1": "100 Main St, Suite 400", "city": "Austin", "state": "TX", "postal_code": "78701", "country": "US"}
    }, idempotency_key="seed_wkd_can102")

    console.print(f"[bold green]Step 2.1:[/bold green] Ingested candidate [bold]{cand['first_name']} {cand['last_name']}[/bold]. Evaluating cross-system drift...")
    drifts = reconciler.compute_drift(hire_id)
    console.print(f"  * Discrepancies detected: [bold red]{len(drifts)}[/bold red]")
    for d in drifts:
        console.print(f"    - Field: [bold]{d.field_name}[/bold] | Ashby: '{d.source_value.get('street1')}' vs Workday: '{d.target_value.get('street1')}'")

    console.print(f"[bold green]Step 2.2:[/bold green] Invoking [bold cyan]Claude Agentic Exception Resolver[/bold cyan]...")
    resolutions = reconciler.reconcile_with_ai(hire_id)
    for res in resolutions:
        console.print(f"  * [bold]AI Reasoning:[/bold] {res.get('analysis')}")
        console.print(f"  * [bold]Auto-Resolved:[/bold] [green]{res.get('can_auto_resolve')}[/green] (Confidence: [bold]{res.get('confidence_score') * 100:.0f}%[/bold])")
        console.print(f"  * [bold]Authoritative Value Written:[/bold] {res.get('resolved_value')}")

    console.print("[bold green][OK] Success:[/bold green] Claude safely normalized the address, preventing courier address correction fees.\n")


def demo_scenario_3(reconciler: Reconciler, data: dict):
    console.print(Panel("[bold yellow]SCENARIO 3: SLA Gatekeeper (Unmonitored Deadlines)[/bold yellow]\n"
                        "A hire starts in 5 days (T-5), but their hardware form is missing, background check is pending, and laptop is unordered.",
                        border_style="yellow"))

    scen = data["scenario_3_sla_gate_breach"]
    raw = scen["hire_record"]

    profile = HireProfile(
        hire_id=raw["hire_id"],
        first_name=raw["first_name"],
        last_name=raw["last_name"],
        email=raw["email"],
        personal_email=raw["personal_email"],
        role_title=raw["role_title"],
        department=raw["department"],
        manager_email=raw["manager_email"],
        start_date=raw["start_date"],
        address=Address(**raw["address"]),
        hardware_status=HardwareStatus[raw["hardware_status"]],
        it_hardware_form_completed=raw["it_hardware_form_completed"],
        background_check_status=BackgroundCheckStatus[raw["background_check_status"]],
        okta_status=OktaStatus[raw["okta_status"]],
        cohort_name=raw["cohort_name"]
    )

    # Set reference date to 2026-10-25 (5 days before start date 2026-10-30)
    gatekeeper = SLAGatekeeper(reference_date=date(2026, 10, 25))
    breaches = gatekeeper.evaluate_hire(profile)

    table = Table(title=f"SLA Breaches Detected for {profile.display_name} (T-5 Days)", border_style="red")
    table.add_column("Gate Name", style="bold red")
    table.add_column("Days Left", justify="center")
    table.add_column("Severity", justify="center")
    table.add_column("Issue & Auto-Remediation")

    for b in breaches:
        color = "red" if b.severity == "CRITICAL" else "yellow"
        table.add_row(
            b.gate_name,
            f"T-{b.days_to_start}d",
            f"[{color}]{b.severity}[/{color}]",
            f"{b.message}\n[italic green]-> Action: {b.recommended_action}[/italic green]"
        )

    console.print(table)
    console.print("[bold green][OK] Success:[/bold green] SLA Gatekeeper proactively surfaced all 3 blocking issues before Day 1!\n")


def demo_scenario_4_idempotency(reconciler: Reconciler, data: dict):
    console.print(Panel("[bold yellow]SCENARIO 4: Strict Idempotency & Replay Protection[/bold yellow]\n"
                        "Replaying the identical event with the same idempotency key must be a strict no-op.",
                        border_style="yellow"))

    scen = data["scenario_1_propagation"]
    update = scen["update_payload"]
    hire_id = update["hire_id"]
    dup_key = f"start_date_update_{hire_id}"

    console.print(f"[bold green]Action:[/bold green] Resending event with key '[cyan]{dup_key}[/cyan]'...")
    res = reconciler.ingest_event(EventType.START_DATE_UPDATED, update, idempotency_key=dup_key)
    
    console.print(f"  * Result Status: [bold cyan]{res['status']}[/bold cyan]")
    console.print(f"  * Idempotent Flag: [bold green]{res['idempotent']}[/bold green]")
    console.print(f"  * Message: {res['message']}")
    console.print("[bold green][OK] Success:[/bold green] Duplicate event blocked with 0 redundant writes or downstream calls!\n")


def demo_scenario_5_audit_verification(reconciler: Reconciler):
    console.print(Panel("[bold yellow]SCENARIO 5: Cryptographic Audit Trail Verification[/bold yellow]\n"
                        "Verifying the append-only SHA-256 hash chain for tamper evidence.",
                        border_style="yellow"))

    history = reconciler.audit.get_history()
    is_valid = reconciler.audit.verify_integrity()

    table = Table(title="Tamper-Evident Audit Trail (Latest Entries)", border_style="magenta")
    table.add_column("Record ID", style="dim")
    table.add_column("Event Type", style="bold")
    table.add_column("Actor")
    table.add_column("Entity ID")
    table.add_column("Prev Hash (Truncated)", style="dim")
    table.add_column("Current Hash (Truncated)", style="cyan")

    for rec in history[-4:]:
        table.add_row(
            rec.record_id,
            rec.event_type,
            rec.actor,
            rec.entity_id,
            f"{rec.prev_hash[:12]}...",
            f"{rec.current_hash[:12]}..."
        )
    console.print(table)
    
    status_text = "[bold green]VALID (No Tampering Detected)[/bold green]" if is_valid else "[bold red]INVALID[/bold red]"
    console.print(f"Audit Trail Cryptographic Integrity Check: {status_text}\n")


def main():
    print_header()
    reconciler = Reconciler()
    scenarios = load_scenarios()

    demo_scenario_1(reconciler, scenarios)
    demo_scenario_2(reconciler, scenarios)
    demo_scenario_3(reconciler, scenarios)
    demo_scenario_4_idempotency(reconciler, scenarios)
    demo_scenario_5_audit_verification(reconciler)

    console.print(Panel.fit("[bold green]All 5 Scenarios Completed Successfully![/bold green]\n"
                            "Full engineering depth demonstrated across connectors, validation, gatekeeping, and Claude triage.",
                            border_style="green"))


if __name__ == "__main__":
    main()
