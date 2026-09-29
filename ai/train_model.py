import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Load dataset
df = pd.read_csv("ai/dataset.csv")

# Input text
X = df["text"]

# AI output labels
labels = [
    "physical",
    "emotional",
    "economic",
    "sexual",
    "controlling"
]

y = df[labels]

# Convert text into numerical TF-IDF features
vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2)
)

X_tfidf = vectorizer.fit_transform(X)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X_tfidf,
    y,
    test_size=0.2,
    random_state=42
)

# Create multi-label classification model
model = MultiOutputClassifier(
    LogisticRegression(max_iter=1000)
)

# Train
print("Training AI model...")
model.fit(X_train, y_train)

print("Training completed.")

# Test model
y_pred = model.predict(X_test)

print("\n========== MODEL EVALUATION ==========\n")

for index, label in enumerate(labels):
    print(f"\n--- {label.upper()} ---")
    print(
        classification_report(
            y_test.iloc[:, index],
            y_pred[:, index],
            zero_division=0
        )
    )

# Save trained model
joblib.dump(model, "ai/violence_classifier.pkl")
joblib.dump(vectorizer, "ai/tfidf_vectorizer.pkl")

print("\n======================================")
print("AI model saved successfully!")
print("violence_classifier.pkl")
print("tfidf_vectorizer.pkl")
print("======================================")