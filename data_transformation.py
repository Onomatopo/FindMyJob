import re

# ==============================
# Hauptfunktionen
# ==============================

# DataFrame (Jobs_DB) schon mal grob bearbeiten (unnötige Elemente entfernen)
def df_preprocessen(df):
    # Job ID aus URL erzeugen und speichern
    df['JobID'] = df['URL'].str[-19:-12]
    # in Spalten 'Firma' und 'Jobtitel' und 'JobContent_1' das 'amp;' entfernen
    spalten_pruefen = ['Firma', 'Jobtitel', 'JobContent_1', 'JobContent_3', 'JobContent_7', 'JobContent_9']
    df[spalten_pruefen] = df[spalten_pruefen].replace({'amp;':''}, regex=True)
    # in Spalten 'JobContent_1 & 3' das '&nbsp;' (fett markierte Schrift) entfernen
    spalten_pruefen = ['JobContent_1', 'JobContent_3', 'JobContent_5', 'JobContent_7', 'JobContent_9']
    df[spalten_pruefen] = df[spalten_pruefen].replace({'&nbsp;':' '}, regex=True)
    #'Chevron bottom icon' entfernen
    spalten_pruefen = ['JobContent_8', 'JobContent_9']
    df[spalten_pruefen] = df[spalten_pruefen].replace({'Chevron bottom icon':' '}, regex=True)
    # neue Zeilen : \n entfernen
    spalten_pruefen = ['JobContent_1', 'JobContent_3', 'JobContent_5', 'JobContent_7',]
    df[spalten_pruefen] = df[spalten_pruefen].replace({'\n':' '}, regex=True)
    # m/w/d etc... aus Jobtitel entfernen (re.escape() sorgt dafür, dass sonderzeichen als teil des strings für die
    # regular expressen gewertet werden. die strings dann mit | zu einem re muster zusammenführen
    mwd_liste = ['(w/m/d)', '(m/w/x)', '(m/f/d)', '(m/w/d)', '(gn)', '(f/m/x)',
                 '(f/m/d)', '(m|w|d|x)', '(w|m|d)', '(all genders)', '(m/w/divers)', 'm/w/d', '(m/f/x)']
    pattern = '|'.join(map(re.escape, mwd_liste))
    df["Jobtitel"] = df["Jobtitel"].str.replace(pattern, '', regex=True)
    df["Jobtitel"] = df["Jobtitel"].str.strip()
    return df

# funktion um emails aus einem text zu identifizieren
# regex um das muster zeichen@irgendwas.xx zu identifizieren
def emails_extrahieren(text):
    # falls es mehrere emails gibt, werden die hintereinander angegeben
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    return ','.join(emails)

# Aufgaben-Inhalte extrahieren & speichern
# alle Spalteninhalte prüfen, ob wörter aus aufgaben_überschriften enthält
# und sie eine gewisse länge 100 nicht überschreiten --> wenn true dann Inhalt der Folgespalte in neue Spalte 'Aufgaben' speichern
# durch re.IGNORECASE wird Groß-/Kleinschreibung in den Zellen und der Wortliste ignoriert
# .* bedeutet, dass dazwischen noch andere wörter sein können
def aufgaben_transformieren(df):
    aufgaben_ueberschriften_1 = ['Perspektiven', 'Aufgaben', 'Aufgabengebiet', 'Aufgabenschwerpunkte', 'Aufgabenbereich',
                                'aufgabe',
                                'Dein Job', 'Tasks', 'Verantwortung', 'verantwortungen', 'verantworten', 'beitrag',
                                'bringt der Job', 'Tätigkeitsfelder', 'Tätigkeit', 'Position', 'helfen kannst',
                                'uns hilfst',
                                'responsibilities', 'Herausforderungen', 'Stellenbeschreibung', 'AUFGABENGEBIET',
                                'Rolle', 'was in dir steckt',
                                # auch noch die engl. sprachigen Anzeigen abdecken
                                'do', 'Job Description']
    # alles mit 'erwartet' nur verwenden, wenn in Spalte 5, weil das ggf. mit den benefits verwechselt werden könnte
    # (daher 2 verschiedene schlagwortliste verwenden)
    aufgaben_ueberschriften_2 = ['dich.*erwartet', 'erwartet dich', 'erwartet sie', 'sie.*erwartet']

    # nur ganze worte suchen: regex zum matching von ganzen wörtern
    aufgaben_schlagworte_1 = re.compile(r'\b(' + '|'.join(aufgaben_ueberschriften_1) + r')\b', flags=re.IGNORECASE)
    aufgaben_schlagworte_2 = re.compile(r'\b(' + '|'.join(aufgaben_ueberschriften_2) + r')\b', flags=re.IGNORECASE)

    # durch alle Zeilen des DF laufen
    for index, row in df.iterrows():
        # durch alle Spalten der Zeile laufen
        for column in df.columns:
            # prüfen ob der inhalt ein string ist und kürzer als 100 zeichen
            if isinstance(row[column], str) and len(row[column]) < 100:
                # prüfen ob strings in den checklisten im aktuellen DF-Feld ist (d.h. auf einen Aufgaben-Abschnitt hinweisen)
                # (alles mit 'erwartet' nur verwenden, wenn in JobContent_1 oder JobContent_2 präsent)
                if (aufgaben_schlagworte_1.search(row[column])) or (aufgaben_schlagworte_2.search(row[column]) and (
                        (column == 'JobContent_2') or (column == 'JobContent_1'))):
                    # den wert aus der nächsten Spalte in die Spalte Aufgaben kopieren
                    next_col_index = df.columns.get_loc(column) + 1
                    df.loc[index, 'Aufgaben'] = row[df.columns[next_col_index]]
                    # aus der Schleife raus, weil ja ein match gefunden wurde
                    break
                # falls keine "Aufgaben" identifiziert wurden "leer" als string eingeben (auch um spätere Funktionalitäten zu erhalten)
                else:
                    df.loc[index, 'Aufgaben'] = "leer"

    return df

# Profil - Inhalte extrahieren & speichern
# alle Spalteninhalte prüfen, ob wörter aus profil_überschriften enthält
# und sie eine gewisse länge 100 nicht überschreiten --> wenn true dann Inhalt der Folgespalte in neue Spalte 'Profil' speichern
# durch re.IGNORECASE wird Groß-/Kleinschreibung in den Zellen und der Wortliste ignoriert
def profil_transformieren(df):
    profil_ueberschriften = ['profil', 'profile', 'hintergrund', 'background', 'skills', 'wir suchen', 'wünschen',
                            'bringst', 'mitbringen', 'mitbringst', 'bringen sie',
                            'requirements', 'voraussetzungen', 'anforderungen', 'qualifikationen', 'qualifications',
                            'kompetenzen',
                            'macht uns neugierig', 'so bist Du', 'im gepäck', 'wer Sie sind', 'zeichnet',
                            'darauf freuen wir uns',
                            'auf sie setzen', 'uns begeistert', 'überzeugen', 'damit punkten sie',
                            # auch noch die engl. sprachigen Annonencen abdecken
                            'need']
    # nur ganze worte suchen (# regex zum matching von ganzen wörtern)
    schlagworte_profil = re.compile(r'\b(' + '|'.join(profil_ueberschriften) + r')\b', flags=re.IGNORECASE)

    # durch alle Zeilen des DF laufen
    for index, row in df.iterrows():
        # durch alle Spalten der Zeile laufen
        for column in df.columns:
            # prüfen ob der inhalt ein string ist und kürzer als 100 zeichen
            if isinstance(row[column], str) and len(row[column]) < 100:
                # prüfen ob strings in den checklisten im aktuellen DF-Feld ist (d.h. auf einen Profil-Abschnitt hinweisen)
                if schlagworte_profil.search(row[column]):
                    # den wert aus der nächsten Spalte in die Spalte Profil kopieren
                    next_col_index = df.columns.get_loc(column) + 1
                    df.loc[index, 'Profil'] = row[df.columns[next_col_index]]
                    # aus der Schleife raus, weil ja ein match gefunden wurde
                    break
                # falls kein "Profil" identifiziert wurden "leer" als string eingeben (auch um spätere Funktionalitäten zu erhalten)
                else:
                    df.loc[index, 'Profil'] = "leer"

    return df

# Benefits - Inhalte extrahieren & speichern
# 'hard' prediction from keyword analysis
# alle Spalteninhalte prüfen, ob wörter aus aufgaben_überschriften enthält
# und sie eine gewisse länge 100 nicht überschreiten --> wenn true dann Inhalt der Folgespalte in neue Spalte 'Aufgaben' speichern
# durch re.IGNORECASE wird Groß-/Kleinschreibung in den Zellen und der Wortliste ignoriert
# .* bedeutet, dass dazwischen noch andere wörter sein können
def benefits_transformieren(df):
    benfits_ueberschriften_1 = ['Angebot','Vorteile bei uns', '.*Vorteile','Wir.*bieten', 'bieten wir.*', '.*bietet Ihnen',
                               'anbieten','wird.*geboten', 'Ihre.*Perspektiven', 'deine.*Perspektiven','Benefits', 'wohlfühlen',
                               'haben viel vor','Gute Gründe', 'Our offer', 'we offer','von uns überzeugen','Darum wir',
                               'So sind wir', 'Darum', 'Das finden Sie bei uns','Das findest du bei uns',
                               'WARUM.*','dich.*freuen','sich.*freuen', 'vorteil',
                                # auch noch die engl. sprachigen Annonencen abdecken
                               'expect']
    benefits_ueberschriften_2 = ['dich.*erwartet', '.*erwartet dich.*','.*erwartet sie*', 'sie.*erwartet', '.*erwartet.*bei',
                                'von.*uns.*erwarten', '.*erwarten kannst']
    # es kommt vor, dass Jobannoncen mit keiner richtigen Überschrift versehen werden und dann scheinbar die default(?) Überschrift
    # "Zusätzliche Informationen" automatisch generiert wird von stepstone.
    benefits_ueberschriften_3 = ['zusätzliche informationen']

    # alles mit 'erwartet' nur verwenden, wenn in Spalte JobContent_6, weil das ggf. mit den benefits verwechselt werden könnte
    # (daher 2 verschiedene schlagwortliste verwenden)
    # nur ganze worte suchen:
    benefits_schlagworte_1 = re.compile(r'\b(' + '|'.join(benfits_ueberschriften_1) + r')\b', flags=re.IGNORECASE)
    benefits_schlagworte_2 = re.compile(r'\b(' + '|'.join(benefits_ueberschriften_2) + r')\b', flags=re.IGNORECASE)
    benefits_schlagworte_3 = re.compile(r'\b(' + '|'.join(benefits_ueberschriften_3) + r')\b', flags=re.IGNORECASE)

    for index, row in df.iterrows():
        # erst ab Spalte 7 checken (keine Jobbeschreibung fängt eh mit den Benefits an)
        for column in df.columns[6:]:
            if isinstance(row[column], str) and len(row[column]) < 100:
                # falls benefits_ueberschriften_3 der trigger ist, dann nur wenn Spalte daneben mit
                # einem der Triggerworte aus benfits_ueberschriften_1 beginnt (in den ersten 50 Zeichen)
                if  (benefits_schlagworte_1.search(row[column])) or \
                    (benefits_schlagworte_2.search(row[column]) and column == 'JobContent_6') or \
                    (benefits_schlagworte_3.search(row[column]) and (benefits_schlagworte_1.search(row[df.columns.get_loc(column) + 1][:50]))):
                    next_col_index = df.columns.get_loc(column) + 1
                    df.loc[index, 'Benefits'] = row[df.columns[next_col_index]]
                    break
                # falls keine "Benefits" identifiziert wurden "leer" als string eingeben (auch um spätere Funktionalitäten zu erhalten)
                else:
                    df.loc[index, 'Benefits'] = "leer"

    return df

# Kontakte - Inhalte extrahieren & speichern
# alle Spalteninhalte prüfen, ob wörter aus aufgaben_überschriften enthält
# und sie eine gewisse länge 100 nicht überschreiten --> wenn true dann Inhalt der Folgespalte in neue Spalte 'Aufgaben' speichern
# durch re.IGNORECASE wird Groß-/Kleinschreibung in den Zellen und der Wortliste ignoriert
# .* bedeutet, dass dazwischen noch andere wörter sein können
def kontakt_transformieren(df):
    kontakt_ueberschriften_1 = ['dein weg zu uns', 'weitere informationen', 'teil.*teams.*werden', 'interessiert', 'interesse',
                              'kontakt', 'contact', 'werden.*teil', 'werde.*teil',
                               'Ansprechpartnerin', 'ansprechpartner', 'ansprechperson',
                               'bewirb Dich', 'bewerben', 'bewerbung', 'bewerbungen',
                               'lernen.*kennen', 'kennen.*lernen', 'kennenzulernen'
                               'weg.*uns', 'jetzt.*am zug', 'erreichst', 'erreichen',
                               'wollen.*?', 'möchten.*?','neue.*?', 'klingt.*?', 'Bist Du dabei', 'sind sie dabei',
                               'wählen', 'angesprochen.*?', 'herausforderung.*?']
    # alles mit 'erwartet' nur verwenden, wenn in Spalte JobContent_6, weil das ggf. mit den benefits verwechselt werden könnte
    # (daher 2 verschiedene schlagwortliste verwenden)
    # nur ganze worte suchen:
    kontakt_schlagworte_1 = re.compile(r'\b(' + '|'.join(kontakt_ueberschriften_1) + r')\b', flags=re.IGNORECASE)

    for index, row in df.iterrows():
        # erst ab Spalte 11 checken (keine Jobbeschreibung fängt eh mit den Benefits an)
        for column in df.columns[10:]:
            if isinstance(row[column], str) and len(row[column]) < 100:
                if  (kontakt_schlagworte_1.search(row[column])):
                    next_col_index = df.columns.get_loc(column) + 1
                    df.loc[index, 'Kontakt'] = row[df.columns[next_col_index]]
                    break

    return df
