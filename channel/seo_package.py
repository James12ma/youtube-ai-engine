"""Evidence-labeled deterministic SEO editorial proposals for Alan7 and LogicScript.

NOT an LLM, NOT approved script metadata. Competitor titles/metrics are observations,
not verified facts or a causal ranking model. Works offline and requires no paid API.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Any

_MAX_TAG_BYTES = 500
_TOPIC_RE = re.compile(r"\s+")
_TERMS = {
    "es": {
        "documentary": ["naturaleza", "vida", "acrobacias", "viaje", "alimentación", "comportamiento", "documental"],
        "tutorial": ["tutorial", "guía", "paso a paso", "explicado", "ejemplo", "práctica"],
    },
    "en": {
        "documentary": ["nature", "wildlife", "journey", "behavior", "feeding", "documentary"],
        "tutorial": ["tutorial", "guide", "step by step", "explained", "demo", "walkthrough"],
    },
}


def _clean(text: str, limit: int = 120) -> str:
    return _TOPIC_RE.sub(" ", str(text).replace("<", "").replace(">", "").strip())[:limit].strip()


def _unique(items: list[str], *, limit: int) -> list[str]:
    out: list[str] = []
    seen = set()
    for item in items:
        item = _clean(item, 120)
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            out.append(item)
        if len(out) == limit:
            break
    return out


def _hashtags(topic: str, lang: str, mode: str) -> list[str]:
    norm = unicodedata.normalize("NFKD", topic)
    ascii_topic = "".join(c for c in norm if not unicodedata.combining(c))
    words = re.findall(r"[A-Za-z0-9]+", ascii_topic)
    topic_tag = "".join(w[:1].upper() + w[1:] for w in words[:5])[:42]
    tags = [f"#{topic_tag}"] if topic_tag else []
    if words:
        tags.append("#" + words[0].capitalize())
    tags.append("#Documental" if mode == "documentary" and lang == "es" else
                "#Wildlife" if mode == "documentary" else
                "#Tutorial" if lang == "es" else "#HowTo")
    return _unique(tags, limit=3)


def propose_editorial_package(
    topic: str, language: str, mode: str, public_videos: list[dict[str, Any]],
    *, draft_title: str = "", draft_hook: str = "",
) -> dict[str, Any]:
    lang = "es" if language.lower().startswith("es") else "en"
    if mode not in ("documentary", "tutorial"):
        raise ValueError("mode must be documentary or tutorial")
    subject = _clean(topic, 95)
    if len(subject) < 3:
        raise ValueError("topic is too short")
    subject = subject[0].upper() + subject[1:]
    es = lang == "es"
    if mode == "documentary":
        suffix = ([
            "lo que muestran las imágenes", "preguntas para investigar",
            "una mirada más cercana", "guía visual", "más allá del primer vistazo"
        ] if es else [
            "what the footage can show", "questions worth exploring",
            "a closer look", "a visual field guide", "beyond the first glance"
        ])
        title_candidates = [f"{subject}: {x}" for x in suffix]
        hook = (f"¿Qué podemos descubrir al observar {subject.lower()} de cerca? "
                "Examinaremos las imágenes y contrastaremos los detalles con fuentes verificadas." if es
                else f"What can careful observation tell us about {subject.lower()}? "
                "We'll examine the footage and check each detail against reliable sources.")
        intro = (f"Exploramos {subject.lower()} a través de imágenes y preguntas que requieren verificación."
                 if es else f"We explore {subject.lower()} through footage and questions that require verification.")
        details = ("Qué veremos: [añadir escenas y hechos comprobados del episodio]."
                   if es else "What you'll see: [insert verified scenes and facts from the episode].")
    else:
        suffix = ([
            "guía paso a paso", "por dónde empezar", "ejemplo práctico",
            "lista de verificación", "preguntas frecuentes"
        ] if es else [
            "step-by-step walkthrough", "where to start", "a practical example",
            "a useful checklist", "common questions answered"
        ])
        title_candidates = [f"{subject}: {x}" for x in suffix]
        hook = (f"¿Quieres aprender {subject.lower()} sin adivinar los pasos? "
                "Vamos a revisar el proceso en pantalla y comprobar el resultado." if es
                else f"Want to learn {subject.lower()} without guessing? "
                "We'll work through the steps on screen and check the result.")
        intro = (f"Guía práctica sobre {subject.lower()}, con revisión de pasos y resultados."
                 if es else f"A practical walkthrough of {subject.lower()}, with steps and results reviewed.")
        details = ("Pasos y archivos: [añadir demostración real revisada]." if es
                   else "Steps and files: [insert a reviewed screen demonstration].")
    # The script title is kept as context, never silently installed as a candidate
    # or written back into a source-verified metadata file.
    titles = _unique([t[:100].rstrip(" :|-") for t in title_candidates], limit=5)
    stop = {"de", "del", "con", "para", "en", "los", "las", "the", "with", "for",
            "about", "and", "how", "una", "que"}
    words = [w for w in re.findall(r"[^\W_]+", subject.casefold())
             if len(w) > 2 and w not in stop]
    keywords = _unique(
        [subject.lower(), f"{subject.lower()} documental" if mode == "documentary" and es
         else f"{subject.lower()} documentary" if mode == "documentary"
         else f"{subject.lower()} tutorial",
         f"{subject.lower()} guía" if es else f"{subject.lower()} guide",
         *words[:4]], limit=8,
    )
    # Public competitor headlines are unverified observations only. Count topical
    # words in a bounded sample; no conclusion on ranking or future performance.
    observed = []
    for phrase in _TERMS[lang][mode]:
        count = sum(phrase.casefold() in _clean(v.get("title", ""), 100).casefold()
                    for v in public_videos[:10] if isinstance(v, dict))
        if count:
            observed.append({"theme": phrase, "sample_title_mentions": count})
    observed.sort(key=lambda x: (-x["sample_title_mentions"], x["theme"]))
    hashtags = _hashtags(subject, lang, mode)
    footer = ("Fuentes: [añadir enlaces comprobados].\n"
              "Nota: propuesta editorial sin validar; imágenes y afirmaciones requieren revisión." if es
              else "Sources: [insert verified URLs].\n"
              "Note: unapproved editorial draft; verify footage and factual claims.")
    description = f"{intro}\n\n{details}\n\n{'Temas' if es else 'Topics'}: {', '.join(keywords[:4])}\n\n{' '.join(hashtags)}\n\n{footer}"
    # Keep candidate tags under YouTube's 500-byte combined limit.
    tags = []
    size = 0
    for tag in keywords:
        new_size = len(tag.encode("utf-8")) + (1 if tags else 0)
        if size + new_size > _MAX_TAG_BYTES:
            break
        tags.append(tag)
        size += new_size
    return {
        "status": "NEEDS_OWNER_REVIEW",
        "generator": "deterministic_templates_no_llm",
        "channel_mode": mode, "language": lang, "topic": subject,
        "titles_unapproved": titles,
        "hook_unapproved": _clean(hook, 500),
        "description_unapproved": description,
        "keywords_unapproved": keywords,
        "tags_unapproved": tags, "hashtags_unapproved": hashtags,
        "sample_size": min(len(public_videos), 10),
        "observed_competitor_title_themes_not_facts": observed,
        "draft_title_preserved": _clean(draft_title, 100),
        "draft_hook_preserved": _clean(draft_hook, 500),
        "requires_verified_script": True,
        "requires_footage_or_screen_demo_review": True,
        "applied_to_release": False, "uploaded": False,
        "notes": [
            "Public competitor title mentions do not establish audience location, search volume or ranking advantage.",
            "A title/hook suggesting visuals must match the actual approved footage or screen recording.",
            "The hook and description include only provisional language; replace placeholders with approved verified information.",
            "Do not copy competitor titles or brands; existing metadata approval remains authoritative.",
        ],
    }


def telegram_editorial_package(package: dict[str, Any]) -> str:
    labels = ("Tit (pou revizyon)", "Hook pwopoze", "Deskripsyon pwopoze",
              "Keywords", "Hashtags", "Ang yo remake nan tit konpetitè")
    lines = [f"SEO EDITORIAL PACKAGE | {package['channel_mode']} | {package['language']}",
             f"Sijè: {package['topic']}", labels[0]]
    lines += [f"{n}. {t}" for n, t in enumerate(package["titles_unapproved"], 1)]
    lines.extend([labels[1], package["hook_unapproved"], labels[2],
                  package["description_unapproved"],
                  labels[3], ", ".join(package["keywords_unapproved"]),
                  labels[4], " ".join(package["hashtags_unapproved"]),
                  labels[5]])
    for item in package["observed_competitor_title_themes_not_facts"][:3]:
        lines.append(f"- {item['theme']} ({item['sample_title_mentions']} tit nan echantiyon an)")
    lines += ["PA APWOUVE. Ranplase placeholders ak done verifye; videyo pa pibliye.",
              "Analiz echantiyon, pa garanti views ni RPM."]
    return "\n".join(lines)[:3900]
