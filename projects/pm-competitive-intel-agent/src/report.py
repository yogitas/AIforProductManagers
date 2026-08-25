"""
Formats the competitive intelligence daily digest into markdown and HTML formats.
Includes structured formatting grouped by competitor.
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple

def generate_markdown_report(
    featured_items: List[Dict[str, Any]],
    extra_items: List[Dict[str, Any]],
    failed_sources: Dict[str, str],
    config: Any,
    pref_summary: str
) -> str:
    """
    Generates a markdown report for the daily digest.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    md = []
    
    # Header
    md.append(f"# Competitive Intelligence Digest - {date_str}")
    md.append(f"**Primary Domain:** {config.domain.primary}")
    if config.domain.focus_subdomain:
        md.append(f"**Focus Subdomain:** `{config.domain.focus_subdomain}` (prioritized with ⭐)")
    md.append("")
    
    # Heuristic Preference Summary (pedagogical visibility)
    md.append("> **Note for PMs:** This digest was ranked utilizing a heuristic Preference Memory.")
    md.append("> It summarizes recent thumbs-up/down selections in-context rather than retraining model weights.")
    md.append("")
    
    # GUARDRAIL: Source isolation failure warning
    # If one competitor fetch failed, we notify the user rather than dropping it silently.
    if failed_sources:
        md.append("> [!WARNING]")
        md.append("> **Discovery Status: Partial Outage**")
        md.append("> The following sources were unavailable during this run. No updates were fetched for them:")
        for source, err in failed_sources.items():
            md.append(f"> - **{source}**: {err}")
        md.append("")
        
    if not featured_items and not extra_items:
        md.append("### No new material updates found today.")
        return "\n".join(md)
        
    # Group featured items by competitor/watchlist category
    grouped_items: Dict[str, List[Dict[str, Any]]] = {}
    for item in featured_items:
        comp = item["competitor"]
        if comp not in grouped_items:
            grouped_items[comp] = []
        grouped_items[comp].append(item)
        
    # Featured updates
    md.append("## Featured Competitor Updates")
    md.append("")
    for competitor, items in grouped_items.items():
        md.append(f"### {competitor}")
        for item in items:
            focus_badge = "⭐ **[FOCUS SUBDOMAIN]** " if item.get("is_focus") else ""
            
            md.append(f"#### {focus_badge}{item['title']}")
            md.append(f"- **Summary:** {item['description']}")
            md.append(f"- **Source:** [Read Full Article]({item['url']})")
            md.append(f"- **Materiality Reason:** *{item.get('materiality_reason', 'N/A')}*")
            md.append("")
            
    # GUARDRAIL: Report size cap
    # Excess items are summarized here in an accordion fold-out to avoid cluttering the primary email view.
    if extra_items:
        md.append("---")
        md.append(f"## Extra Updates (+{len(extra_items)} more items)")
        md.append("To keep your daily digest focused and actionable, the following updates were summarized briefly:")
        md.append("")
        
        for item in extra_items:
            focus_star = "⭐ " if item.get("is_focus") else ""
            md.append(f"- **{focus_star}{item['competitor']}**: [{item['title']}]({item['url']}) - {item['description']}")
            
    # Add active preference memory summary for visibility
    md.append("\n---")
    md.append("### Active Preference Memory Summary")
    md.append("```")
    md.append(pref_summary)
    md.append("```")
    
    return "\n".join(md)

def generate_html_report(
    featured_items: List[Dict[str, Any]],
    extra_items: List[Dict[str, Any]],
    failed_sources: Dict[str, str],
    config: Any,
    pref_summary: str
) -> str:
    """
    Renders the report as an HTML body, suitable for rich email delivery.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # HTML layout styling (minimal, clean styling tailored for email clients)
    html_template = """
    <html>
    <head>
      <style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ border-bottom: 2px solid #3367d6; padding-bottom: 10px; color: #1a73e8; }}
        h2 {{ color: #202124; margin-top: 30px; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px; }}
        h3 {{ color: #202124; margin-top: 20px; }}
        .item {{ margin-bottom: 25px; padding-left: 10px; border-left: 3px solid #f1f3f4; }}
        .item.focus {{ border-left: 3px solid #f4b400; background-color: #fefcf0; padding: 10px; border-radius: 4px; }}
        .badge {{ font-size: 11px; background-color: #f4b400; color: #ffffff; padding: 2px 6px; border-radius: 3px; font-weight: bold; text-transform: uppercase; }}
        .feedback {{ font-size: 12px; margin-top: 8px; color: #666666; }}
        .feedback a {{ text-decoration: none; color: #1a73e8; font-weight: bold; margin-right: 15px; }}
        .warning {{ background-color: #fce8e6; border: 1px solid #fad2cf; padding: 15px; border-radius: 4px; margin-bottom: 20px; color: #c5221f; font-size: 14px; }}
        .pref-box {{ background-color: #f8f9fa; border: 1px solid #e8eaed; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 12px; white-space: pre-wrap; }}
      </style>
    </head>
    <body>
      <h1>Competitive Intelligence Digest - {date}</h1>
      <p><strong>Primary Domain:</strong> {domain}<br/>
      {subdomain_info}</p>
      
      {warnings}
      
      {body_content}
      
      {extra_content}
      
      <h3>Active Preference Memory</h3>
      <div class="pref-box">{pref_summary}</div>
    </body>
    </html>
    """
    
    subdomain_info = f"<strong>Focus Subdomain:</strong> <code>{config.domain.focus_subdomain}</code>" if config.domain.focus_subdomain else ""
    
    warnings = ""
    if failed_sources:
        warnings = '<div class="warning"><strong>Discovery Status: Partial Outage</strong><br/>'
        warnings += "The following sources failed to retrieve updates today:<ul>"
        for src, err in failed_sources.items():
            warnings += f"<li><strong>{src}</strong>: {err}</li>"
        warnings += "</ul></div>"
        
    if not featured_items and not extra_items:
        body_content = "<p>No new material updates found today.</p>"
        return html_template.format(
            date=date_str,
            domain=config.domain.primary,
            subdomain_info=subdomain_info,
            warnings=warnings,
            body_content=body_content,
            extra_content="",
            pref_summary=pref_summary
        )
        
    # Group items
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in featured_items:
        comp = item["competitor"]
        if comp not in grouped:
            grouped[comp] = []
        grouped[comp].append(item)
        
    body_content = "<h2>Featured Competitor Updates</h2>"
    for comp, items in grouped.items():
        body_content += f"<h3>{comp}</h3>"
        for item in items:
            is_focus = item.get("is_focus", False)
            focus_class = "focus" if is_focus else ""
            badge = '<span class="badge">⭐ Focus Subdomain</span><br/>' if is_focus else ""
            
            body_content += f"""
            <div class="item {focus_class}">
              {badge}
              <strong>{item['title']}</strong>
              <p style="margin: 5px 0;">{item['description']}</p>
              <small><strong>Source:</strong> <a href="{item['url']}">{item['url']}</a><br/>
              <strong>Materiality Reason:</strong> <em>{item.get('materiality_reason', 'N/A')}</em></small>
            </div>
            """
            
    extra_content = ""
    if extra_items:
        extra_content = f"<h2>Extra Updates (+{len(extra_items)} more items)</h2><ul>"
        for item in extra_items:
            focus_star = "⭐ " if item.get("is_focus") else ""
            extra_content += f"""
            <li style="margin-bottom: 10px;">
              <strong>{focus_star}{item['competitor']}</strong>: <a href="{item['url']}">{item['title']}</a> - {item['description']}<br/>
            </li>
            """
        extra_content += "</ul>"
        
    return html_template.format(
        date=date_str,
        domain=config.domain.primary,
        subdomain_info=subdomain_info,
        warnings=warnings,
        body_content=body_content,
        extra_content=extra_content,
        pref_summary=pref_summary
    )
