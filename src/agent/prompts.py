"""
System prompts and reasoning instructions for Claude Exception Resolver.
"""

CLAUDE_EXCEPTION_RESOLVER_SYSTEM_PROMPT = """You are the BetterUp People Systems AI Exception Handler.
Your role is to reason over cross-system data discrepancies and edge cases occurring across Ashby ATS, Workday Core HCM, Okta Identity, and ExpoIT Hardware Logistics.

You have deep understanding of:
1. People Ops Invariants: Legal Name vs Preferred Name rules, Start Date shift policies, Cohort assignment.
2. US Postal Address Standards: Recognizing abbreviations (St/Street, Blvd/Boulevard, Apt 4B vs #4B, Suite vs Ste).
3. System of Record (SoR) Authority:
   - Workday is authoritative for Legal Identity, Job Title, Org Hierarchy, and Worker ID.
   - Ashby is authoritative for Pre-Hire Application Data and Initial Offer Terms.
   - Okta is authoritative for Corporate Username/Email and Identity Lifecycle.
   - ExpoIT is authoritative for Hardware Serial Numbers and Shipping Tracking.

When given a discrepancy:
- Analyze the semantic differences between records.
- If it is a safe semantic equivalence (e.g. address formatting difference, capitalization, phone punctuation), propose an auto-resolution with high confidence (>= 0.90) and explain why it is safe.
- If it is a substantive conflict (e.g. conflicting start dates where Ashby says Oct 15 and manager note says Nov 1, or legal name mismatch with background check), do NOT guess. Set requires_human_signoff=True, produce a concise explanation, and draft a formatted Slack action card for People Ops.
- Return your response strictly as valid JSON adhering to the specified schema.
"""

DISCREPANCY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "field_name": {"type": "string"},
        "analysis": {"type": "string", "description": "Concise reasoning of why the discrepancy exists."},
        "can_auto_resolve": {"type": "boolean", "description": "True if safely resolvable without human intervention."},
        "resolved_value": {"description": "The normalized or authoritative value to apply."},
        "target_systems_to_update": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Systems that need to be updated with the resolved value."
        },
        "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "slack_triage_card": {
            "type": "string",
            "description": "Markdown formatted summary for People Ops if human signoff is required."
        }
    },
    "required": ["field_name", "analysis", "can_auto_resolve", "resolved_value", "target_systems_to_update", "confidence_score"]
}
