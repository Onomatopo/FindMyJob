import re
import string
from nltk.stem.snowball import SnowballStemmer
from nltk.stem.cistem import Cistem
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ==============================
# Hauptfunktionen
# ==============================

# Data Cleansing methode
def clean_text(text):
    # Satztrennzeichen ! und ? Durch Leerzeichen ersetzen
    text = re.sub(r'[!?]', ' ', str(text))
    # alle andere Satztrennzeichen entfernen (: , ; etc...)
    text = re.sub("[%s]" %re.escape(string.punctuation), ' ', text)
    #Leerzeilen entfernen
    text = re.sub('\n', '', text)
    # & --> 'und'
    text = re.sub('&', 'und', text)
    # sonderzeichen wie z.b. • entfernen
    text = re.sub(r'[^\w\s]', '', text)
    # Umlaute entfernen
    umlaute = {
    'ü': 'ue',
    'Ü': 'Ue',
    'ä': 'ae',
    'Ä': 'Ae',
    'ö': 'oe',
    'Ö': 'Oe',
    'ß': 'ss'}
    text = re.sub('|'.join(umlaute.keys()), lambda x: umlaute[x.group()], text)
    # alles zu kleinbuchstaben machen
    text = text.lower()
    return text

# Lemmatization
def spacy_lemma(wort, nlp):
    doc = nlp(wort)
    return (doc[0].lemma_)

# stemming ~ lemmatization (wörter auf den wortstamm zurückbringen: 'gelaufen' --> 'laufen')
# (funktion die ein wort einließt und entsprechend der gewählten sprache den wortstamm zurück liefert)
def snowball_stemming(wort, text_sprache):
    s_stemmer_de = SnowballStemmer(language=text_sprache)
    return s_stemmer_de.stem(wort)

def cistem_stemming(wort):
    c_stemmer_de = Cistem()
    return c_stemmer_de.stem(wort)

# methode zum entfernen von stopwörtern --> ließt den array (inhalt der spalte) ein und gibt
# einen array ohne die stopwörter wieder aus
def stopwoerter_entfernen(inhalt, nlp):
    stopwoerter = nlp.Defaults.stop_words
    inhalt = [x for x in inhalt if not x in stopwoerter]
    return (inhalt)

# interessen preprocessen (cleanen + lemman + stemmen)
def interessen_preprocessen(interessen, sprache, nlp):
    # cleanen
    interessen_clean = [clean_text(x) for x in interessen]
    # lemma
    interessen_clean_lemma = [spacy_lemma(x, nlp) for x in interessen_clean]
    # stem1
    interessen_clean_lemma_stem1 = [snowball_stemming(x, sprache) for x in interessen_clean_lemma]
    # stem2
    interessen_clean_lemma_stem2 = [cistem_stemming(x) for x in interessen_clean_lemma_stem1]
    interessen_liste = interessen_clean_lemma_stem2
    return interessen_liste

# skills preprocessen (cleanen + lemman + stemmen)
def skills_preprocessen(skills, sprache, nlp):
    # cleanen
    skills_clean = [clean_text(x) for x in skills]
    # lemma
    skills_clean_lemma = [spacy_lemma(x, nlp) for x in skills_clean]
    # stem1
    skills_clean_lemma_stem1 = [snowball_stemming(x, sprache) for x in skills_clean_lemma]
    # stem2
    skills_clean_lemma_stem2 = [cistem_stemming(x) for x in skills_clean_lemma_stem1]
    skills_liste = skills_clean_lemma_stem2
    return skills_liste

# benefits_liste preprocessen (cleanen + lemman + stemmen)
def benefits_preprocessen(benefits, sprache, nlp):
    # cleanen
    benefits_clean = [clean_text(x) for x in benefits]
    # lemma
    benefits_clean_lemma = [spacy_lemma(x, nlp) for x in benefits_clean]
    # stem1
    benefits_clean_lemma_stem1 = [snowball_stemming(x, sprache) for x in benefits_clean_lemma]
    # stem2
    benefits_clean_lemma_stem2 = [cistem_stemming(x) for x in benefits_clean_lemma_stem1]
    benefits_liste = benefits_clean_lemma_stem2
    return benefits_liste

# Ähnlichkeit zw. Interessen & Aufgaben aus Anzeige kalkulieren (mittels cosine similarity und bag of words Verfahren)
# zusätzlich die gematchten tokens speichern
def aufgaben_aehnlichkeit_berechnen(df, interessen_liste):
    # vorab muss für den vectorizer muss text ein ganzer string sein und keine liste --> daher hier zusammenführen
    df['Aufgaben_clean_stpwrds_cosine'] = df['Aufgaben_clean_stpwrds'].apply(lambda x: ' '.join(x))
    # vectorizer erstellen
    vectorizer = CountVectorizer()
    # vectorizer fitten & transformen
    vectorizer_x = vectorizer.fit_transform(df['Aufgaben_clean_stpwrds_cosine'])
    # die interessen liste transformieren
    interessen = " ".join(interessen_liste)
    interessen_vector = vectorizer.transform([interessen])
    aehnlichkeit_werte_aufgaben = cosine_similarity(interessen_vector, vectorizer_x)

    # ähnlichkeitswerte speichern
    for i, wert in enumerate(aehnlichkeit_werte_aufgaben[0]):
        df.at[i, 'aufgaben_score'] = wert
        # die gematchten tokens auch speichern
        matched_tokens = []
        if wert != 0:
            job_tokens = str(df.loc[i, 'Aufgaben_clean_stpwrds_cosine']).split()
            query_tokens = interessen.split()
            for token in query_tokens:
                if token in job_tokens:
                    matched_tokens.append(token)
            df.at[i, 'matched_tasks'] = " ".join(matched_tokens)

    return df

# Ähnlichkeit zw. Skills & requirements aus Anzeige kalkulieren (mittels cosine similarity und bag of words Verfahren)
# zusätzlich die gematchten tokens speichern
def profil_aehnlichkeit_berechnen(df, skills_liste):
    #print(f' profil clean stpwrds: {df["Profil_clean_stpwrds"]}')
    # für die vectorizer muss der text ein ganzer string sein und keine liste --> daher hier zusammenführen
    df['Profil_clean_stpwrds_cosine'] = df['Profil_clean_stpwrds'].apply(
        lambda x: ' '.join([str(i) for i in x]) if isinstance(x, (list, tuple)) else str(x))
    # vectorizer erstellen
    vectorizer = CountVectorizer()
    # vectorizer fitten & transform
    vectorizer_x = vectorizer.fit_transform(df['Profil_clean_stpwrds_cosine'])

    # die skills liste transformieren
    skills = " ".join(skills_liste)
    skills_vector = vectorizer.transform([skills])

    aehnlichkeit_werte_skills = cosine_similarity(skills_vector, vectorizer_x)

    # ähnlichkeitswerte speichern
    for i, wert in enumerate(aehnlichkeit_werte_skills[0]):
        df.at[i, 'profil_score'] = wert
        # die gematchten tokens auch speichern
        matched_tokens = []
        if wert != 0:
            job_tokens = str(df.loc[i, 'Profil_clean_stpwrds_cosine']).split()
            query_tokens = skills.split()
            for token in query_tokens:
                if token in job_tokens:
                    matched_tokens.append(token)
            df.at[i, 'matched_profil'] = " ".join(matched_tokens)
    return df


# Jaccard-Ähnlichkeit berechnen (Menge überschneidender Wörter zweier Strings / Anzahl der Wörter in beiden strings)
def jaccard_aehnlichkeit_berechnen(liste1, liste2):
    menge1 = set(liste1)
    menge2 = set(liste2)
    ueberschneidungsmenge = len(menge1.intersection(menge2))
    gesamtmenge = len(menge1.union(menge2))
    return ueberschneidungsmenge / gesamtmenge

# Ähnlichkeit zw. Wünschen & benefits aus Anzeige kalkulieren (mittels cosine similarity und bag of words Verfahren)
def benefits_aehnlichkeit_berechnen(df, benefits_liste):
    # für die vectorizer muss der text ein ganzer string sein und keine liste --> daher hier zusammenführen
    df['Benefits_clean_stpwrds_cosine'] = df['Benefits_clean_stpwrds'].apply(
        lambda x: ' '.join([str(i) for i in x]) if isinstance(x, (list, tuple)) else str(x))
    # vectorizer erstellen
    vectorizer = CountVectorizer()
    # vectorizer fitten & transform
    vectorizer_x = vectorizer.fit_transform(df['Benefits_clean_stpwrds_cosine'])

    # die query transformieren
    benefits = " ".join(benefits_liste)
    benefits_vector = vectorizer.transform([benefits])

    aehnlichkeit_werte_benefits = cosine_similarity(benefits_vector, vectorizer_x)

    # ähnlichkeitswerte speichern
    for i, wert in enumerate(aehnlichkeit_werte_benefits[0]):
        df.at[i, 'benefits_score'] = wert

    return df
