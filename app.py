from flask import Flask, request, send_file, render_template_string, jsonify
import os
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# Store the latest image and answer in memory
latest_image = None
latest_answer = None
latest_timestamp = None

HTML_FORM = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CAPTCHA Solver - sellmyagent.com</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .captcha-image {
            text-align: center;
            margin: 20px 0;
        }
        .captcha-image img {
            max-width: 400px;
            max-height: 400px;
            border: 2px solid #ddd;
            border-radius: 5px;
        }
        .form-group {
            text-align: center;
            margin: 20px 0;
        }
        input[type="number"] {
            padding: 10px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 5px;
            width: 200px;
            margin-right: 10px;
        }
        input[type="submit"] {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background-color: #0056b3;
        }
        .status {
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔐 CAPTCHA Solver</h2>
        {% if image_url %}
            <div class="captcha-image">
                <img src="{{ image_url }}" alt="CAPTCHA Image"/>
            </div>
        {% endif %}
        <form method="post" action="/solve">
            <div class="form-group">
                <input type="number" name="answer" min="0" max="5" required placeholder="Enter answer (0-5)">
                <input type="submit" value="Submit Answer">
            </div>
        </form>
        {% if message %}
            <div class="status {{ message_type }}">
                {{ message }}
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_FORM, image_url='/captcha_img' if latest_image else None)

@app.route('/upload', methods=['POST'])
def upload_image():
    global latest_image, latest_answer, latest_timestamp
    import time
    print(f"🔄 UPLOAD ENDPOINT CALLED - Current answer before: {latest_answer}")
    if 'image' in request.files:
        # New image upload - ALWAYS clear the answer and set new timestamp
        latest_image = request.files['image'].read()
        latest_answer = None
        latest_timestamp = time.time()
        print(f"🔄 IMAGE UPLOAD: Cache cleared - new image uploaded, answer reset to: {latest_answer}, timestamp: {latest_timestamp}")
        return jsonify({'status': 'success', 'message': 'Image uploaded and cache cleared', 'timestamp': latest_timestamp})
    print("❌ No image provided in upload request")
    return jsonify({'status': 'error', 'message': 'No image provided'}), 400

@app.route('/solve', methods=['POST', 'GET'])
def solve():
    global latest_image, latest_answer, latest_timestamp
    import time
    if request.method == 'POST':
        if 'image' in request.files:
            # New image upload - ALWAYS clear the answer
            latest_image = request.files['image'].read()
            latest_answer = None
            latest_timestamp = time.time()
            print(f"🔄 SOLVE ENDPOINT: Cache cleared - new image uploaded, answer reset to: {latest_answer}, timestamp: {latest_timestamp}")
            return render_template_string(HTML_FORM, image_url='/captcha_img', message="New CAPTCHA received! Please solve it.", message_type="success")
        elif 'answer' in request.form:
            # Human submits answer
            latest_answer = request.form['answer']
            print(f"✅ SOLVE ENDPOINT: Answer received and stored: {latest_answer}")
            return render_template_string(HTML_FORM, image_url='/captcha_img' if latest_image else None, message="Answer submitted! You can close this tab.", message_type="success")
    # GET request: show form with image if available
    return render_template_string(HTML_FORM, image_url='/captcha_img' if latest_image else None)

@app.route('/captcha_img')
def captcha_img():
    global latest_image
    if latest_image:
        return send_file(BytesIO(latest_image), mimetype='image/png')
    return '', 404

@app.route('/answer', methods=['GET'])
def answer():
    global latest_answer, latest_timestamp
    import time
    current_time = time.time()
    print(f"🔍 ANSWER ENDPOINT CALLED - Current answer: {latest_answer}, timestamp: {latest_timestamp}, current time: {current_time}")
    
    # Only return answer if it was submitted after the latest image upload
    if latest_answer is not None and latest_timestamp is not None:
        # Check if answer was submitted within last 5 minutes of image upload
        if current_time - latest_timestamp < 300:  # 5 minutes
            print(f"📤 Returning valid answer: {latest_answer}")
            return jsonify({'answer': latest_answer})
        else:
            print(f"⚠️  Answer too old, clearing: {latest_answer}")
            latest_answer = None
            return jsonify({'answer': None})
    elif latest_answer is not None:
        print(f"⚠️  Answer exists but no timestamp, clearing: {latest_answer}")
        latest_answer = None
        return jsonify({'answer': None})
    
    print("📤 Returning null answer")
    return jsonify({'answer': None})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'captcha-solver'})

@app.route('/debug', methods=['GET'])
def debug():
    global latest_image, latest_answer, latest_timestamp
    import time
    current_time = time.time()
    return jsonify({
        'latest_answer': latest_answer,
        'has_image': latest_image is not None,
        'image_size': len(latest_image) if latest_image else 0,
        'latest_timestamp': latest_timestamp,
        'current_time': current_time,
        'time_diff': current_time - latest_timestamp if latest_timestamp else None
    })

@app.route('/clear', methods=['POST'])
def clear_cache():
    global latest_image, latest_answer, latest_timestamp
    print(f"🔄 CLEAR ENDPOINT CALLED - Current answer before: {latest_answer}")
    latest_answer = None
    latest_timestamp = None
    print(f"🔄 Manual cache clear - answer reset to: {latest_answer}, timestamp reset")
    return jsonify({'status': 'cache_cleared', 'answer': latest_answer})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 