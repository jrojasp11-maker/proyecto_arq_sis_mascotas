# -*- coding: utf-8 -*-
"""Punto de entrada ASGI para Vercel: expone la misma app de api/main.py."""

from api.main import app

__all__ = ["app"]
