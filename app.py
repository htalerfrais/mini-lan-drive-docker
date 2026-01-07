from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string
import os

app = Flask(__name__)

# This is the folder inside the container (Docker volume will be mounted here)
UPLOAD_FOLDER = "/data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simple HTML template for upload/list
HTML_PAGE = """
<h1>LAN Drive</h1>
<h2>Upload a file</h2>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="file">
  <input type="submit" value="Upload">
</form>
<h2>Files:</h2>
<ul>
{% for filename in files %}
  <li>
    <a href="{{ url_for('download_file', filename=filename) }}">{{ filename }}</a>
    - <a href="{{ url_for('delete_file', filename=filename) }}">Delete</a>
  </li>
{% endfor %}
</ul>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files["file"]
        if f.filename != "":
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)