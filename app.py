import os
import boto3
import pandas as pd
import concurrent.futures
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.metrics import classification_report, confusion_matrix
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(filename="lex_accuracy.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# AWS Lex Bot Details (Modify these)
BOT_NAME = 'YourLexBot'
BOT_ALIAS = 'YourLexAlias'
USER_ID = 'test_user'

# AWS Lex runtime client
client = boto3.client('lex-runtime')

# Directory for uploaded files
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def test_utterance(utterance, expected_intent):
    """Send an utterance to AWS Lex and validate the response."""
    try:
        response = client.post_text(
            botName=BOT_NAME,
            botAlias=BOT_ALIAS,
            userId=USER_ID,
            inputText=utterance
        )
        detected_intent = response.get('intentName', 'None')
        confidence = response.get('nluIntentConfidence', {}).get('score', 0)
        logging.info(f"Utterance: {utterance} | Expected: {expected_intent} | Detected: {detected_intent} | Confidence: {confidence:.2f}")
        return expected_intent, detected_intent, confidence
    except Exception as e:
        logging.error(f"Error processing utterance '{utterance}': {e}")
        return expected_intent, "ERROR", 0

@app.route('/upload', methods=['POST'])
def upload_files():
    """Upload and save CSV files."""
    files = request.files.getlist("files")
    filenames = []
    
    for file in files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        filenames.append(filename)
    
    return jsonify({"message": "Files uploaded successfully", "files": filenames})

@app.route('/start_test', methods=['POST'])
def start_test():
    """Runs the Lex test and returns the final result."""
    selected_files = request.json.get("files", [])
    if not selected_files:
        return jsonify({"error": "No files selected"}), 400

    results = []
    data = []

    # Load selected CSV files
    for file in selected_files:
        file_path = os.path.join(UPLOAD_FOLDER, file)
        if os.path.exists(file_path):
            intent_name = os.path.splitext(file)[0]
            df = pd.read_csv(file_path)
            df['expected_intent'] = intent_name  # Assign intent from filename
            data.append(df)
    
    if not data:
        return jsonify({"error": "No valid data found"}), 400

    test_data = pd.concat(data, ignore_index=True)

    # Process Lex queries
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_utterance, row['utterance'], row['expected_intent']): row for _, row in test_data.iterrows()}
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Convert results to DataFrame
    results_df = pd.DataFrame(results, columns=['expected_intent', 'detected_intent', 'confidence'])

    # Calculate accuracy
    accuracy = (results_df['expected_intent'] == results_df['detected_intent']).mean()

    # Generate Confusion Matrix
    conf_matrix = confusion_matrix(results_df['expected_intent'], results_df['detected_intent']).tolist()
    
    # Generate Classification Report
    class_report = classification_report(results_df['expected_intent'], results_df['detected_intent'], output_dict=True)

    return jsonify({
        "accuracy": round(accuracy * 100, 2),
        "confusion_matrix": conf_matrix,
        "classification_report": class_report
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
