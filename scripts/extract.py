"""
extract.py - Extrae datos de CV desde archivos .adoc de guia-laboral
y genera src/data/portfolio.json con merge inteligente.

Uso:
  py scripts/extract.py
  python3 scripts/extract.py

Requiere: Python 3.8+
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


# ─── Config ───────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_FILE = PROJECT_DIR / "src" / "data" / "portfolio.json"

# Buscar guia-laboral como sibling (mismo directorio padre)
GUIALAB_DIR = PROJECT_DIR.parent / "guia-laboral"
if not GUIALAB_DIR.exists():
    GUIALAB_DIR = PROJECT_DIR.parent / ".." / "guia-laboral"
if not GUIALAB_DIR.exists():
    print("WARNING: guia-laboral/ no encontrado. Usando datos existentes.", file=sys.stderr)
    GUIALAB_DIR = None

CV_FILES = ["cv-es.adoc", "cv-en.adoc"] if GUIALAB_DIR else []


# ─── Helpers de parseo .adoc ─────────────────────────────────────────

def parse_adoc(filepath: Path) -> dict:
    """Parsea un archivo .adoc y extrae su estructura en un dict."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    doc: dict[str, Any] = {
        "title": "",
        "subtitle": "",
        "personal": {},
        "sections": [],
    }

    current_section: Optional[dict] = None
    current_subsection: Optional[dict] = None
    current_subsubsection: Optional[dict] = None
    in_bullets: list[list[str]] = []

    def flush_bullets(target: Optional[dict], key: str = "items"):
        nonlocal in_bullets
        if in_bullets and target is not None:
            flat = []
            for group in in_bullets:
                flat.extend(group)
            if flat:
                target[key] = target.get(key, []) + flat
            in_bullets = []

    for raw in lines:
        line = raw.rstrip()

        # Saltar líneas de atributos AsciiDoc
        if line.startswith(":") and ":" in line[1:]:
            continue

        # Título H1
        if line.startswith("# ") and not line.startswith("##"):
            if doc["title"]:
                continue
            doc["title"] = line[2:].strip()
            continue

        # Subtítulo itálico
        if line.startswith("_*") and line.endswith("*_"):
            doc["subtitle"] = line.strip("_* ")
            continue

        # Título H2 (##) - Sección principal
        if line.startswith("## ") and not line.startswith("### ") and not line.startswith("#### "):
            flush_bullets(current_subsubsection)
            flush_bullets(current_subsection)
            flush_bullets(current_section)
            name = line.lstrip("# ").strip()
            current_section = {"name": name, "subsections": []}
            doc["sections"].append(current_section)
            current_subsection = None
            current_subsubsection = None
            continue

        # Título H3 (###) - Subsección
        if line.startswith("### ") and not line.startswith("#### "):
            flush_bullets(current_subsubsection)
            flush_bullets(current_subsection)
            name = line.lstrip("# ").strip()
            current_subsection = {"name": name, "items": []}
            if current_section is not None:
                current_section["subsections"].append(current_subsection)
            current_subsubsection = None
            continue

        # Título H4 (####) - Sub-subsección (logros, etc.)
        if line.startswith("#### "):
            flush_bullets(current_subsubsection)
            name = line.lstrip("# ").strip()
            current_subsubsection = {"name": name, "items": []}
            if current_subsection is not None:
                current_subsection.setdefault("subsections", []).append(current_subsubsection)
            continue

        # Información personal (líneas con *Key*: Value)
        if current_section and current_section["name"] in ("Sobre Mí", "About", "Información Personal", "Personal Information"):
            m = re.match(r'\s*-\s+\*(\w+)\*:\s*(.+)', line)
            if m:
                doc["personal"][m.group(1).lower()] = m.group(2).strip()
                continue

        # Bullet points ( - o * )
        bullet_match = re.match(r'\s*[-*]\s+(.*)', line)
        if bullet_match:
            text = bullet_match.group(1).strip()
            # Saltar si es solo un link
            if text.startswith("*Link*") or text.startswith("*Website*"):
                continue
            in_bullets.append([text])
            continue

        # Stack tecnológico
        stack_match = re.match(r'.*_Stack_\s*:\s*(.+)', line)
        if stack_match:
            text = f"Stack: {stack_match.group(1).strip()}"
            in_bullets.append([text])
            continue

        # Texto suelto que no es encabezado ni bullet
        stripped = line.strip()
        if stripped and not stripped.startswith("toc::") and not stripped.startswith("```"):
            if current_subsubsection:
                current_subsubsection.setdefault("items", []).append(stripped)
            elif current_subsection:
                current_subsection.setdefault("items", []).append(stripped)

    flush_bullets(current_subsubsection)
    flush_bullets(current_subsection)
    flush_bullets(current_section)

    return doc


# ─── Transformación a JSON portfolio ─────────────────────────────────

def doc_to_portfolio(docs: list[dict]) -> dict:
    """Convierte documentos .adoc parseados a estructura portfolio.json."""
    portfolio: dict[str, Any] = {
        "personal": {},
        "summary": "",
        "experience": [],
        "projects": [],
        "skills": [],
        "education": [],
        "certifications": [],
        "volunteer": [],
        "testimonials": [],
    }

    def _dedup_add(items: list[dict], new: dict, keys: list[str]):
        """Agrega `new` solo si no existe ya un item con mismos `keys`."""
        for existing in items:
            if all(existing.get(k) == new.get(k) for k in keys if k in existing and k in new):
                return
        items.append(new)

    # Fusionar datos de ambos docs (español tiene prioridad)
    for doc in docs:
        personal = doc.get("personal", {})
        if personal.get("city"):
            portfolio.setdefault("personal", {})
            loc = personal.get("city", "")
            portfolio["personal"]["location"] = loc
        if personal.get("phone"):
            portfolio["personal"]["phone"] = personal["phone"]
        if personal.get("email"):
            portfolio["personal"]["email"] = personal["email"]
        if personal.get("github"):
            portfolio["personal"]["github"] = personal["github"]
        if personal.get("linkedin"):
            portfolio["personal"]["linkedin"] = personal["linkedin"]
        if personal.get("portafolio") or personal.get("portfolio"):
            portfolio["personal"]["portfolio"] = personal.get("portafolio") or personal.get("portfolio")

        # Summary (primeros párrafos de "Sobre Mí" / "About")
        for sec in doc["sections"]:
            if sec["name"] in ("Sobre Mí", "About"):
                items = sec.get("items", [])
                if items and not portfolio["summary"]:
                    portfolio["summary"] = items[0] if items else ""
                for sub in sec.get("subsections", []):
                    if sub["name"] in ("Información Personal", "Personal Information"):
                        pass

            # Experiencia
            elif sec["name"] in ("Experiencia", "Experience", "Experiencia Laboral", "Work Experience"):
                for sub in sec.get("subsections", []):
                    exp = _parse_experience(sub)
                    if exp:
                        _dedup_add(portfolio["experience"], exp, ["company", "role"])

            # Proyectos
            elif sec["name"] in ("Proyectos", "Projects", "Proyectos Personales"):
                for sub in sec.get("subsections", []):
                    proj = _parse_project(sub)
                    if proj:
                        _dedup_add(portfolio["projects"], proj, ["name"])

            # Educación
            elif sec["name"] in ("Educación", "Education"):
                for sub in sec.get("subsections", []):
                    edu = _parse_education(sub)
                    if edu:
                        _dedup_add(portfolio["education"], edu, ["institution"])

            # Certificaciones
            elif sec["name"] in ("Licencias y Certificaciones", "Licenses and Certifications"):
                for item in sec.get("items", []):
                    cert = _parse_certification(item)
                    if cert:
                        _dedup_add(portfolio["certifications"], cert, ["name"])

            # Voluntariado
            elif sec["name"] in ("Experiencia Voluntaria", "Volunteer Experience"):
                for sub in sec.get("subsections", []):
                    vol = _parse_volunteer(sub)
                    if vol:
                        _dedup_add(portfolio["volunteer"], vol, ["organization"])

            # Skills (de Specialties, _Specialties_ etc.)
            elif sec["name"] in ("Habilidades Técnicas", "Skills"):
                pass

    return portfolio


def _parse_experience(sub: dict) -> Optional[dict]:
    """Parsea una subsección de experiencia."""
    name = sub.get("name", "").strip()
    if not name:
        return None

    exp = {
        "company": name,
        "description": None,
        "role": "",
        "period": "",
        "stack": [],
        "highlights": [],
        "media": {"logo": None},
    }

    # La descripción suele ser el primer item (párrafo suelto)
    items = sub.get("items", [])
    if items:
        first = items[0].strip()
        # Si no parece un campo estructurado, es la descripción
        if first and not first.startswith("Stack:") and not first.startswith("**"):
            exp["description"] = first

    # Buscar role y periodo en items
    for item in items:
        if item.startswith("Stack:"):
            exp["stack"] = [s.strip() for s in item[6:].split(",")]
        elif item.startswith("-"):
            exp["highlights"].append(item.lstrip("- ").strip())

    # Parsear role/period desde subsubsections (#### Rol (Periodo))
    for ss in sub.get("subsections", []):
        ss_name = ss.get("name", "").strip()
        m = re.match(r'(.+?)\s*\((.+?)\)', ss_name)
        if m:
            exp["role"] = m.group(1).strip()
            exp["period"] = m.group(2).strip()
        ss_name_lower = ss_name.lower()
        if "logro" in ss_name_lower or "achievement" in ss_name_lower:
            for item in ss.get("items", []):
                exp["highlights"].append(item.lstrip("- ").strip())

    return exp


def _parse_project(sub: dict) -> Optional[dict]:
    """Parsea una subsección de proyecto."""
    name = sub.get("name", "").strip()
    if not name:
        return None

    proj = {
        "name": name,
        "status": "completed",
        "featured": False,
        "stack": [],
        "description": "",
        "achievement": None,
        "image": None,
        "videoUrl": None,
        "demoUrl": None,
        "githubUrl": None,
        "presentationUrl": None,
    }

    # Palabras clave que indican campos estructurados, no descripción
    FIELD_PREFIXES = ("*Link*", "*Presentación*", "*Video Demo*", "*Deploy*", "**Stack**",
                      "**APIs**", "**AI**", "**Logro**", "**Nota**", "**Grade**",
                      "**Descripción**", "**Description**", "**Fecha**", "**Date**",
                      "Stack:", "Link", "https://", "http://")

    for item in sub.get("items", []):
        # Stack
        if item.startswith("Stack:") or item.startswith("**Stack**"):
            stack_str = item.split(":", 1)[1].strip().strip("**").strip()
            proj["stack"] = [s.strip() for s in stack_str.split(",")]
        # GitHub link
        elif "github.com" in item.lower():
            m = re.search(r'https://github\.com/\S+', item)
            if m:
                proj["githubUrl"] = m.group(0)
            # Si no hay match, puede ser deploy url
            urls = re.findall(r'https?://\S+', item)
            for url in urls:
                if "github" not in url.lower() and "drive" not in url.lower():
                    proj["demoUrl"] = url
        # Link de presentación
        elif item.startswith("*Presentación*") or item.startswith("*Presentation*") or item.startswith("Presentación"):
            urls = re.findall(r'https?://\S+', item)
            if urls:
                proj["presentationUrl"] = urls[0]
        # Video demo
        elif item.startswith("*Video Demo*") or item.startswith("*Video*"):
            urls = re.findall(r'https?://\S+', item)
            if urls:
                proj["videoUrl"] = urls[0]
        # Deploy / demo URL
        elif item.startswith("*Deploy*") or item.startswith("Deploy"):
            urls = re.findall(r'https?://\S+', item)
            for url in urls:
                if "github" not in url.lower() and "drive" not in url.lower():
                    proj["demoUrl"] = url
        # Achievement (logro/nota)
        elif item.startswith("**Logro**") or item.startswith("**Nota**") or item.startswith("**Grade**"):
            proj["achievement"] = item.split(":", 1)[1].strip() if ":" in item else item
        elif "logro" in item.lower() or "achievement" in item.lower() or "nota" in item.lower() or "grade" in item.lower():
            if not any(item.startswith(p) for p in FIELD_PREFIXES):
                proj["achievement"] = item.split(":", 1)[1].strip() if ":" in item else item
        # Descripción: texto suelto que no es campo estructurado
        elif not any(item.startswith(p) for p in FIELD_PREFIXES) and not proj["description"]:
            item_clean = item.strip()
            if item_clean and len(item_clean) > 10:
                proj["description"] = item_clean

    return proj


def _parse_education(sub: dict) -> Optional[dict]:
    name = sub.get("name", "").strip()
    if not name:
        return None
    edu = {"institution": name, "degree": "", "period": "", "details": [], "logo": None}

    def _clean(text: str) -> str:
        return re.sub(r'^\*\*(.+?)\*\*:?\s*', r'\1: ', text).strip()

    for item in sub.get("items", []):
        m = re.match(r'\*\*(.+?)\*\*\s*\((.+?)\)', item)
        if m:
            if not edu["degree"]:
                edu["degree"] = m.group(1).strip()
                edu["period"] = m.group(2).strip()
            else:
                edu["details"].append(_clean(item))
        elif not edu["degree"]:
            edu["degree"] = item
        else:
            edu["details"].append(_clean(item))
    return edu


def _parse_certification(item: str) -> Optional[dict]:
    # Item sin prefijo "- " (ya removido por parse_adoc)
    # Formato: **Name**: issuer info. https://url
    m = re.match(r'\*\*(.+?)\*\*\s*:\s*(.+?)(?:\s+(https?://\S+))?\s*$', item)
    if m:
        name = m.group(1).strip()
        issuer = m.group(2).strip().rstrip(".")
        url = m.group(3)
        return {"name": name, "issuer": issuer, "date": "", "url": url}
    return None


def _parse_volunteer(sub: dict) -> Optional[dict]:
    name = sub.get("name", "").strip()
    if not name:
        return None
    vol = {"organization": name, "role": "", "period": "", "highlights": []}

    # Role/period puede venir del nombre de la subsubsección o de items
    for ss in sub.get("subsections", []):
        ss_name = ss.get("name", "").strip()
        m = re.match(r'(.+?)\s*\((.+?)\)', ss_name)
        if m:
            vol["role"] = m.group(1).strip()
            vol["period"] = m.group(2).strip()
        for item in ss.get("items", []):
            clean = re.sub(r'^\*\*(.+?)\*\*:\s*', r'\1: ', item).strip()
            vol["highlights"].append(clean)

    for item in sub.get("items", []):
        m = re.match(r'\*\*(.+?)\*\*\s*\((.+?)\)', item)
        if m:
            vol["role"] = m.group(1).strip()
            vol["period"] = m.group(2).strip()
        elif item.startswith("-") or item.startswith("*"):
            vol["highlights"].append(item.lstrip("-* ").strip())
    return vol


# ─── Merge inteligente ───────────────────────────────────────────────

def smart_merge(existing: dict, fresh: dict) -> dict:
    """Mergea datos frescos (de .adoc) en el portfolio existente,
    preservando campos manuales (como imágenes, videos, etc.).
    """
    merged = dict(existing)

    # Personal: actualizar solo campos que vienen de .adoc
    for key in ("location", "phone", "email", "github", "linkedin"):
        if key in fresh.get("personal", {}):
            merged.setdefault("personal", {})[key] = fresh["personal"][key]

    if fresh.get("summary"):
        merged["summary"] = fresh["summary"]

    # Experience: solo actualizar entries existentes (no agregar nuevas)
    # El portfolio.json curado es la fuente de verdad para qué entries mostrar
    merged["experience"] = _merge_list(
        existing.get("experience", []),
        fresh.get("experience", []),
        match_keys=["company", "role"],
        preserve_keys=["media", "description", "highlights", "stack"],
        add_new=False,
    )

    # Projects: solo actualizar existentes
    merged["projects"] = _merge_list(
        existing.get("projects", []),
        fresh.get("projects", []),
        match_keys=["name"],
        preserve_keys=["image", "videoUrl", "demoUrl", "featured", "status", "achievement"],
        add_new=False,
    )

    # Skills: mantener los curados
    if existing.get("skills"):
        merged["skills"] = existing["skills"]

    # Education: solo actualizar existentes
    merged["education"] = _merge_list(
        existing.get("education", []),
        fresh.get("education", []),
        match_keys=["institution"],
        preserve_keys=["logo"],
        add_new=False,
    )

    # Certifications: solo actualizar existentes
    merged["certifications"] = _merge_list(
        existing.get("certifications", []),
        fresh.get("certifications", []),
        match_keys=["name"],
        preserve_keys=["url", "date"],
        add_new=False,
    )

    # Volunteer: solo actualizar existentes
    merged["volunteer"] = _merge_list(
        existing.get("volunteer", []),
        fresh.get("volunteer", []),
        match_keys=["organization"],
        preserve_keys=[],
        add_new=False,
    )

    # Secciones que son puramente manuales se conservan intactas
    for key in ("testimonials", "githubStats", "seo"):
        if key in existing:
            merged[key] = existing[key]

    return merged


def _merge_list(
    existing: list[dict],
    fresh: list[dict],
    match_keys: list[str],
    preserve_keys: list[str],
    add_new: bool = True,
) -> list[dict]:
    """Mergea dos listas de objetos. Los items fresh actualizan a los
    existentes (matched por match_keys). Los items existentes preservan
    sus campos en preserve_keys. Si add_new=False, no agrega items nuevos.
    """
    result = list(existing)

    for f_item in fresh:
        found = False
        for i, e_item in enumerate(result):
            if all(e_item.get(k) == f_item.get(k) for k in match_keys if k in e_item and k in f_item):
                merged_item = dict(e_item)
                for k, v in f_item.items():
                    if k not in preserve_keys and v is not None and v != "":
                        merged_item[k] = v
                result[i] = merged_item
                found = True
                break
        if not found and add_new:
            result.append(f_item)

    return result


# ─── Main ────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Portfolio Data Extractor")
    print("=" * 50)

    # 1. Cargar portfolio existente (si existe)
    existing = {}
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8-sig") as f:
            existing = json.load(f)
        print(f"[OK] Portfolio existente cargado: {DATA_FILE.name}")

    # 2. Parsear archivos .adoc
    docs = []
    if GUIALAB_DIR:
        for fname in CV_FILES:
            fpath = GUIALAB_DIR / "cv" / fname
            if fpath.exists():
                doc = parse_adoc(fpath)
                docs.append(doc)
                print(f"[OK] Parseado: {fpath.name}")
            else:
                print(f"⚠ No encontrado: {fpath}")

    # 3. Generar fresh portfolio desde .adoc
    if docs:
        fresh = doc_to_portfolio(docs)
        print(f"[OK] Datos extraídos de {len(docs)} archivo(s) .adoc")

        # 4. Merge
        if existing:
            merged = smart_merge(existing, fresh)
            print("[OK] Merge inteligente completado (datos .adoc + personalizaciones manuales)")
        else:
            merged = fresh
            print("[OK] Portfolio generado desde .adoc (sin personalizaciones previas)")
    else:
        if existing:
            merged = existing
            print("⚠ guia-laboral no encontrado. Usando datos existentes.")
        else:
            print("ERROR: No hay datos .adoc ni portfolio.json previo.")
            sys.exit(1)

    # 5. Guardar
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Portfolio guardado: {DATA_FILE}")
    print(f"  -> {len(merged.get('experience', []))} experiencias")
    print(f"  -> {len(merged.get('projects', []))} proyectos")
    print(f"  -> {len(merged.get('skills', []))} categorías de skills")
    print(f"  -> {len(merged.get('education', []))} educación")
    print(f"  -> {len(merged.get('certifications', []))} certificaciones")
    print(f"  -> {len(merged.get('volunteer', []))} voluntariados")
    print(f"  -> {len(merged.get('testimonials', []))} testimonios")
    print("=" * 50)


if __name__ == "__main__":
    main()
