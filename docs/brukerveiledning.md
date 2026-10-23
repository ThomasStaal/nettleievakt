# Nettleievakt: følg timetoppene hjemme

Nettleievakt er et gratis tillegg til Home Assistant. Det bruker målingene du
allerede har der, og viser hvilke timer som kan påvirke kapasitetsleddet i nettleien.
Du trenger ikke registrere deg hos Praktiskinfo eller sende oss forbruksdata.

Dette er en tidlig betaversjon. Den er ikke en erstatning for nettselskapets
målinger, en sikkerhetsfunksjon eller en garanti for lavere nettleie.

## Før du installerer

Du trenger Home Assistant 2026.10 eller nyere. Har du en HomeWizard P1 Meter,
legger du først til den vanlige HomeWizard-integrasjonen i Home Assistant.
Nettleievakt leser bare sensorer som allerede finnes i Home Assistant.

Finn to verdier:

1. **Samlet kjøpt strøm fra nettet**, vanligvis i kWh. Dette skal være en løpende
   teller som øker over tid, ikke «forbruk i dag». Bruk samlet import, ikke en
   enkelt fase, ett prisregister, eksport eller solproduksjon.
2. **Effekt akkurat nå**, vanligvis i W eller kW. Denne er valgfri, men trengs for
   prognoser og varsler. Import skal være positiv. Ved solceller skal eksport ha
   negativt fortegn hvis sensoren viser nettoeffekt.

En måler som bare oppdateres én gang i timen, er ikke egnet til denne løsningen.
Vanligvis bør målingene komme med sekunders mellomrom.

## Installasjon med HACS

1. Åpne HACS og velg **Custom repositories** i menyen.
2. Legg til `https://github.com/ThomasStaal/nettleievakt` som **Integration**.
3. Last ned Nettleievakt. Slå på visning av betaversjoner hvis det er nødvendig.
4. Start Home Assistant på nytt.
5. Gå til **Innstillinger > Enheter og tjenester > Legg til integrasjon**.
6. Søk etter **Nettleievakt**, velg sensorene og sett en varselgrense.

Manuell installasjon er også mulig: legg mappen `custom_components/nettleievakt`
fra prosjektet i `config/custom_components` i Home Assistant, og start på nytt.

## Velg en nyttig varselgrense

Hvis du vil holde en klokketime under 5 kW i snitt, kan du for eksempel velge
4,5 kW som varselgrense. Marginen gir deg litt tid til å reagere. Dette er et
regneeksempel, ikke en anbefalt grense for alle boliger.

Antall døgnmakser står som standard til tre. Det passer bare dersom nettselskapet
beregner kapasitetsleddet fra de tre høyeste døgnmaksene på tre ulike dager.
Kontroller vilkårene hos ditt eget nettselskap.

**En kort topp på 8 kW betyr ikke nødvendigvis en timetopp på 8 kW.** Kjører du en
last på 8 kW i et kvarter, tilsvarer det 2 kWh. Resten av timens forbruk avgjør
snittet. Nettleievakt bruker akkumulert kjøpt energi til å beregne timene.

## Hva tallene betyr

- **Kjøpt strøm denne timen:** kWh fra starten av klokketimen frem til siste måling.
- **Anslått timesnitt:** hvordan timen kan ende hvis den siste effekten fortsetter.
- **Gjenværende effektbudsjett:** hvor mye effekt det i snitt er plass til resten
  av timen innenfor din grense. Det sier ikke noe om hva sikringer, kabler eller
  utstyr tåler. Ikke bruk dette til sikkerhetsstyring.
- **Observert snitt av døgnmakser:** høyeste ferdig målte time per dag, deretter
  snittet av de valgte toppdagene. Dagens maksimum kan fortsatt øke.
- **Måledekning:** hvor mye av måneden hittil som har målinger. Lav dekning betyr
  at den reelle toppen kan være høyere enn den vi har sett.

## Hvorfor står det «ukjent»?

Installerer du klokken 14.20, vet vi ikke hva du brukte fra 14.00 til 14.20.
Vi fyller ikke inn nuller. Timen blir derfor ufullstendig, mens neste hele time
kan måles som normalt.

Etter omstart kan samme situasjon oppstå. Lange opphold, utilgjengelige sensorer
og nullstilling av energitelleren gjør også målingene ufullstendige. Prognosen
blir ukjent når energimåleren eller effektsensoren er for gammel.

Månedssnittet trenger komplette timer på nok forskjellige datoer. Med tre
toppdager valgt kommer det tidligst den tredje dagen. Eldre målinger fra
HomeWizard-appen eller Home Assistant hentes ikke inn i denne versjonen.

## Sett opp et varsel

Legg først entitetene på et vanlig Home Assistant-dashboard. For varsler kan du
bruke prosjektets [blueprint](../blueprints/hourly-warning.yaml): velg
varselentiteten fra Nettleievakt og handlingen som skal sende beskjeden.
Varslet utløses først når prognosen har ligget over grensen i to minutter.

Varslet gjelder den pågående timen. Det sier ikke at nettleien nødvendigvis øker.
En høyere eller lavere time kan være uten betydning hvis andre dager allerede
bestemmer månedsnivået.

## Data og begrensninger

Timeverdiene lagres lokalt i inntil 62 dager. Endrer du varselgrensen under
**Konfigurer**, beholdes historikken. Fjerner du integrasjonen, slettes dens egne
lagrede timeverdier. Vanlige sikkerhetskopier av Home Assistant kan inneholde dem.

Ved overgang til vintertid er de to timene som heter 02.00, to forskjellige
timer. Ved overgang til sommertid finnes ikke den bortfalte timen. Beregningen
bruker norsk kalender og tidssonen Europe/Oslo.

Sammenlign gjerne resultatene med nettselskapets oversikt etter noen dager.
Avvik kan skyldes tidspunkt for målinger, manglende data, avrunding eller et annet
beregningsgrunnlag. Nettselskapets godkjente målinger avgjør regningen.

Kilder: [Elvias forklaring av fastleddet](https://www.elvia.no/nettleie/alt-om-nettleiepriser/slik-fungerer-fastleddet/)
og [Home Assistants HomeWizard-integrasjon](https://www.home-assistant.io/integrations/homewizard/).
