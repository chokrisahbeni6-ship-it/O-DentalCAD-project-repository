from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_frontend_displays_permanent_lab_nonclinical_warning():
    html = (ROOT / 'frontend/index.html').read_text(encoding='utf-8')
    assert 'LABORATOIRE — USAGE EXCLUSIVEMENT NON CLINIQUE' in html
    assert 'Ne pas utiliser pour le diagnostic' in html
    assert 'ni une validation clinique ni une certification réglementaire' in html


def test_api_metadata_declares_nonclinical_research_scope():
    source = (ROOT / 'backend/app/main.py').read_text(encoding='utf-8')
    assert 'LABORATOIRE / NON CLINIQUE' in source
    assert 'exclusivement non clinique' in source


def test_documentation_defines_prohibited_clinical_use():
    doc = (ROOT / 'NOTICE_USAGE_LABORATOIRE_NON_CLINIQUE.md').read_text(encoding='utf-8')
    assert 'Usages interdits' in doc
    assert 'Décision thérapeutique' in doc
    assert 'fantômes synthétiques' in doc
