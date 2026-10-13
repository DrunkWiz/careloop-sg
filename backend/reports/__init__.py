"""Weekly digest, handover pack, GP brief PDF, insights and activities for the caregiver app. Owner: Nathan.

backend/api imports gp_brief_pdf lazily: if reportlab isn't installed, the name is missing, so
GET /senior/{id}/brief.pdf answers 501 and points at brief.json instead of failing the whole API.
insights and activities use the standard library only.
"""
try:
    from .gp_brief import gp_brief_pdf

    __all__ = ["gp_brief_pdf"]
except ImportError:  # reportlab missing
    __all__ = []
