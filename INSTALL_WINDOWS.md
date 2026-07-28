# Installing SabzalStudio on Windows

Everything below is done once. Afterwards, starting the app is a single
command.

---

## 1. Python

Install Python 3.10 or newer from <https://www.python.org/downloads/>.

**Tick "Add python.exe to PATH" on the first screen of the installer.** It is
easy to miss, and almost every "python is not recognized" problem comes from
skipping it.

Check it worked, in Command Prompt or PowerShell:

```powershell
python --version
```

---

## 2. Get the project

Either download the ZIP and extract it, or clone it:

```powershell
git clone https://github.com/KingSabzal/SabzalStudio.git
cd SabzalStudio
```

---

## 3. A virtual environment (recommended)

This keeps the project's packages away from the rest of your system.

```powershell
python -m venv venv
venv\Scripts\activate
```

Your prompt now starts with `(venv)`. Run the remaining commands with it
active. Next time you open a terminal, run `venv\Scripts\activate` again
before starting the app.

If PowerShell refuses with a script execution error, either use Command Prompt
instead, or allow local scripts once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 4. Install the packages

```powershell
pip install -r requirements.txt
```

This takes a few minutes. Torch and Whisper are large.

**ffmpeg is not a separate install.** A copy is bundled and put on the path
automatically the first time you run anything.

---

## 5. ImageMagick (for captions)

Captions are drawn with ImageMagick.

1. Download it from <https://imagemagick.org/script/download.php#windows>
2. Run the installer
3. **Tick "Install legacy utilities (e.g. convert)"** — the project needs it
4. Leave "Add application directory to your system path" ticked

Check:

```powershell
magick -version
```

If a caption ever fails to draw, the render says so and carries on with the
rest of the video, so a missing ImageMagick is annoying rather than fatal.

---

## 6. Start it

```powershell
streamlit run app.py
```

Your browser opens on the interface. Go to **Settings** and add:

* a **Pexels key**, free from <https://www.pexels.com/api/new/>
* an **AI provider** — 9Router, OpenRouter, NVIDIA NIM or Cloudflare Workers AI
* optionally a **Pixabay key**, free from <https://pixabay.com/api/key/>

Press **Test the connection** to check the provider before generating
anything.

---

## Windows-specific notes

**Long file names.** Video files are named after their upload title. The name
is capped at 120 characters and cut on a word boundary, and Windows reserved
names such as `CON` are handled, so no title can produce a file Windows
refuses to create.

**Antivirus and the first run.** The bundled ffmpeg is copied to `bin\` on
first use. Some antivirus tools scan it and slow that first run down. It only
happens once.

**Whisper's first transcription** downloads its model, roughly 1.5 GB. That
also happens once.

**Paths with spaces** are fine. The project works from anywhere, including
`C:\Users\Your Name\Documents`.

---

## Common problems

**`python is not recognized`**
Python was installed without being added to PATH. Re-run the installer, choose
Modify, and tick the PATH option.

**`streamlit is not recognized`**
The virtual environment is not active. Run `venv\Scripts\activate` first.

**A caption renders as a plain box, or captions are missing**
ImageMagick is not installed, or it was installed without the legacy
utilities. Re-run its installer and tick that box.

**A run stops during the Footage stage**
The connection dropped or the media sources are rate-limiting. Nothing is
lost: the checkpoint is saved, so generating the same topic again resumes from
that stage. Adding a free Pixabay key makes this much less likely.

**`config.json` was edited by hand and now the app complains**
Delete it. The defaults come back, and you can set everything again from the
Settings tab.
