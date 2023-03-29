import spacy
import pandas as pd
from langdetect import detect
from selenium.webdriver.common.by import By
import time
from personal_info import meine_plz, api_key, adresse, ort, fruehestes_datum, unterschrift_pfad, \
    anschreiben_speicherpfad, lebenslauf_speicherpfad, zeugnisse_speicherpfad, anzeigen_speicherpfad
from data_extraction import chromedriver_aufrufen, cookies_ablehnen, web_request_url, \
    jobs_aktualisieren, jobresults, jobs_auslesen, df_speichern, zur_jobs_db_hinzufuegen
from data_transformation import df_preprocessen, emails_extrahieren, aufgaben_transformieren, \
    profil_transformieren, benefits_transformieren, kontakt_transformieren
from data_analysis import clean_text, spacy_lemma, snowball_stemming, cistem_stemming, stopwoerter_entfernen, \
    interessen_preprocessen, aufgaben_aehnlichkeit_berechnen, skills_preprocessen, profil_aehnlichkeit_berechnen, \
    benefits_preprocessen, benefits_aehnlichkeit_berechnen, jaccard_aehnlichkeit_berechnen
from create_letter import anschreiben_erstellen, mail_erstellen


# ==============================
# User-Inputs
# Sucheinstellungen und api key
# & Job-Filter (Jobs die rausgefiltert werden)
# & interessen (bzgl. der Aufgaben)
# ==============================

such_begriffe = ['data-analyst']     # nach welchen Begriffen gesucht werden soll
such_plz = meine_plz                             # Postleitzahl des Suchgebiets
such_radius = "30"                              # Radius des Suchgebiets um die PLZ
anzeigen_pro_seite = 5                          # Anzahl der Jobanzeigen die pro Seite analysiert werden sollen
anzahl_seitendurchsuche = 1                     # Anzahl der Suchergebnisseiten die durchsucht werden sollen
api_key = api_key   # API-Key zur Schnittstelle von Chat GPT (kostenpflichtig!)

# falls diese Begriffe als Wörter vorkommen --> Jobanzeige wird aus DF rausgefiltert
jobfilter = ['CTA', 'BTA', 'MTLA', 'Chemie', 'Sozialarbeiter', 'Werkstudent', 'Praktikum', 'befristet',
             'Studium', 'außendienst', 'therapeut', 'Biologielaborant', 'Chemielaborant']

# die interessen nach denen in den Anzeigen gesucht werden soll definieren
interessen = ['analyse', 'report', 'dashboard', 'auswertung', 'daten', 'datenanalyse', 'datenauswertung',
              'business', 'intelligence', 'bi', 'kpi', 'etl', 'data', 'warehouse', 'dwh', 'forecast', 'zusammenarbeit',
              'workflow', 'prozess', 'handlungsempfehlung', 'Prozessoptimierung', 'Datenmengen', 'it-affinität',
              'visualisierung', 'Modelle', 'methoden', 'daten-muster', 'extrahieren', 'datensätze', 'reporting']

# die skills nach denen in den Anzeigen gesucht werden soll definieren
skills = ['analytisch', 'studium', 'wirtschaft', 'ms office', 'excel', 'datenanalyse', 'englisch', 'fremdsprache',
                'grundkenntnisse', 'sql', 'python', 'tableau', 'flow', 'power', 'bi', 'automate']

# die benefits nach denen in den Anzeigen gesucht werden soll definieren
benefits = ['mobiles', 'arbeiten', 'Home', 'Office', 'flexibel', 'flexible', 'gleitzeit', 'Hybrid', 'Philosophie']

# Ähnlichkeitsschwellenwerte festlegen:
aufgaben_schwellenwert = 0.044
profil_schwellenwert = 0.022
benefits_schwellenwert = 0
gesamt_schwellenwert = 0.09
schwellenwerte = [aufgaben_schwellenwert, profil_schwellenwert, benefits_schwellenwert, gesamt_schwellenwert]

# Infos für das anschreiben (importiert aus personal_info.py)
eigene_adresse = adresse
eigener_ort = ort
fruehestes_datum = fruehestes_datum
unterschrift_pfad = unterschrift_pfad

# speicherorte der anhänge (anschreiben + lebenslauf + zeugnisse)
# (Angabe zum Ordner, aber ohne den den letzten slash (/), nicht die Pfadangabe zu einer konkreten Datei!!)
anschreiben_speicherpfad = anschreiben_speicherpfad
# der lebenslauf und die zeugnisse sind für alle bewerbungen gleich --> insofern fixer link zu den jeweiligen dokumenten
# ("pfad/und/datei.pdf")
lebenslauf_speicherpfad = lebenslauf_speicherpfad
# zeugnisse speicherort ("pfad/und/datei.pdf")
zeugnisse_speicherpfad = zeugnisse_speicherpfad
# falls die anzeigen als html gespeichert werden sollen --> speicherort angeben
# (Angabe zum Ordner, aber ohne den den letzten slash (/), nicht die Pfadangabe zu einer konkreten Datei!!)
anzeigen_speicherpfad = anzeigen_speicherpfad


# ==============================
# Daten extrahieren
# ==============================

# den Initialdriver instanziieren
driver_main = chromedriver_aufrufen()
# Initialen Web Request zum Abruf der 1. Seite der Job Listings auf Stepstone mit den gegebenen Such-Settings
# 1: Startseite aufrufen, 2: Cookies ablehnen
driver_main.get('https://www.stepstone.de')
# Cookies nach initialem Aufruf ablehnen
cookies_ablehnen(driver_main)
# liste für erstellte dataframes erstellen (pro suchbegriff & ergebnisseite wird jeweils ein eigener df erstellt, der später wieder konkateniert wird)
gesammelte_df = []
for suchwort in such_begriffe:
    # Suchseite mit Zieleingaben aufrufen
    driver_main.get(web_request_url(suchwort, such_plz, such_radius))#, ziel_suchseite))
    # joblistings aktualisieren
    jobs_aktualisieren(driver_main)
    ###########################
    # Die Job Anzeigen der ausgewählten Suchseiten ziehen
    for seiten in range(1, anzahl_seitendurchsuche+1):
        # jobresults der suchseite ziehen
        jobresults_urls_list = jobresults(driver_main)
        #print(jobresults_urls_list)

        # falls die jobresults_urls_list leer ist (= keine Suchergebnisse auf der Suchergebnisseite)
        # --> dann zum nächsten suchwort in der loop springen
        print(f'anzahl ergebnisse s.{seiten}: {len(jobresults_urls_list)}')
        if len(jobresults_urls_list) > 0:
            ##########################################################
            ### Detail Extraktion pro Joblisting (pro eigener URL) ###
            # jobs der aktuellen seite auslesen & speichern
            df_raw_jobs = jobs_auslesen(anzeigen_pro_seite, jobresults_urls_list)

            #print(df_raw_jobs)

            gesammelte_df.append(df_speichern(df_raw_jobs))

            # ggf zur nächsten Suchseite wechseln (5 sek sleep um der seite zeit zum aufbau zu geben)
            if seiten < anzahl_seitendurchsuche:
                # je nach Suche gibt es eine unterschiedliche Anzahl an Ergebnisseiten --> entsprechend verändert sich der Xpath des Buttons um auf die nächste Seite zu gelangen.
                # das wird hier gelöst, indem geschaut wird, an welcher Stelle sich das Element 'Chevron right icon' (=nächste Seite) befindet und entsprechend der Xpath aus dem
                # dict gewählt wird als xpath für die nächste Seite
                nav_bar = '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]'
                elemente = driver_main.find_element(By.XPATH, nav_bar)
                # die elemente der navigationsbar (navigations buttons als text in einer liste speichern
                btns_liste = elemente.text.split("\n")
                #print(btns_liste)
                # position von 'Chevron right icon' identifizieren
                next_page_index = btns_liste.index('Chevron right icon')
                #print(next_page_index)
                # dict um die index position der items in der nav bar und zugehörigem xpath zu definieren
                navigation_leiste = {1: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[1]',
                                     2: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[2]',
                                     3: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[3]',
                                     4: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[4]',
                                     5: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[5]',
                                     6: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[6]',
                                     7: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[7]',
                                     8: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[8]',
                                     9: '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[3]/div/nav/ul/li[9]'}
                element = driver_main.find_element(By.XPATH, navigation_leiste[next_page_index])
                driver_main.execute_script("arguments[0].scrollIntoView();", element)
                element.click()
                time.sleep(5)

        # falls die liste der suchergebnisse der aktuellen seite leer ist --> zum nächsten suchwort springen
        else:
           continue

# Driver (Web Request) schließen, (Driver zur Auflistung der Jobs auf Ergebnisseite & Wechseln der Ergebnisseiten)
driver_main.close()
# Die Liste der einzelnen Dataframes (pro Ergebnisseite) zu einem gesamten DF konkatenieren
df_raw_jobs = pd.concat(gesammelte_df, axis=0, ignore_index=True)
# Jobs_DB speichern
zur_jobs_db_hinzufuegen(df_raw_jobs)
# Duplikate auf Basis der URL löschen & DF speichern
Jobs_DB = pd.read_csv('Jobs_DB.csv')
Jobs_DB = Jobs_DB.drop_duplicates(subset='URL', keep='first')


# ==============================
# Daten transformieren
# ==============================

# DF preprocessen
Jobs_DB = df_preprocessen(Jobs_DB)

# Jobs filtern & unpassende Anzeigen löschen
mask = Jobs_DB['Jobtitel'].str.contains('|'.join(jobfilter), case=False)
Jobs_DB.drop(Jobs_DB[mask].index, inplace=True)
Jobs_DB.reset_index(inplace=True, drop=True)

# identifikation der Sprache mit der langdetect Bibliothek und der integrierten funktion
# identifikation anhand von Spalte JobContent_1 und weil diese ggf leer sein kann --> JobContent_2 spalte mit zur Beurteilung
# einbeziehen. --> daher beide spalten erst zusammenführen in neue spalte --> identifizieren --> neue spalte wieder löschen
Jobs_DB['temporär'] = Jobs_DB['JobContent_1'] + ' ' + Jobs_DB['JobContent_2']
Jobs_DB['sprache'] = Jobs_DB['temporär'].apply(lambda x: detect(x))
Jobs_DB = Jobs_DB.drop('temporär', axis=1)

# Emails aus Kontaktspalte identifizieren
# die gefundenen mailadressen in einer neuen spalte speichern (zunächst die inhalte zu strings machen)
Jobs_DB['email'] = Jobs_DB['JobContent_9'].astype(str).apply(lambda x: emails_extrahieren(x))

# Aufgaben-Inhalte extrahieren & speichern
Jobs_DB = aufgaben_transformieren(Jobs_DB)

# Profil-Inhalte extrahieren & speichern
Jobs_DB = profil_transformieren(Jobs_DB)

# Benefits - Inhalte extrahieren & speichern
Jobs_DB = benefits_transformieren(Jobs_DB)

# Kontakte - Inhalte extrahieren & speichern
Jobs_DB = kontakt_transformieren(Jobs_DB)

# DF speichern
Jobs_DB.to_csv('Jobs_DB.csv', encoding='utf-8', index=False)


# ==============================
# Daten analysieren: Vergleich Aufgaben<>Interessen, Profil<>Skills, Wünschen<>Benefits
# ==============================

# Data Cleansing für ganze Spalten
Jobs_DB['Aufgaben_clean'] = Jobs_DB['Aufgaben'].apply(clean_text)
Jobs_DB['Profil_clean'] = Jobs_DB['Profil'].apply(clean_text)
Jobs_DB['Benefits_clean'] = Jobs_DB['Benefits'].apply(clean_text)
# Tokenization: alle wörte zu elementen einer liste machen
Jobs_DB['Aufgaben_clean'] = Jobs_DB['Aufgaben_clean'].apply(lambda x: x.split())
Jobs_DB['Profil_clean'] = Jobs_DB['Profil_clean'].apply(lambda x: x.split())
Jobs_DB['Benefits_clean'] = Jobs_DB['Benefits_clean'].apply(lambda x: x.split())
# Lemmatization
# zunächst Spacy bibliothek laden
nlp = spacy.load('de_core_news_sm')
Jobs_DB['Aufgaben_clean_lemma'] = [[spacy_lemma(x, nlp) for x in wort_liste] for wort_liste in Jobs_DB['Aufgaben_clean']]
Jobs_DB['Profil_clean_lemma'] = [[spacy_lemma(x, nlp) for x in wort_liste] for wort_liste in Jobs_DB['Profil_clean']]
Jobs_DB['Benefits_clean_lemma'] = [[spacy_lemma(x, nlp) for x in wort_liste] for wort_liste in Jobs_DB['Benefits_clean']]
# Stemming
text_sprache = 'german'
# snowball stemming
Jobs_DB['Aufgaben_clean_stem'] = [[snowball_stemming(x, text_sprache) for x in wort_liste] for wort_liste in Jobs_DB['Aufgaben_clean_lemma']]
Jobs_DB['Profil_clean_stem'] = [[snowball_stemming(x, text_sprache) for x in wort_liste] for wort_liste in Jobs_DB['Profil_clean_lemma']]
Jobs_DB['Benefits_clean_stem'] = [[snowball_stemming(x, text_sprache) for x in wort_liste] for wort_liste in Jobs_DB['Benefits_clean_lemma']]
# cistem stemming
Jobs_DB['Aufgaben_clean_stem_2'] = [[cistem_stemming(x) for x in wort_liste] for wort_liste in Jobs_DB['Aufgaben_clean_stem']]
Jobs_DB['Profil_clean_stem_2'] = [[cistem_stemming(x) for x in wort_liste] for wort_liste in Jobs_DB['Profil_clean_stem']]
Jobs_DB['Benefits_clean_stem_2'] = [[cistem_stemming(x) for x in wort_liste] for wort_liste in Jobs_DB['Benefits_clean_stem']]
# stopwörter entfernen
Jobs_DB['Aufgaben_clean_stpwrds'] = Jobs_DB['Aufgaben_clean_stem_2'].apply(lambda x: stopwoerter_entfernen(x, nlp))
Jobs_DB['Profil_clean_stpwrds'] = Jobs_DB['Profil_clean_stem_2'].apply(lambda x: stopwoerter_entfernen(x, nlp))
Jobs_DB['Benefits_clean_stpwrds'] = Jobs_DB['Benefits_clean_stem_2'].apply(lambda x: stopwoerter_entfernen(x, nlp))

# interessen preprocessen (cleanen + lemman + stemmen)
interessen_liste = interessen_preprocessen(interessen, text_sprache, nlp)

# skills preprocessen (cleanen + lemman + stemmen)
skills_liste = skills_preprocessen(skills, text_sprache, nlp)

# benefits preprocessen (cleanen + lemman + stemmen)
benefits_liste = benefits_preprocessen(benefits, text_sprache, nlp)

# DF speichern
Jobs_DB.to_csv('Jobs_DB.csv', encoding='utf-8', index=False)

# Ähnlichkeit zw. Interessen & Aufgaben aus Anzeige kalkulieren (mittels cosine similarity und bag of words Verfahren)
# (inkl. die gematchten tokens speichern)
Jobs_DB = aufgaben_aehnlichkeit_berechnen(Jobs_DB, interessen_liste)
Jobs_DB['aufgaben_score_cos_rang'] = Jobs_DB['aufgaben_score'].rank(ascending=False)
# Ähnlichkeit zw. Interessen & Aufgaben aus Anzeige kalkulieren (mittels Jaccard-Ähnlichkeit)
Jobs_DB['aufgaben_score_jaccard'] = Jobs_DB['Aufgaben_clean_stpwrds'].apply(lambda x: jaccard_aehnlichkeit_berechnen(x, interessen_liste))
Jobs_DB['aufgaben_score_jaccard_rang'] = Jobs_DB['aufgaben_score_jaccard'].rank(ascending=False)
# unterschiede im rang der aufgaben berechnen (als betrag)
Jobs_DB['rangdiff_aufgaben'] = abs(Jobs_DB['aufgaben_score_cos_rang'] - Jobs_DB['aufgaben_score_jaccard_rang'])
durchschnittsabweichung_rang_aufgaben = Jobs_DB['rangdiff_aufgaben'].mean()
print(f'ø-Abweichung rang aufgaben: {durchschnittsabweichung_rang_aufgaben}')


# Ähnlichkeit zw. Skills & requirements aus Anzeige kalkulieren (mittels cosine similarity und bag of words Verfahren)
# (inkl. die gematchten tokens speichern)
Jobs_DB = profil_aehnlichkeit_berechnen(Jobs_DB, skills_liste)
Jobs_DB['profil_score_cos_rang'] = Jobs_DB['profil_score'].rank(ascending=False)
# Ähnlichkeit zw. Skills & requirements aus Anzeige kalkulieren (mittels Jaccard-Ähnlichkeit)
Jobs_DB['profil_score_jaccard'] = Jobs_DB['Profil_clean_stpwrds'].apply(lambda x: jaccard_aehnlichkeit_berechnen(x, skills_liste))
Jobs_DB['profil_score_jaccard_rang'] = Jobs_DB['profil_score_jaccard'].rank(ascending=False)
# unterschiede im rang des profils berechnen (als betrag)
Jobs_DB['rangdiff_profil'] = abs(Jobs_DB['profil_score_cos_rang'] - Jobs_DB['profil_score_jaccard_rang'])
durchschnittsabweichung_rang_profil = Jobs_DB['rangdiff_profil'].mean()
print(f'ø-Abweichung rang profil: {durchschnittsabweichung_rang_profil}')


# Ähnlichkeit zw. Wünschen & benefits aus Anzeige kalkulieren (mittels cosine similarity und bag of words Verfahren)
# zusätzlich die gematchten tokens speichern
Jobs_DB = benefits_aehnlichkeit_berechnen(Jobs_DB, benefits_liste)
Jobs_DB['benefits_score_cos_rang'] = Jobs_DB['benefits_score'].rank(ascending=False)
# Ähnlichkeit zw. Wünschen & benefits aus Anzeige kalkulieren (mittels Jaccard-Ähnlichkeit)
Jobs_DB['benefits_score_jaccard'] = Jobs_DB['Benefits_clean_stpwrds'].apply(lambda x: jaccard_aehnlichkeit_berechnen(x, benefits_liste))
Jobs_DB['benefits_score_jaccard_rang'] = Jobs_DB['benefits_score_jaccard'].rank(ascending=False)
# unterschiede im rang des profils berechnen (als betrag)
Jobs_DB['rangdiff_benefits'] = abs(Jobs_DB['benefits_score_cos_rang'] - Jobs_DB['benefits_score_jaccard_rang'])
durchschnittsabweichung_rang_benefits = Jobs_DB['rangdiff_benefits'].mean()
print(f'ø-Abweichung rang benefits: {durchschnittsabweichung_rang_benefits}')

# die einzelscores (aufgaben_score, profil_score, benefits_score) addieren und in neuer spalte anzeigen
# die 3 Teile sind unterschiedlich gewichtet
Jobs_DB['Gesamtscore'] = (Jobs_DB['aufgaben_score']) + (Jobs_DB['profil_score']) + (Jobs_DB['benefits_score']/2)
Jobs_DB['Gesamtscore_jaccard'] = (Jobs_DB['aufgaben_score_jaccard']) + (Jobs_DB['profil_score_jaccard']) + (Jobs_DB['benefits_score_jaccard']/2)

# DF speichern
Jobs_DB.to_csv('Jobs_DB.csv', encoding='utf-8', index=False)

# ==============================
# Anschreiben erstellen
# ==============================
# Jobs_DB aufrufen
Jobs_DB = pd.read_csv('Jobs_DB.csv')

# Anschließend gesamtes Anschreiben erstellen
# (inkl. Abruf/Erstellung des individuellen Textbausteins)
Jobs_DB = anschreiben_erstellen(Jobs_DB, api_key, eigene_adresse, fruehestes_datum, unterschrift_pfad,
                                schwellenwerte, anschreiben_speicherpfad, anzeigen_speicherpfad)

# DF speichern
Jobs_DB.to_csv('Jobs_DB.csv', encoding='utf-8', index=False)

# Mails als Entwürfe erstellen
mail_erstellen(Jobs_DB, anschreiben_speicherpfad, lebenslauf_speicherpfad, zeugnisse_speicherpfad)

# DF speichern
Jobs_DB.to_csv('Jobs_DB.csv', encoding='utf-8', index=False)
