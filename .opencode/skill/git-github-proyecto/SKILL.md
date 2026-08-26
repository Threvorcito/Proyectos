---
name: git-github-proyecto
description: Git GitHub commits branches pull requests status diff log. Use when the user asks for git status, diffs, commits, branches, merges, conflict help, GitHub PRs, issues, or repository hygiene for this project.
---

# Git Y GitHub Proyecto

Use esta Skill para operaciones Git y GitHub en `C:\Proyectos`.

## Antes De Cambios Git

- Revisar `git status`.
- Revisar `git diff` antes de commitear.
- Revisar `git log --oneline -10` antes de crear commits o PRs.
- No revertir ni sobrescribir cambios no solicitados del usuario.
- No usar `git reset --hard`, `git checkout --` ni comandos destructivos sin aprobacion explicita.

## Commits

- Solo commitear si el usuario lo pide explicitamente.
- Stagear solo archivos relacionados con la tarea.
- Evitar incluir `.env`, bases SQLite, `media/`, `venv/` o archivos temporales.
- Usar mensajes breves y descriptivos, por ejemplo: `Add lesson report filters` o `Fix teacher permission check`.

## GitHub

- Usar `gh` para PRs, issues y checks si esta disponible.
- Antes de crear PR, revisar rama actual, remoto, commits incluidos y diff contra base.
- Devolver la URL del PR cuando se cree.

## Conflictos

- Identificar archivos en conflicto.
- Resolver conservando cambios del usuario y comportamiento esperado del proyecto.
- Verificar con `python manage.py check` o tests relevantes si el conflicto toca codigo.
