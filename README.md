# GenScan2.0
# Overlijdensberichten automatisch inlezen met AI

Automatische verwerking van overlijdensberichten (rouwbrieven, bidprentjes, overlijdensberichten en krantenberichten) voor **Familiekunde Vlaanderen Brugge**. Het doel is om het huidige OCR-proces te vervangen door een gratis, AI-gestuurd systeem dat de documenten *begrijpend* verwerkt, volledig lokaal op een standalone pc.

---

## Inhoud

- [Over de organisatie](#over-de-organisatie)
- [Probleemstelling](#probleemstelling)
- [Hoe werkt het nu?](#hoe-werkt-het-nu)
- [Te extraheren gegevens](#te-extraheren-gegevens)
- [Technische werking (huidige situatie)](#technische-werking-huidige-situatie)
- [Wensen en vereisten](#wensen-en-vereisten)
- [Open vragen](#open-vragen)
- [Roadmap](#roadmap)

---

## Over de organisatie

**Familiekunde Vlaanderen Brugge** is een vzw die volledig draait op vrijwilligers.

| | |
|---|---|
| **Opgericht** | 8 maart 1967 |
| **Leden** | ± 350 |
| **Bestuur** | 10 leden |
| **Activiteiten** | Cursussen, stamboomonderzoek, anderen helpen met stamboomonderzoek, familieverhalen maken |
| **Collectie** | Een paar miljoen documenten |
| **Uitbreiding** | Eventueel later ook andere afdelingen |

## Probleemstelling

De belangrijkste en meest waardevolle documenten in de collectie zijn de **overlijdensberichten**: meer dan **1 miljoen** stuks.

Vandaag wordt ongeveer **70% automatisch** en **30% manueel** verwerkt. De centrale vraag is:

> Kan dit via AI (grotendeels) automatisch worden ingelezen en opgeslagen, met betere resultaten dan het huidige OCR-systeem?

## Hoe werkt het nu?

1. **Triëren en sorteren** per beginletter van de familienaam.
2. **Eén voor één nakijken** in de bestaande database.
3. **Scannen** en inlezen als PDF in **Genscan**.
4. In Genscan zijn de **voorkeuren** (tweede icoon links) belangrijk om correct in te stellen.
5. **Updaten**, waarna Genscan het inventariseren opstart.
6. Het resultaat wordt vandaag door **een tweede persoon gecontroleerd**.

## Te extraheren gegevens

| Veld | Opmerking |
|---|---|
| Voornaam | |
| Naam | |
| Geboorteplaats en -datum | |
| Overlijdensplaats en -datum | |
| Gender | Extra info; moet geautomatiseerd worden |
| Foto | |
| Nota | |
| Type | `rouwbrief`, `bidprentje`, `overlijdensbericht` of `krantenbericht` |
| Nazicht vereist? | Het systeem geeft aan wanneer het onzeker is |
| **Naam van de partner** | 🆕 Nieuwe wens |

**Bestandstypes:** `jpg` en `pdf`

## Technische werking (huidige situatie)

- **Verwerking:** één pc verwerkt alle documenten, met wegschrijven op de verwerkings-pc of via een NAS.
- **Taal:** bijna alles is in Python.
- **Procesvorm:** lineair proces.
- **Website:** de pc uploadt de `jpg` naar **WordPress** en voert de gevonden gegevens in via de front-end.
- **Spreadsheet:** een Excel-bestand bevat alle info.
- **Batches:** per map tot 1000 stuks per batch, daarna naar de NAS.
- **Bekende zwakte:** het systeem heeft moeite met **lichtgrijze tekst**.

### Naamconventie voor bestanden

Bestanden worden benoemd volgens een vast sjabloon:

```
achternaam_voornaam_geboortedatum_overlijdensdatum
```

Datums staan in het formaat `YYYYMMDD`. De bestandsnaam is vrij kort, maar mag zo lang worden als gewenst.

**Voorbeeld:**

```
Janssens_Maria_19210715_20080227.jpg
```

Het bestand wordt geïmporteerd in plaats van rechtstreeks in de database geschreven.

## Wensen en vereisten

### Verplicht

- [ ] Het systeem **moet volledig op een standalone pc draaien**.
- [ ] Draait op een **krachtige** standalone pc.
- [ ] Het huidige OCR-inleesproces wordt vervangen door een **gratis, AI-gestuurd systeem** dat de gegevens begrijpend verwerkt, zodat de resultaten aanzienlijk beter zijn.
- [ ] Het systeem **geeft aan wanneer het ergens onzeker over is**.

### Wensen

- [ ] Ook de **naam van de partner** inlezen.
- [ ] **Gender** automatisch bepalen.
- [ ] Indien nodig **Genscan verbeteren, upgraden of volledig vervangen** door een nieuw systeem.

### Randvoorwaarden

- **Octopus** hoeft niet aangepast te worden. De flow *naar* Octopus wel.
- De AI wordt pas geïmplementeerd **wanneer alles is ingescand**.

## Open vragen

- Welke gratis, lokaal draaiende AI-modellen halen de beste resultaten op deze documenten (ook bij lichtgrijze tekst en handschrift)?
- Hoe wordt de onzekerheid van het systeem uitgedrukt en teruggekoppeld (bv. score of vlag

