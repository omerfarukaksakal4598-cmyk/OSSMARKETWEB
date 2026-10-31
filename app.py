
import streamlit as st
import json
import uuid
import os
import re
import hashlib
import hmac
import secrets
from pathlib import Path
from datetime import datetime

# ==================================================
# OSS MARKET CONFIG
# ==================================================

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
IMAGES = DATA / "images"
UPLOADS = DATA / "uploads"

DB = DATA / "catalog.json"
ADMIN_DB = DATA / "admin.json"

for folder in (DATA, IMAGES, UPLOADS):
    folder.mkdir(parents=True, exist_ok=True)

if not DB.exists():
    DB.write_text("[]", encoding="utf-8")

st.set_page_config(
    page_title="OSS Market",
    page_icon="🛍️",
    layout="wide"
)

DEFAULT_PASSWORD = "OSS-Admin-2026"

# ==================================================
# DATABASE
# ==================================================

def load_apps():
    try:
        result = json.loads(DB.read_text(encoding="utf-8"))
        return result if isinstance(result, list) else []
    except Exception:
        return []

def save_apps(apps):
    temp = DB.with_suffix(".tmp")
    temp.write_text(
        json.dumps(apps, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temp.replace(DB)

def load_admin():
    if not ADMIN_DB.exists():
        return None

    try:
        return json.loads(ADMIN_DB.read_text(encoding="utf-8"))
    except Exception:
        return None

def save_admin(data):
    temp = ADMIN_DB.with_suffix(".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temp.replace(ADMIN_DB)

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        310000
    ).hex()

def verify_password(password, admin):
    if not admin:
        return False

    calculated = password_hash(
        password,
        admin["salt"]
    )

    return hmac.compare_digest(
        calculated,
        admin["hash"]
    )

def set_password(password):
    salt = secrets.token_hex(16)

    save_admin({
        "salt": salt,
        "hash": password_hash(password, salt),
        "changed": True
    })

# ==================================================
# FILE FUNCTIONS
# ==================================================

def safe_filename(name):
    name = Path(name).name
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:100] or "download.bin"

def save_upload(upload, folder, app_id):
    if upload is None:
        return ""

    extension = Path(upload.name).suffix.lower()
    filename = app_id + extension

    target = folder / filename
    target.write_bytes(upload.getbuffer())

    return filename

def remove_file(folder, filename):
    if not filename:
        return

    target = folder / Path(filename).name

    if target.exists():
        target.unlink()

# ==================================================
# ADMIN AUTHENTICATION
# ==================================================

def admin_login():
    st.sidebar.title("Yönetici Paneli")

    admin = load_admin()

    # İlk kurulum
    if admin is None:
        st.sidebar.info("İlk yönetici kurulumu")

        with st.sidebar.form("first_login"):
            password = st.text_input(
                "İlk giriş şifresi",
                type="password"
            )

            submit = st.form_submit_button(
                "Giriş yap",
                use_container_width=True
            )

        if submit:
            if password == DEFAULT_PASSWORD:
                st.session_state["admin"] = True
                st.session_state["must_change_password"] = True
                st.rerun()
            else:
                st.sidebar.error("İlk giriş şifresi yanlış.")

        return

    # Normal giriş
    if not st.session_state.get("admin", False):
        with st.sidebar.form("login"):
            password = st.text_input(
                "Yönetici şifresi",
                type="password"
            )

            submit = st.form_submit_button(
                "Giriş yap",
                use_container_width=True
            )

        if submit:
            if verify_password(password, admin):
                st.session_state["admin"] = True
                st.session_state["must_change_password"] = False
                st.rerun()
            else:
                st.sidebar.error("Şifre yanlış.")

    else:
        st.sidebar.success("Yönetici girişi açık")

        if st.sidebar.button("Oturumu kapat"):
            st.session_state["admin"] = False
            st.session_state["must_change_password"] = False
            st.rerun()

# ==================================================
# PASSWORD CHANGE
# ==================================================

def password_change_screen():
    st.title("🔐 Yönetici şifresi belirle")

    st.warning(
        "Güvenlik nedeniyle yönetim panelini kullanmadan önce "
        "varsayılan şifreni değiştirmelisin."
    )

    with st.form("mandatory_password_change"):
        new_password = st.text_input(
            "Yeni şifre",
            type="password"
        )

        repeat_password = st.text_input(
            "Yeni şifreyi tekrar gir",
            type="password"
        )

        submit = st.form_submit_button(
            "Şifremi kaydet",
            use_container_width=True
        )

        if submit:
            if len(new_password) < 10:
                st.error("Şifre en az 10 karakter olmalı.")

            elif new_password != repeat_password:
                st.error("Şifreler eşleşmiyor.")

            elif new_password == DEFAULT_PASSWORD:
                st.error("Varsayılan şifreyi kullanamazsın.")

            else:
                set_password(new_password)

                st.session_state["must_change_password"] = False
                st.success("Yeni şifren kaydedildi.")
                st.rerun()

# ==================================================
# DESIGN
# ==================================================

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
    padding: 32px;
    border-radius: 20px;
    background: linear-gradient(120deg,#172554,#312e81);
    margin-bottom: 25px;
    border: 1px solid #334155;
}
.hero h1 {
    color: white;
    font-size: 42px;
    margin: 0;
}
.hero p {
    color: #cbd5e1;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# HEADER
# ==================================================

st.markdown("""
<div class="hero">
    <h1>OSS MARKET</h1>
    <p>Kendi uygulama mağazan.</p>
    <p>OSS uygulamalarını keşfet, tanıt ve indir.</p>
</div>
""", unsafe_allow_html=True)

admin_login()

# Zorunlu şifre değişikliği
if (
    st.session_state.get("admin", False)
    and st.session_state.get("must_change_password", False)
):
    password_change_screen()
    st.stop()

apps = load_apps()

# ==================================================
# TABS
# ==================================================

market_tab, manage_tab = st.tabs([
    "🛒 Uygulama Mağazası",
    "⚙️ Yönetim Paneli"
])

# ==================================================
# MARKET
# ==================================================

with market_tab:

    col1, col2 = st.columns([3, 1])

    with col1:
        search = st.text_input(
            "Uygulama ara",
            placeholder="OSS Browser..."
        )

    with col2:
        categories = ["Tümü"] + sorted({
            app.get("category", "Diğer")
            for app in apps
        })

        selected_category = st.selectbox(
            "Kategori",
            categories
        )

    filtered = []

    for app in apps:
        searchable = (
            app.get("name", "") + " " +
            app.get("short", "") + " " +
            app.get("description", "")
        ).lower()

        if search.lower() not in searchable:
            continue

        if (
            selected_category != "Tümü"
            and app.get("category") != selected_category
        ):
            continue

        filtered.append(app)

    st.caption(f"{len(filtered)} uygulama")

    if not filtered:
        st.info("Henüz uygulama eklenmemiş.")

    for app in filtered:

        with st.container(border=True):

            image_path = IMAGES / app.get("image", "")

            if app.get("image") and image_path.is_file():
                left, right = st.columns([1, 2.5])
            else:
                left, right = st.columns([1, 2.5])

            with left:
                if app.get("image") and image_path.is_file():
                    st.image(
                        str(image_path),
                        use_container_width=True
                    )
                else:
                    st.markdown("## 📦")

            with right:
                st.subheader(app.get("name", "İsimsiz uygulama"))

                st.caption(
                    f'{app.get("category", "Diğer")} · '
                    f'v{app.get("version", "1.0")}'
                )

                if app.get("short"):
                    st.write(app["short"])

                if app.get("description"):
                    with st.expander("Uygulama açıklaması"):
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
            "Yönetim panelini kullanmak için giriş yapmalısın."
        )

    else:

        st.title("Yönetim Merkezi")

        add_tab, edit_tab, security_tab = st.tabs([
            "＋ Uygulama ekle",
            "📦 Uygulamaları yönet",
            "🔐 Güvenlik"
        ])

        # ------------------------------------------
        # ADD APPLICATION
        # ------------------------------------------

        with add_tab:

            with st.form("new_app", clear_on_submit=True):

                name = st.text_input("Uygulama adı *")

                col1, col2 = st.columns(2)

                with col1:
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

                with col2:
                    short = st.text_input(
                        "Kısa tanıtım (isteğe bağlı)"
                    )

                    website = st.text_input(
                        "Proje bağlantısı (isteğe bağlı)"
                    )

                description = st.text_area(
                    "Uygulama açıklaması (isteğe bağlı)",
                    height=140
                )

                image = st.file_uploader(
                    "Kapak görseli (isteğe bağlı)",
                    type=["png", "jpg", "jpeg", "webp"]
                )

                upload = st.file_uploader(
                    "Uygulama dosyası *",
                    help="EXE, ZIP, APK ve diğer dosyalar."
                )

                submit = st.form_submit_button(
                    "🚀 Mağazaya ekle",
                    use_container_width=True
                )

                if submit:

                    if not name.strip():
                        st.error("Uygulama adı zorunludur.")

                    elif upload is None:
                        st.error("Uygulama dosyası zorunludur.")

                    else:
                        app_id = uuid.uuid4().hex

                        filename = save_upload(
                            upload,
                            UPLOADS,
                            app_id
                        )

                        image_name = save_upload(
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
                            "original_filename": safe_filename(upload.name),
                            "image": image_name,
                            "date": datetime.now().strftime(
                                "%d.%m.%Y %H:%M"
                            )
                        }

                        apps.append(new_app)
                        save_apps(apps)

                        st.success("Uygulama mağazaya eklendi.")
                        st.rerun()

        # ------------------------------------------
        # EDIT / DELETE
        # ------------------------------------------

        with edit_tab:

            if not apps:
                st.info("Henüz uygulama yok.")

            for app in apps:

                with st.expander(
                    f'{app["name"]} · v{app["version"]}'
                ):

                    with st.form("edit_" + app["id"]):

                        new_name = st.text_input(
                            "Uygulama adı",
                            value=app.get("name", "")
                        )

                        new_version = st.text_input(
                            "Sürüm",
                            value=app.get("version", "1.0")
                        )

                        new_short = st.text_input(
                            "Kısa tanıtım",
                            value=app.get("short", "")
                        )

                        new_description = st.text_area(
                            "Açıklama",
                            value=app.get("description", "")
                        )

                        new_website = st.text_input(
                            "Proje bağlantısı",
                            value=app.get("website", "")
                        )

                        new_image = st.file_uploader(
                            "Yeni görsel (isteğe bağlı)",
                            type=["png", "jpg", "jpeg", "webp"],
                            key="image_" + app["id"]
                        )

                        new_file = st.file_uploader(
                            "Yeni uygulama dosyası (isteğe bağlı)",
                            key="file_" + app["id"]
                        )

                        save_edit = st.form_submit_button(
                            "Değişiklikleri kaydet"
                        )

                        if save_edit:

                            current = load_apps()

                            target = next(
                                (
                                    x for x in current
                                    if x["id"] == app["id"]
                                ),
                                None
                            )

                            if target:
                                target.update({
                                    "name": new_name.strip(),
                                    "version": new_version.strip(),
                                    "short": new_short.strip(),
                                    "description": new_description.strip(),
                                    "website": new_website.strip()
                                })

                                if new_image:
                                    remove_file(IMAGES, target.get("image", ""))
                                    target["image"] = save_upload(
                                        new_image,
                                        IMAGES,
                                        app["id"]
                                    )

                                if new_file:
                                    remove_file(UPLOADS, target.get("file", ""))
                                    target["file"] = save_upload(
                                        new_file,
                                        UPLOADS,
                                        app["id"]
                                    )
                                    target["original_filename"] = safe_filename(
                                        new_file.name
                                    )

                                save_apps(current)
                                st.success("Uygulama güncellendi.")
                                st.rerun()

                    confirm = st.checkbox(
                        "Silme işlemini onaylıyorum",
                        key="confirm_" + app["id"]
                    )

                    if st.button(
                        "🗑️ Uygulamayı sil",
                        key="delete_" + app["id"],
                        disabled=not confirm
                    ):
                        current = load_apps()

                        target = next(
                            (
                                x for x in current
                                if x["id"] == app["id"]
                            ),
                            None
                        )

                        if target:
                            remove_file(UPLOADS, target.get("file", ""))
                            remove_file(IMAGES, target.get("image", ""))

                            current = [
                                x for x in current
                                if x["id"] != app["id"]
                            ]

                            save_apps(current)

                        st.success("Uygulama silindi.")
                        st.rerun()

        # ------------------------------------------
        # SECURITY
        # ------------------------------------------

        with security_tab:

            st.subheader("Yönetici şifresini değiştir")

            with st.form("change_password"):

                old_password = st.text_input(
                    "Mevcut şifre",
                    type="password"
                )

                new_password = st.text_input(
                    "Yeni şifre",
                    type="password"
                )

                repeat_password = st.text_input(
                    "Yeni şifre tekrar",
                    type="password"
                )

                change = st.form_submit_button(
                    "Şifreyi değiştir"
                )

                if change:

                    admin = load_admin()

                    if not verify_password(old_password, admin):
                        st.error("Mevcut şifre yanlış.")

                    elif len(new_password) < 10:
                        st.error("Yeni şifre en az 10 karakter olmalı.")

                    elif new_password != repeat_password:
                        st.error("Yeni şifreler eşleşmiyor.")

                    else:
                        set_password(new_password)
                        st.success("Yönetici şifren değiştirildi.")

        st.divider()
        st.caption(f"Mağazada {len(apps)} uygulama bulunuyor.")
