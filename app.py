
import streamlit as st
import json
import uuid
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

# ---------------- CONFIG ----------------

ROOT = Path(__file__).parent
DATA = ROOT / "data"
IMAGES = DATA / "images"
UPLOADS = DATA / "uploads"
DB = DATA / "catalog.json"

for folder in [DATA, IMAGES, UPLOADS]:
    folder.mkdir(parents=True, exist_ok=True)

if not DB.exists():
    DB.write_text("[]", encoding="utf-8")

st.set_page_config(
    page_title="OSS Market",
    page_icon="🛍️",
    layout="wide"
)

# ---------------- DESIGN ----------------

st.markdown("""
<style>
.stApp {
    background: #0b1120;
    color: #f1f5f9;
}
section[data-testid="stSidebar"] {
    background: #111827;
}
.hero {
    padding: 30px;
    border-radius: 18px;
    background: linear-gradient(120deg,#172554,#312e81);
    margin-bottom: 25px;
}
.hero h1 {
    color: white;
    font-size: 42px;
    margin: 0;
}
.hero p {
    color: #cbd5e1;
    font-size: 16px;
}
.app-card {
    background: #172033;
    border: 1px solid #29364b;
    border-radius: 15px;
    padding: 15px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE ----------------

def load_apps():
    try:
        return json.loads(DB.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_apps(apps):
    temp = DB.with_suffix(".tmp")
    temp.write_text(
        json.dumps(apps, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temp.replace(DB)

def safe_filename(name):
    name = Path(name).name
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:100] or "download.bin"

def save_file(upload, folder, app_id):
    if upload is None:
        return ""

    ext = Path(upload.name).suffix.lower()
    filename = app_id + ext
    path = folder / filename
    path.write_bytes(upload.getbuffer())
    return filename

def remove_file(folder, filename):
    if not filename:
        return

    path = folder / Path(filename).name

    if path.exists():
        path.unlink()

# ---------------- ADMIN ----------------

def admin_password():
    return os.environ.get(
        "OSS_MARKET_PASSWORD",
        "OSS-Admin-2026"
    )

def admin_login():
    st.sidebar.title("Yönetici")

    if not st.session_state.get("admin", False):

        with st.sidebar.form("login"):
            password = st.text_input(
                "Yönetici şifresi",
                type="password"
            )

            login = st.form_submit_button(
                "Giriş yap",
                use_container_width=True
            )

        if login:
            if hashlib.sha256(password.encode()).digest() == hashlib.sha256(admin_password().encode()).digest():
                st.session_state.admin = True
                st.rerun()
            else:
                st.sidebar.error("Şifre yanlış.")

    else:
        st.sidebar.success("Yönetici girişi açık")

        if st.sidebar.button("Çıkış yap"):
            st.session_state.admin = False
            st.rerun()

# ---------------- HEADER ----------------

st.markdown("""
<div class="hero">
    <h1>OSS MARKET</h1>
    <p>OSS uygulamalarının kişisel mağazası.</p>
    <p>Uygulamalarını keşfet, incele ve indir.</p>
</div>
""", unsafe_allow_html=True)

admin_login()

apps = load_apps()

# ---------------- TABS ----------------

market_tab, manage_tab = st.tabs([
    "🛒 Uygulama Mağazası",
    "⚙️ Yönetim Paneli"
])

# ==================================================
# MARKET
# ==================================================

with market_tab:

    search_col, category_col = st.columns([3, 1])

    with search_col:
        search = st.text_input(
            "🔎 Uygulama ara",
            placeholder="Örn: OSS Browser"
        )

    with category_col:
        categories = ["Tümü"] + sorted(
            set(a.get("category", "Diğer") for a in apps)
        )

        category = st.selectbox(
            "Kategori",
            categories
        )

    filtered = []

    for app in apps:

        text = (
            app.get("name", "") + " " +
            app.get("description", "")
        ).lower()

        if search.lower() not in text:
            continue

        if category != "Tümü" and app.get("category") != category:
            continue

        filtered.append(app)

    st.caption(f"{len(filtered)} uygulama bulundu.")

    if not filtered:
        st.info("Henüz uygulama eklenmemiş.")

    for app in filtered:

        with st.container(border=True):

            col1, col2 = st.columns([1, 2.5])

            with col1:
                image_path = IMAGES / app.get("image", "")

                if image_path.is_file():
                    st.image(str(image_path), use_container_width=True)
                else:
                    st.markdown("## 📦")

            with col2:

                st.subheader(app["name"])

                st.caption(
                    f'{app["category"]}  ·  Sürüm {app["version"]}'
                )

                st.write(app["description"])

                if app.get("website"):
                    st.link_button(
                        "Proje sayfası",
                        app["website"]
                    )

                file_path = UPLOADS / app.get("file", "")

                if file_path.is_file():

                    st.download_button(
                        "⬇️ Uygulamayı indir",
                        data=file_path.read_bytes(),
                        file_name=app.get(
                            "original_filename",
                            file_path.name
                        ),
                        mime="application/octet-stream",
                        key="download_" + app["id"]
                    )

# ==================================================
# MANAGEMENT
# ==================================================

with manage_tab:

    if not st.session_state.get("admin", False):

        st.warning(
            "Uygulama eklemek için yönetici girişi yapmalısın."
        )

    else:

        st.subheader("＋ Yeni uygulama ekle")

        with st.form("new_app", clear_on_submit=True):

            name = st.text_input("Uygulama adı")

            c1, c2 = st.columns(2)

            with c1:
                category = st.selectbox(
                    "Kategori",
                    [
                        "Tarayıcı",
                        "Araçlar",
                        "Üretkenlik",
                        "Multimedya",
                        "Oyun",
                        "Geliştirici araçları",
                        "Diğer"
                    ]
                )

                version = st.text_input(
                    "Sürüm",
                    value="1.0"
                )

            with c2:
                short = st.text_input("Kısa tanıtım")
                website = st.text_input(
                    "Proje bağlantısı (isteğe bağlı)"
                )

            description = st.text_area(
                "Uygulama açıklaması",
                height=150
            )

            image = st.file_uploader(
                "Kapak görseli",
                type=["png", "jpg", "jpeg", "webp"]
            )

            file = st.file_uploader(
                "İndirilebilir uygulama dosyası",
                help="EXE, ZIP, APK veya başka dosya türleri."
            )

            submit = st.form_submit_button(
                "🚀 Mağazaya ekle",
                use_container_width=True
            )

            if submit:

                if not name.strip() or not description.strip() or file is None:

                    st.error(
                        "Uygulama adı, açıklama ve dosya zorunludur."
                    )

                else:

                    app_id = uuid.uuid4().hex

                    filename = save_file(
                        file,
                        UPLOADS,
                        app_id
                    )

                    image_name = save_file(
                        image,
                        IMAGES,
                        app_id
                    ) if image else ""

                    new_app = {
                        "id": app_id,
                        "name": name.strip(),
                        "short": short.strip(),
                        "category": category,
                        "version": version.strip() or "1.0",
                        "website": website.strip(),
                        "description": description.strip(),
                        "file": filename,
                        "original_filename": safe_filename(file.name),
                        "image": image_name,
                        "date": datetime.now().strftime(
                            "%d.%m.%Y %H:%M"
                        )
                    }

                    apps.append(new_app)
                    save_apps(apps)

                    st.success("Uygulama eklendi!")
                    st.rerun()

        # ---------------- EDIT / DELETE ----------------

        st.divider()
        st.subheader("Mevcut uygulamalar")

        if not apps:
            st.info("Henüz uygulama yok.")

        for app in apps:

            with st.expander(
                f'{app["name"]} — v{app["version"]}'
            ):

                with st.form("edit_" + app["id"]):

                    new_name = st.text_input(
                        "Uygulama adı",
                        value=app["name"]
                    )

                    new_version = st.text_input(
                        "Sürüm",
                        value=app["version"]
                    )

                    new_description = st.text_area(
                        "Açıklama",
                        value=app["description"]
                    )

                    new_website = st.text_input(
                        "Proje bağlantısı",
                        value=app.get("website", "")
                    )

                    new_image = st.file_uploader(
                        "Yeni görsel",
                        type=["png", "jpg", "jpeg", "webp"],
                        key="img_" + app["id"]
                    )

                    new_file = st.file_uploader(
                        "Yeni uygulama dosyası",
                        key="file_" + app["id"]
                    )

                    save_edit = st.form_submit_button(
                        "Değişiklikleri kaydet"
                    )

                    if save_edit:

                        current = load_apps()

                        target = next(
                            (x for x in current if x["id"] == app["id"]),
                            None
                        )

                        if target:

                            target["name"] = new_name.strip()
                            target["version"] = new_version.strip()
                            target["description"] = new_description.strip()
                            target["website"] = new_website.strip()

                            if new_image:
                                remove_file(IMAGES, target["image"])
                                target["image"] = save_file(
                                    new_image,
                                    IMAGES,
                                    app["id"]
                                )

                            if new_file:
                                remove_file(UPLOADS, target["file"])
                                target["file"] = save_file(
                                    new_file,
                                    UPLOADS,
                                    app["id"]
                                )
                                target["original_filename"] = safe_filename(
                                    new_file.name
                                )

                            save_apps(current)
                            st.success("Güncellendi.")
                            st.rerun()

                confirm = st.checkbox(
                    "Silmek istediğimi onaylıyorum",
                    key="confirm_" + app["id"]
                )

                if st.button(
                    "🗑️ Uygulamayı sil",
                    key="delete_" + app["id"],
                    disabled=not confirm
                ):

                    remove_file(UPLOADS, app["file"])
                    remove_file(IMAGES, app["image"])

                    current = [
                        x for x in load_apps()
                        if x["id"] != app["id"]
                    ]

                    save_apps(current)
                    st.success("Uygulama silindi.")
                    st.rerun()

        st.divider()

        st.caption(
            f"Toplam {len(apps)} uygulama kayıtlı."
        )
