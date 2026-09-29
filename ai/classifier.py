import joblib

model = joblib.load("ai/violence_classifier.pkl")
vectorizer = joblib.load("ai/tfidf_vectorizer.pkl")

LABELS = [
    "Physical Violence",
    "Emotional / Psychological Violence",
    "Economic Violence",
    "Sexual Violence",
    "Controlling Behaviour"
]


def analyze_report(text):

    text_vector = vectorizer.transform([text])

    probabilities = []

    for classifier in model.estimators_:
        probability = classifier.predict_proba(text_vector)[0]

        if len(probability) == 2:
            probabilities.append(probability[1])
        else:
            probabilities.append(0)

    result = {}

    for label, probability in zip(LABELS, probabilities):

        result[label] = {
            "detected": probability >= 0.35,
            "confidence": round(probability * 100, 2)
        }

    return result