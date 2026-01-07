from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string, flash, session
from werkzeug.exceptions import RequestEntityTooLarge
import os

app = Flask(__name__)
app.secret_key = "supersecret"  # Needed for flash messages

# Configuration
UPLOAD_FOLDER = "/data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_FILE_SIZE = 5000 * 1024 * 1024      # 10 MB max per file
MAX_TOTAL_STORAGE = 50000 * 1024 * 1024 # 1 GB total
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# HTML template
HTML_PAGE = """
<h1>Drive LAN</h1>
<h2>Ajouter un fichier</h2>
<form id="uploadForm" method="post" enctype="multipart/form-data">
  <input id="file" type="file" name="file">
  <input type="submit" value="Envoyer">
</form>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <ul style="color:red;">
    {% for category, message in messages %}
      <li>{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}

<progress id="progressBar" value="0" max="100" style="width:300px; display:block; margin-top:10px;"></progress>

<h2>Fichiers :</h2>
<ul>
{% for filename in files %}
  <li>
    <a href="{{ url_for('download_file', filename=filename) }}">{{ filename }}</a>
    - <a href="{{ url_for('delete_file', filename=filename) }}">Supprimer</a>
  </li>
{% endfor %}
</ul>

<script>
const form = document.getElementById('uploadForm');
const progressBar = document.getElementById('progressBar');

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

form.addEventListener('submit', function(event) {
    event.preventDefault();

    const fileInput = document.getElementById('file');
    if (!fileInput.files.length) return;

    // Check file size before uploading
    if (fileInput.files[0].size > MAX_FILE_SIZE) {
        alert("Erreur : le fichier est trop volumineux (max 10 Mo).");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/', true);

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            progressBar.value = percent;
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            progressBar.value = 0;
            location.reload();
        }
    };

    xhr.send(formData);
});
<script>
"""

# Helper: check total storage
def check_total_storage(new_file_size):
    total_size = sum(
        os.path.getsize(os.path.join(UPLOAD_FOLDER, f))
        for f in os.listdir(UPLOAD_FOLDER)
    )
    if total_size + new_file_size > MAX_TOTAL_STORAGE:
        return False
    return True

# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files["file"]
        if f.filename != "":
            # Check total storage
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0)
            if not check_total_storage(file_size):
                flash(f"Erreur : espace disque total dépassé ({MAX_TOTAL_STORAGE // (1024*1024)} Mo). Supprimez des fichiers avant d'ajouter.", "error")
                return redirect(url_for("index"))

            f.save(os.path.join(UPLOAD_FOLDER, f.filename))
        return redirect(url_for("index"))
    files = os.listdir(UPLOAD_FOLDER)
    return render_template_string(HTML_PAGE, files=files)

@app.route("/files/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/delete/<filename>")
def delete_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("index"))


# Handle file too large
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash(f"Erreur : le fichier est trop volumineux (max {MAX_FILE_SIZE // (1024*1024)} Mo).", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)