from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string, flash
from werkzeug.exceptions import RequestEntityTooLarge
import time
import os

app = Flask(__name__)
app.secret_key = "supersecret"  # Needed for flash messages

# Configuration
UPLOAD_FOLDER = "/data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_FILE_SIZE = 5000 * 1024 * 1024      # 5 GB max per file
MAX_TOTAL_STORAGE = 50000 * 1024 * 1024 # 50 GB total
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# --- Helper: file info ---
def get_file_info(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.isfile(path):
        return None
    size = os.path.getsize(path)
    mtime = os.path.getmtime(path)

    # Human-readable size
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024*1024:
        size_str = f"{size/1024:.1f} KB"
    else:
        size_str = f"{size/(1024*1024):.1f} MB"

    # Format timestamp
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))

    return {"name": filename, "size": size_str, "mtime": time_str}

# --- Helper: check total storage ---
def check_total_storage(new_file_size):
    total_size = sum(
        os.path.getsize(os.path.join(UPLOAD_FOLDER, f))
        for f in os.listdir(UPLOAD_FOLDER)
        if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))
    )
    return total_size + new_file_size <= MAX_TOTAL_STORAGE

# --- HTML template ---
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
{% for file in files %}
  <li>
    <a href="{{ url_for('download_file', filename=file.name) }}">{{ file.name }}</a>
    ({{ file.size }}, modifié: {{ file.mtime }})
    - <a href="{{ url_for('delete_file', filename=file.name) }}">Supprimer</a>
  </li>
{% endfor %}
</ul>

<script>
const form = document.getElementById('uploadForm');
const progressBar = document.getElementById('progressBar');
const MAX_FILE_SIZE = {{ max_file_size }};

form.addEventListener('submit', function(event) {
    event.preventDefault();

    const fileInput = document.getElementById('file');
    if (!fileInput.files.length) return;

    const file = fileInput.files[0];
    if (file.size > MAX_FILE_SIZE) {
        alert("Erreur : le fichier est trop volumineux (max " + (MAX_FILE_SIZE / (1024*1024)).toFixed(1) + " Mo).");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/', true);

    // Track upload progress
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            progressBar.value = percent;
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            progressBar.value = 100;  // show completion
            setTimeout(() => {
                progressBar.value = 0;
                location.reload();
            }, 300);  // small delay so user sees the bar fill
        } else {
            alert("Erreur lors de l'upload du fichier.");
            progressBar.value = 0;
        }
    };

    xhr.onerror = function() {
        alert("Erreur réseau ou fichier trop volumineux.");
        progressBar.value = 0;
    };

    xhr.send(formData);
});
</script>
"""

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            # Check total storage
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0)
            if not check_total_storage(file_size):
                flash(f"Erreur : espace disque total dépassé ({MAX_TOTAL_STORAGE // (1024*1024)} Mo). Supprimez des fichiers avant d'ajouter.", "error")
                return redirect(url_for("index"))

            f.save(os.path.join(UPLOAD_FOLDER, f.filename))
        return redirect(url_for("index"))

    # Build file info list dynamically
    files = []
    for f in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, f)
        if os.path.isfile(path):
            info = get_file_info(f)
            if info:
                files.append(info)

    return render_template_string(HTML_PAGE, files=files, max_file_size=MAX_FILE_SIZE)

@app.route("/files/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/delete/<filename>")
def delete_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("index"))

# Handle files too large
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    flash(f"Erreur : le fichier est trop volumineux (max {MAX_FILE_SIZE // (1024*1024)} Mo).", "error")
    return redirect(url_for("index"))

# --- Run ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)