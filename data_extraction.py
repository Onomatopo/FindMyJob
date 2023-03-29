from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import re
from pathlib import Path
from bs4 import BeautifulSoup

# ==============================
# Hilfsfunktionen
# ==============================

# Web Request URL erstellen (URL zur Suche auf stepstone inkl. der Auswahl "schnelle Bewerbung")
def web_request_url(begriff, ort, radius, seite=1):
    web_request = f"https://www.stepstone.de/jobs/{begriff}/in-{ort}?radius={radius}&page={seite}&action=facet_selected%3bapplicationMethod%3bINTERNAL&am=INTERNAL"
    return web_request

# Website cookies ablehnen
def cookies_ablehnen(driver_in):
    fullXpath_decline = '//*[@id="fixedfooter"]/div[1]/div[1]'
    fullXpath_confirm_decline = '//*[@id="fixedfooter"]/div/div[1]'
    element = WebDriverWait(driver_in, 20).until(EC.element_to_be_clickable((By.XPATH, fullXpath_decline)))
    element.click()
    element = WebDriverWait(driver_in, 20).until(EC.element_to_be_clickable((By.XPATH, fullXpath_confirm_decline)))
    element.click()

# Hilfsmethode um aus HTML Input (bestimmtes Format) die Firmenadresse zu identifizieren
def adress_reinigung(html_input):
    # html-parts rausnehmen...
    fakten = re.sub('<[^<]+?>', '', html_input).split(' ')
    # die Elemente zu strings machen
    fakten = [str(item) for item in fakten]
    # ...alles was mit 'Fakten' anfängt entfernen...
    fakten = [item for item in fakten if not item.startswith('Fakten')]
    # ... alles was mit 'http' anfängt auch...
    fakten = [item for item in fakten if not item.startswith('http')]
    # alles ab "Unternehmensgröße rauslöschen (sofern vorhanden)
    if 'DEUnternehmensgröße:' in fakten or 'Unternehmensgröße:' in fakten:
        ab_hier_loeschen = fakten.index('DEUnternehmensgröße:' if 'DEUnternehmensgröße:' in fakten else 'Unternehmensgröße:')
        fakten = fakten[:ab_hier_loeschen]
    # die gewünschten Elemente zusammenführen
    fakten = " ".join(fakten)
    # elemente bei Kommata splitten
    fakten = fakten.split(',')
    # vor- und hintergelagertes whitespace und leere items löschen
    fakten = [s.strip() for s in fakten]
    firmen_adresse = [string for string in fakten if string.strip()]
    return firmen_adresse

# ChromeDriver und Optionen
def chromedriver_aufrufen():
    options = Options()
    options.add_argument('--disable-gpu')  #kann dabei helfen crashes zu verhindern
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver
    except:
        time.sleep(5)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver


# DataFrame weiter bearbeiten (JobContent in mehrere Spalten überführen)
def df_speichern(df):
    # Die Liste in Spalte 'JobContent' in einzelnen Spalten überführen
    df = df.join(pd.DataFrame(df.pop('JobContent').tolist(), index=df.index).fillna('').rename(columns=lambda c: f'JobContent_{c + 1}'))
    return df


# ==============================
# Hauptfunktionen
# ==============================

# Auflistung der Suchergebnisse aktualisieren (--> dadurch werden die Anzeigen neu geladen/abrufen (dynamischer content))
# erfolgt, indem zunächst nach Datum und dann wieder nach Relevanz sortiert wird
def jobs_aktualisieren(driver):
    # xpath zum sortier dropdown feld
    sort_dropdown_xpath = '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[1]/div[2]'
    # exception zur wiederholung ('TimeoutException') (z.B. falls die Seite nur sehr langsam lädt
    while True:
        try:
            # warten bis der dropdown button gefunden/identifiziert wurde
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, sort_dropdown_xpath)))
            break
        except:
            driver.refresh()
    # ausführen der clicks (wenn button gefunden)
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, sort_dropdown_xpath))).click()
    obere_auswahl_dropdown_xpath = '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[1]/div[2]/div/div/div/div/div/div/div/div/div[1]/a[1]'
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, obere_auswahl_dropdown_xpath))).click()
    # hier nochmal das dropdown auswählen, um dann wieder nach Relevanz (der untere Punkt im Dropdown Menu) sortieren
    # etwas zeit lassen zum aufbau der seite
    time.sleep(5)
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, sort_dropdown_xpath))).click()
    untere_auswahl_dropdown_xpath = '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[1]/div[2]/div/div/div/div/div/div/div/div/div[1]/a[2]'
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, untere_auswahl_dropdown_xpath))).click()
    time.sleep(5)

# Methode zur Identifikation der URLs aller Jobanzeigen auf der Ergebnisseite
def jobresults(driver):
    # Xpath des HTML Blocks wo alle Suchergebnisse aufgelistet sind
    xpath_result_list = '/html/body/div[4]/div[1]/div/div/div[2]/div/div[2]/div[2]'
    # falls keine Ergebnisse gefunden werden --> leere Liste zurückgeben
    try:
        # Den HTML Block des Xpaths laden und per regular Expression nur die href d.h. die Links zu den Stellenangeboten in Liste speichern
        raw_jobresults_html = driver.find_element(By.XPATH, xpath_result_list).get_attribute('innerHTML')
        jobresults_urls = re.findall(r'href=[\'"]?([^\'" >]+)', raw_jobresults_html)
        # Weil auch noch interne Stepstone Links zu Logos o.ä. in der Liste sind, werden die hiermit rausgefiltert
        jobresults_urls = [x for x in jobresults_urls if not x.startswith('https://')]
        # Damit die Job Links auch klickbar/aufrufbar sind, wird der vordere Teil (https://www.stepstone.de) noch hinzugefügt bei allen Elementen der Liste
        # (weil die Jobseiten noch nicht als gesamter link in der liste sind)
        jobresults_urls = ['https://www.stepstone.de' + x for x in jobresults_urls]
        return jobresults_urls
    except NoSuchElementException:
        jobresults_urls = []
        return jobresults_urls

# Die einzelnen Jobanzeigen aufrufen, auslesen und deren Inhalte im DataFrame speichern.
# Dazu wird pro Job Annonce ein eigener ChromeDriver ausgeführt
def jobs_auslesen(anzahl, list):
    # pro Suchseite einen DF anlegen
    # Blanko DataFrame erstellen um die einzelnen Job Listings zu speichern
    df_raw_jobs = pd.DataFrame(columns=['URL', 'Jobtitel', 'Firma', 'Adresse', 'JobContent'])

    # Chrome Driver für jedes Job-Listing separat erstellen und Job Content abrufen und im DF speichern
    for i in range(anzahl):
        driver_neu = chromedriver_aufrufen()
        driver_neu.get(list[i])

        # cookies ablehnen für jedes neue fenster der driver
        # zusätzlich try/except Passage, falls die Seite mal nicht so schnell lädt und eine Exception rufen würden
        # --> so wird zum nächsten Item (d.h. zur nächsten Jobanzeige in der for loop gesprungen
        try:
            cookies_ablehnen(driver_neu)
        except TimeoutException:
            #print("Seite lädt zu langsam, springe zur nächsten Anzeige")
            continue

        # Kontaktblock anklicken, damit die Informationen geladen werden und verwendet werden können
        # Try / Except, falls der Kontaktinfo Abschnitt fehlt
        try:
            # xpath zum Kontaktblock
            konktakt_block = '/html/body/div[2]/div[2]/div/div[1]/div/div[1]/div/div[6]/div[1]/div/div/div[5]/div'
            WebDriverWait(driver_neu, 20).until(EC.element_to_be_clickable((By.XPATH, konktakt_block))).click()
        except TimeoutException:
            print("Keine Kontaktinfos hinterlegt")


        # ggf warten bis sich die Hauptelemente der Jobanzeige aufgebaut haben (durch try/exception-Konstrukt)
        # ggf browser refresh
        while True:
            try:
                WebDriverWait(driver_neu, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'js-app-ld-HeaderStepStoneBlock')))
                break
            except:
                driver_neu.refresh()

        # Aus dem Header HTML per regex den Firmennamen + Job Titel extrahieren
        header_html = driver_neu.find_element(By.CLASS_NAME, 'js-app-ld-HeaderStepStoneBlock').get_attribute('innerHTML')
        # (das splitten erzeugt eine Liste, wir wollen aber nur das eine Item an Index 1 haben (dort sind Name + Titel)  --> daher [1])
        firmen_name = re.split(r'"header-company-name" target="_blank">|<\/a><\/span>', header_html)[1]
        job_titel = re.split(r'"header-job-title">|<\/span><\/div>', header_html)[1]

        # Adresse der Firma identifizieren --> über verschiedene Verfahren (weil nicht immer alle Felder auf stepstone gepflegt sind)
        # Verfahren 1 (falls der Location Abschnitt vorhanden ist)
        try:
            location_html = driver_neu.find_element(By.CLASS_NAME, 'js-app-ld-LocationWithCommuteTimeBlock').get_attribute('innerHTML')
            # (das regex splitten erzeugt eine Liste, wir wollen aber nur das eine Item an Index 1 haben --> daher [1] (das ist die adresse)
            firmen_adresse = re.split(r'<span class="listing-content-provider-9iwe6r" data-genesis-element="TEXT" data-at="address-text">(.+?)</span>', location_html)[1]
            # die Elemente zu einer Liste hinzufügen und vor- und nachgelagertes whitespace entfernen
            firmen_adresse = [s.strip() for s in firmen_adresse.split(',')]
            # Letztes Element in der Liste löschen (meist 'Deutschland')
            firmen_adresse.pop()
        except NoSuchElementException:
            # Verfahren 2 falls der Location Abschnitt nicht vorhanden ist --> dann Adresse via Unternehmensporträtseite identifizieren
            # per beautifulsoup die href zur Unternehmensporträtseite identifizieren (im html code wo auch 'lccp-companycard-company-btn' ist
            firmenportraet_xpath = '/html/body/div[2]/div[2]/div/div[1]/div/div[2]/div/div[2]/div/article/div/div/a[2]'
            html_code = driver_neu.find_element(By.XPATH, firmenportraet_xpath).get_attribute('outerHTML')
            soup = BeautifulSoup(html_code, 'html.parser')
            # variable instanziieren (zunächst zu none) --> falls nicht vorhanden --> adresse nicht auffindbar
            #link = None
            if 'lccp-companycard-company-btn' in html_code:
                link = soup.find('a')['href']
                driver_firmen_profil = chromedriver_aufrufen()
                driver_firmen_profil.get(link)
                xpath_fakten_block = '/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div[1]/div[3]/div/div'

                # warten bis die seite geladen ist und cookies akzeptieren
                # mit try / except,  falls die seite nicht lädt --> zum nächsten job in der liste springen
                try:
                    xpath_cookies_akzeptieren = '//*[@id="ccmgt_explicit_accept"]'
                    element = WebDriverWait(driver_firmen_profil, 20).until(EC.element_to_be_clickable((By.XPATH, xpath_cookies_akzeptieren)))
                    element.click()
                except TimeoutException:
                    continue

                try:
                    WebDriverWait(driver_firmen_profil, 20).until(EC.presence_of_element_located((By.XPATH, xpath_fakten_block)))
                    # den HTML Block (Fakten) der Unternehmensporträtseite reinladen....
                    fakten_block_html = driver_firmen_profil.find_element(By.XPATH, xpath_fakten_block).get_attribute('innerHTML')
                    # adresse um unnötigen kram bereinigen
                    firmen_adresse = adress_reinigung(fakten_block_html)
                    driver_firmen_profil.close()
                except TimeoutException:
                    # verbesserungspotenzial
                    # hier versuchen die Unternehmensporträtseiten abzufangen, die bspw. nur den Faktenabschnitt gepflegt haben
                    # (erst prüfen ob 2 blocks exisitieren (z.b. "über uns" und "fakten")
                    xpath_fakten_block_1 = '/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div[1]/div[2]/div/div'
                    xpath_fakten_block_2 = '/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div[1]/div/div/div'
                    try:
                        fakten_block_html = driver_firmen_profil.find_element(By.XPATH, xpath_fakten_block_1).get_attribute('innerHTML')
                        firmen_adresse = adress_reinigung(fakten_block_html)
                        driver_firmen_profil.close()
                    except NoSuchElementException:
                        try:
                            # falls nur 1 block (fakten) existiert
                            fakten_block_html = driver_firmen_profil.find_element(By.XPATH, xpath_fakten_block_2).get_attribute('innerHTML')
                            firmen_adresse = adress_reinigung(fakten_block_html)
                            driver_firmen_profil.close()
                        except NoSuchElementException:
                            firmen_adresse = ''
                            driver_firmen_profil.close()
            else:
                firmen_adresse = ''

        # (einzelnes) JobContent extrahieren als html
        raw_job_content = driver_neu.find_element(By.CLASS_NAME, 'js-app-ld-ContentBlock')
        job_content_html = raw_job_content.get_attribute('innerHTML')

        # html von jobseite über regex splitten bei h4 überschriften --> erzeugt liste (Elemente sind aber noch in HTML Format)
        # (gilt für die meisten Anzeigen, die in 4 parts aufgesplittet sind)
        # für die Anzeigen, die in einem Einzelblock sind --> über überschrift h2 splitten
        if '<h4' in job_content_html:
            raw_job_content_parts = re.split(r'(<h4.*?>.*?</h4>)', job_content_html)
        elif '<h2' in job_content_html:
            raw_job_content_parts = re.split(r'(<h2.*?>.*?</h2>)', job_content_html)

        # Eine leere Liste anlegen, wo die einzelnen gesäuberten Content-Teile gespeichert werden
        job_content_parts = []

        # html aus den einzelnen teilen entfernen, damit nur text übrig bleibt (per regex) und in Liste speichern
        for part in range(len(raw_job_content_parts)):
            job_content_parts.append(re.sub('<[^<]+?>', ' ', raw_job_content_parts[part]))

        # leere items in 'job_content_parts' löschen, items strippen und zu viele whitespaces entfernen per split und anschließendem join
        job_content_parts = [" ".join(string.split()) for string in job_content_parts]

        # leere Elemente ('') aus Liste entfernen
        job_content_parts = [x for x in job_content_parts if x != '']

        # Wenn mehr als 4 Überschriften (= Intro ohne Überschrift) --> erstes Element in Liste löschen damit
        # die gleichen JobContent parts einigermaßen in den gleichen Spalten im DataFrame sind
        anzahl_headings = job_content_html.count('h4')
        if anzahl_headings > 8:
            job_content_parts.pop(0)

        # URL, Titel, Firma, JobContent im DF abspeichern
        df_raw_jobs.loc[i] = [list[i], job_titel, firmen_name, firmen_adresse, job_content_parts]

        print(i)

        # Driver am Ende schließen
        driver_neu.close()

    #den DataFrame als Ergebnis zurückgeben
    return df_raw_jobs

# diese Methode speichert den DataFrame aus den extrahierten Informationen ab
def zur_jobs_db_hinzufuegen(df):
    # prüfen ob schon eine Jobs_DB existiert
    datei = Path('Jobs_DB.csv')
    if datei.is_file():
        Jobs_DB = pd.read_csv('Jobs_DB.csv')
        Jobs_DB = pd.concat([Jobs_DB, df], ignore_index=True)
        Jobs_DB.to_csv('Jobs_DB.csv', encoding='utf-8', index=False)
    # falls noch nicht existiert eine Jobs_DB erstellen
    else:
        Jobs_DB = pd.DataFrame(columns=['JobID', 'URL', 'Jobtitel', 'Firma', 'Adresse', 'JobContent_1', 'JobContent_2',
                                        'JobContent_3', 'JobContent_4', 'JobContent_5', 'JobContent_6', 'JobContent_7',
                                        'JobContent_8', 'JobContent_9', 'JobContent_10', 'JobContent_11', 'sprache', 'email', 'Aufgaben',
                                        'Profil', 'Benefits',  'Kontakt', 'Aufgaben_clean', 'Profil_clean',
                                        'Benefits_clean', 'Aufgaben_clean_lemma', 'Profil_clean_lemma',
                                        'Benefits_clean_lemma', 'Aufgaben_clean_stem', 'Profil_clean_stem',
                                        'Benefits_clean_stem', 'Aufgaben_clean_stem_2',
                                        'Profil_clean_stem_2', 'Benefits_clean_stem_2', 'Aufgaben_clean_stpwrds',
                                        'Aufgaben_clean_stpwrds_cosine', 'Profil_clean_stpwrds',
                                        'Profil_clean_stpwrds_cosine', 'Benefits_clean_stpwrds',
                                        'Benefits_clean_stpwrds_cosine',
                                        'aufgaben_score', 'aufgaben_score_cos_rang','aufgaben_score_jaccard',
                                        'aufgaben_score_jaccard_rang', 'rangdiff_aufgaben',
                                        'matched_tasks', 'profil_score','profil_score_cos_rang', 'profil_score_jaccard',
                                        'profil_score_jaccard_rang', 'rangdiff_profil','matched_profil',
                                        'benefits_score', 'benefits_score_cos_rang', 'benefits_score_jaccard',
                                        'benefits_score_jaccard_rang', 'rangdiff_benefits', 'Gesamtscore', 'Gesamtscore_jaccard',
                                        'anschreiben_mid', 'anschreiben_erstellt?', 'anschreiben_dateiname',
                                        'bewerbung_verschickt?'])

        # ...und die aktuelle Extraktion hinzufügen
        Jobs_DB = pd.concat([Jobs_DB, df], ignore_index=True)
        # ... und als csv abspeichern
        Jobs_DB.to_csv('Jobs_DB.csv', encoding='utf-8', index=False)


