#!/usr/bin/env python3
"""
Generate graph visualization data from backlinks.json

Transforms RemNote-style backlinks into D3.js-compatible graph format
with additional metrics (PageRank, clustering, centrality)
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
import sys

try:
    import networkx as nx
except ImportError:
    print("Error: networkx not installed. Run: pip install networkx")
    sys.exit(1)

ISCED_TO_DOMAIN = {
    '01': 'education', '02': 'humanities', '03': 'social-sciences',
    '04': 'business-law', '05': 'natural-sciences', '06': 'ict',
    '07': 'engineering', '08': 'agriculture', '09': 'health', '10': 'services'
}

SUBDOMAIN_MAP = {
    'equity': 'business-law', 'fixed-income': 'business-law',
    'derivatives': 'business-law', 'fx': 'business-law',
    'commodities': 'business-law', 'credit': 'business-law',
    'rates': 'business-law', 'finance': 'business-law',
    'banking': 'business-law', 'law': 'business-law', 'legal': 'business-law',
    'economics': 'social-sciences', 'sociology': 'social-sciences',
    'politics': 'social-sciences',
    'python': 'ict', 'csharp': 'ict', 'javascript': 'ict',
    'programming': 'ict', 'software': 'ict', 'computer': 'ict',
    'french': 'humanities', 'english': 'humanities', 'chinese': 'humanities',
    'spanish': 'humanities', 'language': 'humanities',
    'linguistics': 'humanities', 'literature': 'humanities',
    'history': 'humanities', 'philosophy': 'humanities',
    'pedagogy': 'education', 'teaching': 'education',
    'physics': 'natural-sciences', 'chemistry': 'natural-sciences',
    'mathematics': 'natural-sciences', 'biology': 'natural-sciences',
    'engineering': 'engineering', 'mechanical': 'engineering',
    'electrical': 'engineering',
    'agriculture': 'agriculture', 'farming': 'agriculture',
    'medicine': 'health', 'nursing': 'health', 'healthcare': 'health',
    'hospitality': 'services', 'tourism': 'services', 'transport': 'services'
}

DOMAIN_COLORS = {
    'education': '#e67e22', 'humanities': '#f39c12',
    'social-sciences': '#34495e', 'business-law': '#3498db',
    'natural-sciences': '#1abc9c', 'ict': '#2ecc71',
    'engineering': '#16a085', 'agriculture': '#27ae60',
    'health': '#9b59b6', 'services': '#95a5a6', 'generic': '#bdc3c7'
}

RELATION_TYPE_COLORS = {
    'prerequisite_of': '#e74c3c', 'uses': '#3498db',
    'example_of': '#2ecc71', 'contrasts_with': '#f39c12',
    'synonym': '#9b59b6', 'component_of': '#1abc9c',
    'analogous_to': '#e67e22', 'linked-from-example_of': '#2ecc71',
    'linked-from-used_in': '#3498db', 'reference': '#95a5a6',
    'inferred': '#d0d0d0'
}


def load_backlinks(path):
    """Load backlinks.json from disk."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _domain_from_isced(isced):
    m = re.match(r'(\d{2})', isced)
    return ISCED_TO_DOMAIN.get(m.group(1), '') if m else ''


def _domain_from_path(fp):
    for pat in [r'knowledge-base/(\d{2})-', r'/(\d{2})-[^/]+/', r'/(\d{3})-', r'/(\d{4})-']:
        m = re.search(pat, fp)
        if not m:
            continue
        d = ISCED_TO_DOMAIN.get(m.group(1)[:2])
        if d:
            return d
    return ''


def extract_isced_domain(fp, fm):
    """Extract domain from ISCED, file path, or subdomain."""
    r = _domain_from_isced(fm.get('isced', ''))
    if r:
        return r
    r = _domain_from_path(fp)
    if r:
        return r
    sub = fm.get('subdomain', '').lower()
    for kw, dom in SUBDOMAIN_MAP.items():
        if kw in sub:
            return dom
    return 'generic'


def _parse_frontmatter(content):
    """Parse YAML frontmatter, return (dict, body)."""
    if not content.startswith('---'):
        return {}, content
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    fm = {}
    for line in parts[1].split('\n'):
        line = line.strip()
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key, val = key.strip(), val.strip()
        if key == 'tags' and val.startswith('[') and val.endswith(']'):
            fm[key] = [t.strip().strip('"\'') for t in val[1:-1].split(',') if t.strip()]
        else:
            fm[key] = val
    return fm, parts[2].strip()


def _extract_section(lines, heading):
    """Extract text under a ## heading until next heading."""
    result, active = [], False
    for line in lines:
        if line.strip() == f'## {heading}':
            active = True
        elif line.startswith('## ') and active:
            break
        elif active and line.strip():
            result.append(line.strip())
    return '\n'.join(result)


def _extract_excerpt(lines, max_chars=2000):
    """Extract first 5 exchanges from Full Conversation."""
    out, active, turns, chars = [], False, 0, 0
    for line in lines:
        if line.strip() == '## Full Conversation':
            active = True
            continue
        if not active:
            continue
        if line.startswith('###'):
            turns += 1
        if turns > 10:
            break
        out.append(line)
        chars += len(line)
        if chars > max_chars:
            out.append('\n\n*(Conversation continues...)*')
            break
    return '\n'.join(out).strip()


def _extract_full_conv(lines):
    """Extract everything after ## Full Conversation."""
    result, active = [], False
    for line in lines:
        if line.strip() == '## Full Conversation':
            active = True
            continue
        if active:
            result.append(line)
    return '\n'.join(result).strip()


def extract_conversation_content(conv_path):
    """Extract structured content from a conversation file."""
    try:
        p = Path(conv_path)
        if not p.exists():
            return {}
        fm, body = _parse_frontmatter(p.read_text(encoding='utf-8'))
        lines = body.split('\n')
        tags = fm.get('tags', [])
        return {
            'summary': _extract_section(lines, 'Summary'),
            'tags': tags if isinstance(tags, list) else [],
            'date': fm.get('date', ''),
            'excerpt': _extract_excerpt(lines),
            'content': _extract_full_conv(lines)
        }
    except Exception as e:
        print(f"Warning: {conv_path}: {e}", file=sys.stderr)
        return {}


def _extract_title(body):
    for line in body.split('\n'):
        if line.strip().startswith('# '):
            return line.strip()[2:].strip()
    return ''


def _build_conv_link(source):
    """Build conversation link from frontmatter source field."""
    source = source.replace('../', '')
    if not source.startswith('chats/'):
        return {}
    conv = extract_conversation_content(source)
    name = Path(source).stem
    return {
        'title': name.replace('-conversation-', ' - ').replace('-', ' ').title(),
        'path': source, 'date': conv.get('date', ''),
        'summary': conv.get('summary', ''), 'tags': conv.get('tags', []),
        'excerpt': conv.get('excerpt', ''), 'content': conv.get('content', '')
    }


def _body_conv_link(body):
    """Extract conversation link from legacy body format."""
    active = False
    for line in body.split('\n'):
        if line.startswith('## Conversation Source'):
            active = True
            continue
        if line.startswith('## ') and active:
            break
        if not active:
            continue
        if '> See:' not in line and '\u2192 See:' not in line:
            continue
        m = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', line)
        if not m:
            continue
        path = m.group(2).replace('../', '')
        conv = extract_conversation_content(path)
        return {
            'title': m.group(1), 'path': path,
            'date': conv.get('date', ''), 'summary': conv.get('summary', ''),
            'tags': conv.get('tags', []), 'excerpt': conv.get('excerpt', ''),
            'content': conv.get('content', '')
        }
    return {}


def _filter_body(body):
    """Remove Conversation Source and Related Rems sections."""
    lines, skip = [], False
    for line in body.split('\n'):
        if line.startswith('## Conversation Source') or line.startswith('## Related Rems'):
            skip = True
        elif line.startswith('## ') and skip:
            skip = False
        if not skip:
            lines.append(line)
    return '\n'.join(lines).strip()


def _resolve_isced(fm, fp):
    """Resolve ISCED code from frontmatter or file path."""
    isced = fm.get('isced', '')
    if not isced:
        m = re.search(r'/(\d{2,4})-([^/]+)/', fp)
        if m:
            isced = m.group(0).strip('/')
    return isced


def _process_concept(cf, kb_path, metadata):
    """Process one concept file into metadata dict."""
    try:
        content = cf.read_text(encoding='utf-8')
    except Exception:
        return
    if not content.startswith('---'):
        return
    fm, body = _parse_frontmatter(content)
    rem_id = fm.get('rem_id')
    if not rem_id:
        return
    fp = str(cf.relative_to(kb_path.parent))
    isced = _resolve_isced(fm, fp)
    subdomain = fm.get('subdomain', '')
    tags = fm.get('tags', [])
    tags = [tags] if isinstance(tags, str) else tags
    source = fm.get('source')
    domain = extract_isced_domain(fp, {'isced': isced, 'subdomain': subdomain})
    fc = (_build_conv_link(source) if source else {}) or _body_conv_link(body)
    if not tags and fc.get('tags'):
        tags = fc['tags']
    metadata[rem_id] = {
        'title': _extract_title(body) or rem_id, 'domain': domain,
        'isced': isced, 'subdomain': subdomain, 'tags': tags,
        'file': fp, 'content': _filter_body(body),
        'conversation': fc if fc else None
    }


def load_concept_metadata(kb_path):
    """Load metadata from all concept files."""
    metadata = {}
    for cf in kb_path.rglob('**/*.md'):
        if cf.name.startswith('_') or '/_templates/' in str(cf):
            continue
        _process_concept(cf, kb_path, metadata)
    return metadata


def load_review_stats():
    """Load FSRS review statistics from schedule.json."""
    path = Path('.review/schedule.json')
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        schedule = json.load(f)
    stats = {}
    for rid, rd in schedule.get('concepts', {}).items():
        fs = rd.get('fsrs_state', {})
        stats[rid] = {
            'review_count': fs.get('review_count') or 0,
            'stability': round(fs.get('stability', 0), 2),
            'difficulty': round(fs.get('difficulty', 0), 2),
            'last_reviewed': rd.get('last_reviewed', ''),
            'next_review': fs.get('next_review', '')
        }
    return stats


def _truncate(text, max_chars):
    """Truncate text to max_chars at word boundary."""
    if not text or len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + '...'


def _truncate_convs(convs):
    """Truncate conversation fields to reduce JSON size."""
    return [
        {'title': c.get('title', ''), 'path': c.get('path', ''),
         'date': c.get('date', ''), 'tags': c.get('tags', []),
         'summary': _truncate(c.get('summary', ''), 500),
         'excerpt': _truncate(c.get('excerpt', ''), 300),
         'content': c.get('content', '')}
        for c in convs if c
    ]


def _collect_neighbors(info, cid, metas):
    """Collect unique neighbor IDs from all link types for a concept."""
    nb = set()
    for tl in info.get('typed_links_to', []):
        t = tl.get('to') if isinstance(tl, dict) else tl
        if t and t in metas and t != cid:
            nb.add(t)
    for t in info.get('links_to', []):
        if t and t in metas and t != cid:
            nb.add(t)
    for il in info.get('inferred_links_to', []):
        t = il.get('to') if isinstance(il, dict) else il
        if t and t in metas and t != cid:
            nb.add(t)
    for s in info.get('linked_from', []):
        if s and s in metas and s != cid:
            nb.add(s)
    for tlf in info.get('typed_linked_from', []):
        s = tlf.get('from') if isinstance(tlf, dict) else tlf
        if s and s in metas and s != cid:
            nb.add(s)
    return nb


def _count_connections(metas, ld):
    """Count unique neighbors per concept."""
    return {cid: len(_collect_neighbors(ld.get(cid, {}), cid, metas)) for cid in metas}


def _add_typed_edges(info, src, metas, edges, seen):
    """Add typed link edges for a source node."""
    clr = lambda t: RELATION_TYPE_COLORS.get(t, '#999')
    for tl in info.get('typed_links_to', []):
        tgt, lt = (tl.get('to'), tl.get('type', 'reference')) if isinstance(tl, dict) else (tl, 'reference')
        key = (src, tgt, lt)
        if tgt and tgt in metas and key not in seen:
            edges.append({'source': src, 'target': tgt, 'type': lt, 'weight': 2.5, 'color': clr(lt), 'dashed': False, 'bidirectional': False})
            seen.add(key)


def _add_ref_edges(info, src, ld, metas, edges, seen):
    """Add reference link edges for a source node."""
    clr = RELATION_TYPE_COLORS.get('reference', '#999')
    for tgt in info.get('links_to', []):
        key = (src, tgt, 'reference')
        if tgt and tgt in metas and key not in seen:
            bidir = src in ld.get(tgt, {}).get('links_to', [])
            edges.append({'source': src, 'target': tgt, 'type': 'reference', 'weight': 1.0, 'color': clr, 'dashed': False, 'bidirectional': bidir})
            seen.add(key)


def _add_inferred_edges(info, src, metas, edges, seen):
    """Add inferred link edges for a source node."""
    clr = RELATION_TYPE_COLORS.get('inferred', '#999')
    for il in info.get('inferred_links_to', []):
        tgt = il.get('to') if isinstance(il, dict) else il
        key = (src, tgt, 'inferred')
        if tgt and tgt in metas and key not in seen:
            edges.append({'source': src, 'target': tgt, 'type': 'inferred', 'weight': 0.5, 'color': clr, 'dashed': True, 'bidirectional': False})
            seen.add(key)


def _build_edges(ld, metas):
    """Build edge list from links data."""
    edges, seen = [], set()
    for src, info in ld.items():
        if src not in metas:
            continue
        _add_typed_edges(info, src, metas, edges, seen)
        _add_ref_edges(info, src, ld, metas, edges, seen)
        _add_inferred_edges(info, src, metas, edges, seen)
    return edges


def _build_nodes(metas, concepts, rstats, conn):
    """Build node list from concept metadata."""
    nodes = []
    for cid, m in metas.items():
        dom = m.get('domain', 'generic')
        s = rstats.get(cid, {})
        title = m.get('title') or concepts.get(cid, {}).get('title', cid)
        rc = [m.get('conversation')] if m.get('conversation') else []
        nodes.append({
            'id': cid, 'label': title, 'isced': m.get('isced', ''),
            'subdomain': m.get('subdomain', ''), 'domain': dom,
            'color': DOMAIN_COLORS.get(dom, DOMAIN_COLORS['generic']),
            'size': 8 + (4 * (1 + conn.get(cid, 0)) ** 0.5),
            'reviewCount': s.get('review_count', 0),
            'stability': s.get('stability', 0),
            'difficulty': s.get('difficulty', 0),
            'lastReviewed': s.get('last_reviewed', ''),
            'nextReview': s.get('next_review', ''),
            'connections': conn.get(cid, 0),
            'tags': m.get('tags', []), 'file': m.get('file', ''),
            'content': _truncate(m.get('content', ''), 500),
            'conversations': _truncate_convs(rc)
        })
    return nodes


def transform_to_graph_format(bd, cm, domain_filter=None):
    """Transform backlinks to D3.js graph format."""
    ld = bd.get('links', {})
    cd = bd.get('concepts', {})
    rs = load_review_stats()
    if domain_filter:
        cm = {k: v for k, v in cm.items() if v.get('domain') == domain_filter}
        ld = {k: ld[k] for k in cm if k in ld}
    conn = _count_connections(cm, ld)
    nodes = _build_nodes(cm, cd, rs, conn)
    edges = _build_edges(ld, cm)
    dc = {}
    for n in nodes:
        dc[n['domain']] = dc.get(n['domain'], 0) + 1
    return {
        'nodes': nodes, 'edges': edges,
        'metadata': {
            'nodeCount': len(nodes), 'edgeCount': len(edges),
            'domainFilter': domain_filter, 'domainDistribution': dc,
            'relationTypeColors': RELATION_TYPE_COLORS,
            'generated': datetime.now().isoformat()
        }
    }


def _run_generation(args):
    """Core generation logic."""
    bp = Path('knowledge-base/_index/backlinks.json')
    if not bp.exists():
        print(f"Error: backlinks.json not found at {bp.absolute()}")
        sys.exit(1)
    op = Path(args.output)
    if not args.force and op.exists():
        if op.stat().st_mtime > bp.stat().st_mtime:
            print("Using cached graph data. Use --force to regenerate")
            return
    bd = load_backlinks(bp)
    cm = load_concept_metadata(Path('knowledge-base'))
    if not cm:
        print("Error: No concepts found in knowledge base")
        sys.exit(1)
    gd = transform_to_graph_format(bd, cm, args.domain)
    if gd['metadata']['nodeCount'] == 0:
        print(f"Error: No concepts match filter (domain={args.domain})")
        sys.exit(1)
    op.parent.mkdir(parents=True, exist_ok=True)
    with open(op, 'w', encoding='utf-8') as f:
        json.dump(gd, f, indent=2)
    _print_summary(gd, args, op)


def _print_summary(gd, args, op):
    """Print generation summary."""
    md = gd['metadata']
    print(f"Graph data generated: {md['nodeCount']} nodes, {md['edgeCount']} edges")
    dd = md.get('domainDistribution', {})
    if dd:
        top = ', '.join(f'{d}({c})' for d, c in sorted(dd.items(), key=lambda x: -x[1])[:5])
        print(f"  Domains: {top}")
    if args.domain:
        print(f"  Filter: {args.domain}")
    print(f"  Output: {op}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Generate graph visualization data')
    parser.add_argument('--domain', type=str, help='Filter by domain')
    parser.add_argument('--output', type=str, default='knowledge-base/_index/graph-data.json')
    parser.add_argument('--force', action='store_true', help='Force regeneration')
    _run_generation(parser.parse_args())


if __name__ == '__main__':
    main()
