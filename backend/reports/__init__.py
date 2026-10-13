"""Weekly digest, handover pack, GP brief PDF. Owner: Nathan.

backend/api imports gp_brief_pdf lazily: if reportlab isn't installed, GET /senior/{id}/brief.pdf
answers 501 and points at brief.json instead of failing the whole API.
"""
from .gp_brief import gp_brief_pdf

__all__ = ["gp_brief_pdf"]
