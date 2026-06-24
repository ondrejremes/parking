# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Záměr projektu

Firemní rezervační systém parkovacích míst pro zaměstnance. Uživatel si přes webové rozhraní rezervuje konkrétní parkovací místo na konkrétní den nebo směnu, maximálně měsíc dopředu.

**Stack**: FastAPI + Python, Jinja2 šablony, autentizace přes Microsoft 365 / Azure AD (OAuth SSO).

## Typy parkovacích míst

Parkoviště má do 30 míst, každé místo má identitu (číslo nebo název). Dva typy:

- **Přidělené místo** — trvale přiřazeno konkrétnímu zaměstnanci adminem. Vlastník ho může:
  - Uvolnit na celý den → místo přejde do sdíleného poolu
  - Uvolnit na denní směnu nebo noční směnu (18:00–00:00) → půlden do poolu
  - Předat konkrétní osobě (ne do poolu, ale cíleně)
- **Sdílené místo** — volně dostupné, kdokoli si ho může rezervovat

## Rezervační model

- Granularita: celý den, denní směna, noční směna (18:00–00:00)
- Horizont: max. 1 měsíc dopředu
- Zaměstnanec rezervuje konkrétní místo (ne automatické přidělení)
- Přidělené místo, u něhož vlastník neudělá žádnou akci, zůstává blokované výhradně pro něj — neuvolní se automaticky
- Pokud vlastník uvolní slot do poolu a nikdo si ho nezabere, zůstane volný — místo se vlastníkovi automaticky nevrátí
- Vlastník může uvolnění vzít zpět (stornovat), dokud si slot nikdo jiný nezarezervoval

## UI — zaměstnanec

Týdenní kalendářový pohled:
- Vlastní rezervace zvýrazněné
- Ve dnech bez rezervace viditelná dostupnost sdílených míst (a uvolněných přidělených)
- Akce: rezervovat, zrušit, uvolnit přidělené místo, předat místo osobě

## Notifikace

- E-mail potvrzení při vytvoření rezervace
- E-mail připomenutí den před rezervací

## Admin

- Přiděluje/odebírá přidělená místa zaměstnancům
- Spravuje seznam míst a uživatelů

