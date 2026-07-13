# Email Templates - Parking Reservation System

## 1. ✉️ Vytvoření Rezervace (Potvrzení)

**Předmět:** Potvrzení rezervace parkovacího místa

```
Dobrý den,

vaše rezervace parkovacího místa byla úspěšně vytvořena.

📍 Parkovací místo: Patro {{ floor }}, Místo {{ number }}
📅 Datum: {{ date | format_date }}
⏰ Čas: {{ shift_name }}  ({{ shift_time }})
🚗 Typ: {{ spot_type }}

Pokud chcete rezervaci zrušit, můžete tak učinit v aplikaci minimálně 24 hodin před termínem.

Parkování App
Alintrust
```

---

## 2. ✉️ Zrušení Rezervace

**Předmět:** Zrušení rezervace parkovacího místa

```
Dobrý den,

vaše rezervace parkovacího místa byla zrušena.

📍 Parkovací místo: Patro {{ floor }}, Místo {{ number }}
📅 Datum: {{ date | format_date }}
⏰ Čas: {{ shift_name }}

Pokud jste si rezervaci zrušili omylem, můžete si místo znovu rezervovat v aplikaci.

Parkování App
Alintrust
```

---

## 3. ✉️ Uvolnění Přiděleného Místa

**Předmět:** Vaše přidělené místo bylo uvolněno do sdíleného poolu

```
Dobrý den,

vaše přidělené parkovací místo bylo uvolněno do sdíleného poolu a je nyní dostupné dalším zaměstnancům.

📍 Parkovací místo: Patro {{ floor }}, Místo {{ number }}
📅 Datum: {{ date | format_date }}
⏰ Čas: {{ shift_name }}
👤 Uvolnil/a: {{ released_by_user }}

Své místo si můžete znovu přidělit v aplikaci.

Parkování App
Alintrust
```

---

## 4. ✉️ Připomenutí Den Před Rezervací (Jen Přidělená Místa)

**Předmět:** Připomenutí: Vaše rezervace parkovacího místa je zítra

```
Dobrý den,

připomínáme vám, že máte zítra zarezervované parkovací místo.

📍 Parkovací místo: Patro {{ floor }}, Místo {{ number }}
📅 Datum: {{ date | format_date }}
⏰ Čas: {{ shift_name }}

Pokud se nemůžete dostavit, zrušte si prosím rezervaci v aplikaci, aby místo mohli využít ostatní.

Parkování App
Alintrust
```

---

## Implementation Notes

- Emails budou obsahovat HTML a plain text verze
- Budou personalizované s údaji uživatele a rezervace
- Whitelist pro testování: `ondrej.remes@alintrust.cz`
- Ostatní uživatelé nebudou dostávat emaily, dokud se whitelist neodestraní
