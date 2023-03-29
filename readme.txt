Funktionsweise des Skripts:
1. Extraktion von Jobanzeigen auf Stepstone.de (mittels webscraping) --> siehe 'data_extraction.py'
2. Die Daten/Informationen werden gesäubert & weiter verarbeitet und ein einer Tabelle ('Jobs_DB') gespeichert. Diese Tabelle fungiert hier quasi als Datenbank
--> siehe 'data_transformation' und 'data_analysis'
3. Für die extrahierten Anzeigen werden automatisch Anschreiben erstellt
4. Die Bewerbungsunterlagen werden als E-Mail Entwurf gespeichert (Anschreiben, Lebenslauf, Zeugnisse)

Zusätzliche Hinweise zur Funktionalität:
- die API-Calls an Chat GPT sind kostenpflichtig (Stand 24.03.2023)
- die persönlichen Angaben zu den eigenen Präferenzen, Fähigkeiten, Kriterien der Suche, etc... werden in 'main.py' gepflegt
- die (sensiblen) persönlichen Angaben bzgl. der Adresse, API-Key zu ChatGPT, etc... müssen in separatem .py file definiert und importiert werden (hier unter "personal_info.py")
- weitere persönliche Angaben zur eigenen Adresse, frühestmöglichen Eintrittdatums, Bild der Unterschrift, etc... müssen in 'create_letter.py' gepflegt werden
- die Kriterien, bei welchen "Übereinstimmungswerten" der Kategorien eine Bewerbung geschickt werden soll wird in 'create_letter.py' innerhalb Funktion 'anschreiben_erstellen()' festgelegt

Hinweise zum NLP:
- Die Ähnlichkeit zw. eigenen Interessen und Aufgaben aus den Jobanzeigen etc... wird mit der sog. Jaccard-Ähnlichkeit berechnet
(= Menge übereinstimmender Tokens / Gesamtmenge (ohne Doppelungen) Tokens zweier Strings). --> d.h. Wert zw. 0 und 1 (1 = vollstände Übereinstimmung, 0 = keine übereinstimmenden Tokens)
--> Vorteil für diesen Use Case: Wert bezieht sich nur auf das jeweilige Dokument und nicht auf den aktuell extrahierten Korpus
--> Nachteil für diesen Use Case: Länger der Jobanzeige hat Einfluss auf den Wert (je umfangreicher die Beschreibung --> drückt den score, auch wenn es mehr matched tokens gibt als bei einer anderen jobanzeige mit weniger matched tokens)

- Alternative Berechnungsmöglichkeit hier: mit cosine_similarity Funktion. Wert kann zw. 0 und 1 liegen. (1 = vollstände Übereinstimmung, 0 = keine übereinstimmenden Tokens)
Je mehr Strings in die Interessen/Skills/Benefits Liste aufgenommen werden, desto geringer wird per se der Wert werden, da alle Strings in der Liste gegenüber den Strings in der Jobanzeige geprüft werden.
--> nicht dramatisch für diesen Use Case, da weiterhin ebendiese Anzeigen mit mehr Übereinstimmungen höher gewertet werden (hier ist die relative Wertung wichtiger als die absolute Wertung).
Für den Übereinstimmungsvergleich wird die Methode "CountVectorizer()" (ein einfaches bag-of-words-Verfahren) aus scikit_learn verwendet. Ebenso könnte auch theoretisch die Methode TfidfVectorizer() verwendet werden.
Das TFIDF-Verfahren eignet sich für diesen use case weniger u.a. weil es nicht das Ziel ist, die Wichtigkeit/Gewichtung eines Worts im Dokument zu bewerten, der Dokumentenkorpus nicht starr ist und regelmäßig erweitert wird (--> dadurch verändern sich TFIDF-Ergebnisse auch noch nachträglich)
--> Nachteil für diesen Use Case: Wert ist abhängig vom Korpus (aktuell extrahierte Anzeigen)

Nachteile beider Berechnungsmethoden sind akzeptabel --> weil a) grundsätzlich die Länge der Jobanzeigen nicht wesentlich unterschiedlich ist
und b) niedrige Ähnlichkeitswerte durch Anpassung der Schwellenwerte (Auslösung der Bewerbung) "normalisiert" werden
- Es gibt theoretisch weitere Berechnungsmethoden, die aber nicht weiter untersucht werden für diesen Use Case: z.B. Levenshtein Distanz


Verbesserungspotenzial:
- ggf gekette Wörter (z.B.Lern-/Reisebereitschaft) aufteilen (--> Lernbereitschaft und Reisebereitschaft) --> kommt selten vor --> würde wohl kaum einen Einfluss haben
- Ergebnisse mit anderen Stemmern prüfen
- eine richtige Datenbank auf SQL-Basis statt eines DataFrames verwenden
- englischsprachige Jobanzeigen auch verarbeitbar machen (d.h. Interessen/Skills/Benefits-Listen auch in Englisch anlegen,
Stemming & Lemmatisation & gewählte Sprachen der Bibliotheken (u.a. SpaCy) variabel je nach Sprache der Jobanzeige wählen, ...
- Prüfen/Testen inwiefern die einzelnen Seiten der Jobanzeigen (einfacher?) mit BeautifulSoup geparst werden können
- Ergebnisse mit der Similarity Funktion aus der SpaCy Bibliothek prüfen und mit aktueller vergleichen
- Machine Learning Modell anlegen, um den gesamten HTML Code/Text der Jobanzeigen in die Bestandteile zu clustern (Aufgaben, Profil, Benefits, Kontakt), z.B. mit k-means Clustering