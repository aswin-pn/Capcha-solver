from flask import Flask, request, send_file, render_template_string, jsonify, session
import os
from io import BytesIO
from PIL import Image
import time
import uuid

app = Flask(__name__)
app.secret_key = 'debug-secret-key'  # Needed for session

# Store the latest image, answer, and a unique captcha_id in memory
latest_image = None
latest_answer = None
latest_captcha_id = None
latest_answer_time = None

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
        .debug {
            font-size: 12px;
            color: #888;
            margin-top: 10px;
        }
    </style>
    <script>
        function now() {
            return new Date().toISOString();
        }
        document.addEventListener('DOMContentLoaded', function() {
            console.log('[DEBUG] Page loaded at', now());
            var form = document.querySelector('form');
            if (form) {
                form.addEventListener('submit', function(e) {
                    var val = form.querySelector('input[name="answer"]').value;
                    var cid = form.querySelector('input[name="captcha_id"]').value;
                    console.log('[DEBUG] Form submitted at', now(), 'Value entered:', val, 'captcha_id:', cid);
                });
            }
            var img = document.querySelector('.captcha-image img');
            if (img) {
                img.addEventListener('load', function() {
                    console.log('[DEBUG] CAPTCHA image loaded at', now(), img.src);
                });
            }
            var answerInput = document.querySelector('input[name="answer"]');
            if (answerInput) {
                answerInput.addEventListener('input', function() {
                    console.log('[DEBUG] Input changed at', now(), answerInput.value);
                });
                // Log initial value
                console.log('[DEBUG] Initial input value at', now(), answerInput.value);
            }
            var cidInput = document.querySelector('input[name="captcha_id"]');
            if (cidInput) {
                console.log('[DEBUG] captcha_id for this form:', cidInput.value);
            }
        });
    </script>
</head>
<body>
    <div class="container">
        <h2>🔐 CAPTCHA Solver</h2>
        <div class="debug">
            <b>captcha_id:</b> {{ captcha_id }}<br>
            <b>Server time:</b> {{ server_time }}<br>
            <b>Latest answer:</b> {{ latest_answer }}<br>
            <b>Latest answer time:</b> {{ latest_answer_time }}<br>
        </div>
        {% if image_url %}
            <div class="captcha-image">
                <img src="{{ image_url }}" alt="CAPTCHA Image"/>
            </div>
        {% endif %}
        <form method="post" action="/solve">
            <div class="form-group">
                <input type="number" name="answer" min="0" max="5" required placeholder="Enter answer (0-5)" autocomplete="off">
                <input type="hidden" name="captcha_id" value="{{ captcha_id }}">
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
    global latest_captcha_id, latest_answer, latest_answer_time
    return render_template_string(
        HTML_FORM,
        image_url='/captcha_img' if latest_image else None,
        captcha_id=latest_captcha_id,
        server_time=time.strftime('%Y-%m-%d %H:%M:%S'),
        latest_answer=latest_answer,
        latest_answer_time=latest_answer_time
    )

@app.route('/solve', methods=['POST', 'GET'])
def solve():
    global latest_image, latest_answer, latest_captcha_id, latest_answer_time
    if request.method == 'POST':
        if 'image' in request.files:
            # New image upload
            latest_image = request.files['image'].read()
            latest_answer = None
            latest_captcha_id = str(uuid.uuid4())
            latest_answer_time = None
            print(f'[DEBUG] New CAPTCHA uploaded at {time.strftime("%H:%M:%S")}, captcha_id={latest_captcha_id}')
            if request.is_json or request.headers.get('Accept') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'captcha_id': latest_captcha_id})
            return render_template_string(HTML_FORM, image_url='/captcha_img', captcha_id=latest_captcha_id, server_time=time.strftime('%Y-%m-%d %H:%M:%S'), latest_answer=latest_answer, latest_answer_time=latest_answer_time, message="New CAPTCHA received! Please solve it.", message_type="success")
        elif 'answer' in request.form and 'captcha_id' in request.form:
            # Human submits answer
            answer = request.form['answer']
            captcha_id = request.form['captcha_id']
            print(f'[DEBUG] Answer submitted at {time.strftime("%H:%M:%S")}, answer={answer}, captcha_id={captcha_id}, expected_captcha_id={latest_captcha_id}')
            if captcha_id == latest_captcha_id:
                latest_answer = answer
                latest_answer_time = time.strftime('%Y-%m-%d %H:%M:%S')
                return render_template_string(HTML_FORM, image_url='/captcha_img' if latest_image else None, captcha_id=latest_captcha_id, server_time=time.strftime('%Y-%m-%d %H:%M:%S'), latest_answer=latest_answer, latest_answer_time=latest_answer_time, message="Answer submitted! You can close this tab.", message_type="success")
            else:
                print(f'[DEBUG] Mismatched captcha_id! Submitted: {captcha_id}, Expected: {latest_captcha_id}')
                return render_template_string(HTML_FORM, image_url='/captcha_img' if latest_image else None, captcha_id=latest_captcha_id, server_time=time.strftime('%Y-%m-%d %H:%M:%S'), latest_answer=latest_answer, latest_answer_time=latest_answer_time, message="Mismatched CAPTCHA ID! Please reload and try again.", message_type="error")
    # GET request: show form with image if available
    return render_template_string(HTML_FORM, image_url='/captcha_img' if latest_image else None, captcha_id=latest_captcha_id, server_time=time.strftime('%Y-%m-%d %H:%M:%S'), latest_answer=latest_answer, latest_answer_time=latest_answer_time)

@app.route('/captcha_img')
def captcha_img():
    global latest_image
    if latest_image:
        return send_file(BytesIO(latest_image), mimetype='image/png')
    return '', 404

@app.route('/answer', methods=['GET'])
def answer():
    global latest_answer, latest_image, latest_captcha_id, latest_answer_time
    if latest_answer is not None:
        ans = latest_answer
        ans_time = latest_answer_time
        cid = latest_captcha_id
        print(f'[DEBUG] /answer polled at {time.strftime("%H:%M:%S")}, returning answer={ans}, captcha_id={cid}, answer_time={ans_time}')
        # Clear both after the answer is retrieved
        latest_answer = None
        latest_image = None
        latest_captcha_id = None
        latest_answer_time = None
        return jsonify({'answer': ans, 'captcha_id': cid, 'answer_time': ans_time})
    print(f'[DEBUG] /answer polled at {time.strftime("%H:%M:%S")}, no answer available')
    return jsonify({'answer': None})

@app.route('/current', methods=['GET'])
def current():
    global latest_captcha_id
    return jsonify({'captcha_id': latest_captcha_id})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'captcha-solver'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port, debug=False) 