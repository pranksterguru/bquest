import boto3
import pandas as pd
import concurrent.futures
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from io import StringIO
from sklearn.metrics import classification_report, confusion_matrix

logging.basicConfig(filename="lex_accuracy.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)
CORS(app)

BOT_NAME = 'YourLexBot'
BOT_ALIAS = 'YourLexAlias'
USER_ID = 'test_user'

client = boto3.client('lex-runtime')

uploaded_files = {}

def test_utterance(utterance, expected_intent):
    try:
        response = client.post_text(
            botName=BOT_NAME,
            botAlias=BOT_ALIAS,
            userId=USER_ID,
            inputText=utterance
        )
        detected_intent = response.get('intentName', 'None')
        confidence = response.get('nluIntentConfidence', {}).get('score', 0)
        return expected_intent, detected_intent, confidence
    except Exception as e:
        logging.error(f"Error processing utterance '{utterance}': {e}")
        return expected_intent, "ERROR", 0

@app.route('/upload', methods=['POST'])
def upload_files():
    global uploaded_files
    files = request.files.getlist("files")
    uploaded_files.clear()

    for file in files:
        intent_name = file.filename.rsplit('.', 1)[0]  # Extract intent name from filename
        df = pd.read_csv(StringIO(file.stream.read().decode("utf-8")))
        df['expected_intent'] = intent_name
        uploaded_files[intent_name] = df  # Store in memory

    return jsonify({"message": "Files uploaded successfully", "files": list(uploaded_files.keys())})

@app.route('/start_test', methods=['POST'])
def start_test():
    if not uploaded_files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    test_data = pd.concat(uploaded_files.values(), ignore_index=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_utterance, row['utterance'], row['expected_intent']): row for _, row in test_data.iterrows()}
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    results_df = pd.DataFrame(results, columns=['expected_intent', 'detected_intent', 'confidence'])
    accuracy = (results_df['expected_intent'] == results_df['detected_intent']).mean()

    conf_matrix = confusion_matrix(results_df['expected_intent'], results_df['detected_intent']).tolist()
    class_report = classification_report(results_df['expected_intent'], results_df['detected_intent'], output_dict=True)

    return jsonify({
        "accuracy": round(accuracy * 100, 2),
        "confusion_matrix": conf_matrix,
        "classification_report": class_report
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
