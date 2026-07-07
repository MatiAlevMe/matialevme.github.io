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
                if items:
                    portfolio["summary"] = items[0] if items else ""
                for sub in sec.get("subsections", []):
                    if sub["name"] in ("Información Personal", "Personal Information"):
                        pass

            # Experiencia
            elif sec["name"] in ("Experiencia", "Experience", "Experiencia Laboral", "Work Experience"):
                for sub in sec.get("subsections", []):
                    exp = _parse_experience(sub)
                    if exp:
                        portfolio["experience"].append(exp)

            # Proyectos
            elif sec["name"] in ("Proyectos", "Projects", "Proyectos Personales"):
                for sub in sec.get("subsections", []):
                    proj = _parse_project(sub)
                    if proj:
                        portfolio["projects"].append(proj)

            # Educación
            elif sec["name"] in ("Educación", "Education"):
                for sub in sec.get("subsections", []):
                    edu = _parse_education(sub)
                    if edu:
                        portfolio["education"].append(edu)

            # Certificaciones
            elif sec["name"] in ("Licencias y Certificaciones", "Licenses and Certifications"):
                for item in sec.get("items", []):
                    cert = _parse_certification(item)
                    if cert:
                        portfolio["certifications"].append(cert)

            # Voluntariado
            elif sec["name"] in ("Experiencia Voluntaria", "Volunteer Experience"):
                for sub in sec.get("subsections", []):
                    vol = _parse_volunteer(sub)
                    if vol:
                        portfolio["volunteer"].append(vol)

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

    # Buscar role y periodo en items o subsections
    for item in sub.get("items", []):
        # Buscar formato: "#### Rol (Periodo)"
        m = re.match(r'(.+?)\s*\((.+?)\)', item)
        if m and not item.startswith("-") and not item.startswith("*"):
            exp["role"] = m.group(1).strip()
            exp["period"] = m.group(2).strip()
        elif item.startswith("Stack:"):
            exp["stack"] = [s.strip() for s in item[6:].split(",")]
        elif item.startswith("-"):
            exp["highlights"].append(item.lstrip("- ").strip())

    # Revisar subsections (logros/achievements)
    for ss in sub.get("subsections", []):
        ss_name = ss.get("name", "").lower()
        if "logro" in ss_name or "achievement" in ss_name:
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

    for item in sub.get("items", []):
        if item.startswith("Stack:") or item.startswith("**Stack**"):
            stack_str = item.split(":", 1)[1].strip().strip("**").strip()
            proj["stack"] = [s.strip() for s in stack_str.split(",")]
        elif item.startswith("*Link*") or item.startswith("Link") or "github.com" in item.lower():
            m = re.search(r'https://github\.com/\S+', item)
            if m:
                proj["githubUrl"] = m.group(0)
        elif "deploy" in item.lower() or "http" in item.lower():
            urls = re.findall(r'https?://\S+', item)
            for url in urls:
                if "github" not in url.lower() and "drive" not in url.lower():
                    proj["demoUrl"] = url
        elif "logro" in item.lower() or "achievement" in item.lower() or "nota" in item.lower() or "grade" in item.lower():
            proj["achievement"] = item.split(":", 1)[1].strip() if ":" in item else item
        elif item.startswith("-") or item.startswith("*"):
            text = item.lstrip("-* ").strip()
            if text and not proj["description"]:
                proj["description"] = text

    return proj


def _parse_education(sub: dict) -> Optional[dict]:
    name = sub.get("name", "").strip()
    if not name:
        return None
    edu = {"institution": name, "degree": "", "period": "", "details": [], "logo": None}
    for item in sub.get("items", []):
        m = re.match(r'\s*[-*]\s+\*\*(.+?)\*\*\s*\((.+?)\)', item)
        if m:
            edu["degree"] = m.group(1).strip()
            edu["period"] = m.group(2).strip()
        elif item.startswith("-") or item.startswith("*"):
            edu["details"].append(item.lstrip("-* ").strip())
        elif not edu["degree"]:
            edu["degree"] = item
    return edu


def _parse_certification(item: str) -> Optional[dict]:
    m = re.match(r'\s*[-*]\s+\*\*(.+?)\*\*\s*:\s*(.+?)(?:\s+https?://\S+)?$', item)
    if m:
        return {"name": m.group(1).strip(), "issuer": m.group(2).strip(), "date": "", "url": None}
    return None


def _parse_volunteer(sub: dict) -> Optional[dict]:
    name = sub.get("name", "").strip()
    if not name:
        return None
    vol = {"organization": name, "role": "", "period": "", "highlights": []}
    for item in sub.get("items", []):
        m = re.match(r'\s*[-*]\s+\*\*(.+?)\*\*\s*\((.+?)\)', item)
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
        preserve_keys=["logo", "details"],
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
        preserve_keys=["highlights"],
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
