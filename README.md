# KudoBoard

A lightweight, server-rendered employee appreciation board with real-time updates and export to PDF.

## 🚀 Features
- Create Events
- Submit real-time appreciation messages using WebSockets
- Export all kudos as a sleek PDF using WeasyPrint

## 💻 Tech Stack
- **Backend**: Python, FastAPI, SQLAlchemy (SQLite), Jinja2
- **Frontend**: Server-rendered HTML, Tailwind CSS, Alpine.js, HTMX
- **PDF Engine**: WeasyPrint

---

## 🛠️ Installation & Setup

### 1. Install System Dependencies for WeasyPrint

**macOS:**
```bash
brew install pango cairo libffi
```

**Ubuntu / Debian (VPS):**
```bash
sudo apt-get update
sudo apt-get install -y pango1.0-tools libpango1.0-dev libcairo2-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info
```

### 2. Setup the Application Locally

Run the setup wrapper script which takes care of Virtual Environment creation and Package Installation:

```bash
./run.sh
```

Or do it manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Server

If you use the `./run.sh` script, it automatically sets the library fallback path.
Otherwise, on macOS with Homebrew, you may need to specify the path for WeasyPrint explicitly so it can locate `pango` and `cffi` libraries before launching:

```bash
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH"
uvicorn app.main:app --reload
```

The app will be available at `http://localhost:8000`. And the Admin Dashboard is at `http://localhost:8000/dash`.

### 4. (Optional) Add New Theme Categories & Images

If you wish to download additional background images or add brand new event categories to the app, you can utilize the `download_pixabay.py` script!

1. Sign up and get a free API Key from [Pixabay](https://pixabay.com/api/docs/).
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` and replace `YOUR_API_KEY_HERE` with your actual Pixabay API key. You can customize the image count or edit the `PIXABAY_THEMES` JSON map to assign your own Pixabay search terms to new category names.
4. Run the downloader:
   ```bash
   python download_pixabay.py
   ```
   *Note: If you invent completely new categories, remember to update the `THEMES` array in `app/main.py`, and link it to pastel CSS stylings mapped natively inside `app/templates/event.html` and `app/templates/pdf/event_pdf.html`!*

## 📂 Project Structure

- `app/`
  - `main.py` - FastAPI App with real-time WebSockets
  - `db.py` - Database models and setup
  - `services/pdf_service.py` - PDF export service
  - `templates/` - Jinja2 Templates powered by HTMX & Tailwind
    - `pdf/event_pdf.html` - PDF layout
