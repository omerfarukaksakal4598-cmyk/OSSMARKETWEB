
import streamlit as st
import json
import uuid
import os
import re
import hashlib
import hmac
import secrets
import io
import zipfile
from pathlib import Path
from datetime import datetime

# =========================================================
# OSS MARKET - CONFIGURATION
# =========================================================

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
    layout="wide",
    initial_sidebar_state="expanded"
)

DEFAULT_PASSWORD = "OSS-Admin-2026"

CATEGORIES = [
    "Tarayıcı",
    "Araçlar",
    "Üretkenlik",
    "Multimedya",
    "Oyun",
    "Geliştirici araçları",
    "Sistem",
    "Diğer"
]

# =========================================================
# DATABASE
# =========================================================

def load_apps():
    try:
        data = json.loads(DB.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
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
        return json.loads(
            ADMIN_DB.read_text(encoding="utf-8")
        )
    except Exception:
        return None


def save_admin(data):
    temp = ADMIN_DB.with_suffix(".tmp")

    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    temp.replace(ADMIN_DB)


# =========================================================
# PASSWORD SECURITY
# =========================================================

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

    try:
        calculated = password_hash(
            password,
            admin["salt"]
        )

        return hmac.compare_digest(
            calculated,
            admin["hash"]
        )
    except Exception:
        return False


def set_password(password):
    salt = secrets.token_hex(16)

    save_admin({
        "salt": salt,
        "hash": password_hash(password, salt),
        "changed": True,
        "updated": datetime.now().isoformat()
    })


# =========================================================
# FILE UTILITIES
# =========================================================

def safe_filename(name):
    name = Path(name).name

    name = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        name
    )

    return name[:120] or "download.bin"


def save_single_file(upload, app_id):
    if upload is None:
        return ""

    extension = Path(upload.name).suffix.lower()

    filename = app_id + extension

    destination = UPLOADS / filename

    destination.write_bytes(
        upload.getbuffer()
    )

    return filename


def save_folder_upload(uploaded_files, app_id):
    """
    Klasör dosyalarını göreli yollarıyla kaydeder.
    Alt klasörler korunur.
    """

    app_folder = UPLOADS / app_id
    app_folder.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for uploaded in uploaded_files:

        raw_path = uploaded.name.replace("\\", "/")

        relative_path = Path(raw_path)

        if relative_path.is_absolute():
            continue

        if ".." in relative_path.parts:
            continue

        if not relative_path.parts:
            continue

        target = app_folder.joinpath(*relative_path.parts)

        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        target.write_bytes(
            uploaded.getbuffer()
        )

        saved_files.append(
            relative_path.as_posix()
        )

    return saved_files


def create_folder_zip(app_id, files):
    memory = io.BytesIO()

    app_folder = UPLOADS / app_id

    with zipfile.ZipFile(
        memory,
        "w",
        zipfile.ZIP_DEFLATED
    ) as archive:

        for relative in files:

            relative_path = Path(relative)

            if relative_path.is_absolute() or ".." in relative_path.parts:
                continue

            source = app_folder.joinpath(*relative_path.parts)

            if source.is_file():
                archive.write(
                    source,
                    arcname=relative_path.as_posix()
                )

    memory.seek(0)

    return memory.getvalue()


def remove_file(folder, filename):
    if not filename:
        return

    target = folder / Path(filename).name

    if target.is_file():
        target.unlink()


def remove_app_files(app):
    remove_file(
        UPLOADS,
        app.get("file", "")
    )

    remove_file(
        IMAGES,
        app.get("image", "")
    )

    app_folder = UPLOADS / app.get("id", "")

    if app_folder.is_dir():
        import shutil
        shutil.rmtree(app_folder)


# =========================================================
# ADMIN LOGIN
# =========================================================

def admin_login():

    st.sidebar.title("Yönetici")

    admin = load_admin()

    if not st.session_state.get("admin", False):

        if admin is None:

            st.sidebar.info(
                "İlk yönetici kurulumu"
            )

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

                if hmac.compare_digest(
                    password,
                    DEFAULT_PASSWORD
                ):

                    st.session_state["admin"] = True

                    st.session_state[
                        "must_change_password"
                    ] = True

                    st.rerun()

                else:
                    st.sidebar.error(
                        "İlk giriş şifresi yanlış."
                    )

        else:

            with st.sidebar.form("admin_login"):

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
                    st.session_state[
                        "must_change_password"
                    ] = False

                    st.rerun()

                else:
                    st.sidebar.error(
                        "Şifre yanlış."
                    )

    else:

        st.sidebar.success(
            "Yönetici girişi açık"
        )

        if st.sidebar.button(
            "Oturumu kapat",
            use_container_width=True
        ):

            st.session_state["admin"] = False
            st.session_state["must_change_password"] = False

            st.rerun()


# =========================================================
# MANDATORY PASSWORD CHANGE
# =========================================================

def password_change_screen():

    st.title("🔐 Yönetici şifresi belirle")

    st.warning(
        "Yönetim paneline geçmeden önce varsayılan şifreni değiştirmelisin."
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
            "Şifreyi kaydet",
            use_container_width=True
        )

        if submit:

            if len(new_password) < 10:
                st.error(
                    "Şifre en az 10 karakter olmalı."
                )

            elif new_password != repeat_password:
                st.error(
                    "Şifreler eşleşmiyor."
                )

            elif new_password == DEFAULT_PASSWORD:
                st.error(
                    "Varsayılan şifreyi kullanamazsın."
                )

            else:

                set_password(new_password)

                st.session_state[
                    "must_change_password"
                ] = False

                st.success(
                    "Yeni şifren kaydedildi."
                )

                st.rerun()


# =========================================================
# VISUAL DESIGN
# =========================================================

st.markdown("""
<style>

.stApp {
    background:
        radial-gradient(
            circle at top right,
            #172554 0%,
            #0b1120 40%,
            #080d18 100%
        );

    color: #f1f5f9;
}

section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #29364b;
}

.hero {
    padding: 35px;
    border-radius: 22px;

    background:
        linear-gradient(
            120deg,
            #172554,
            #312e81,
            #1e1b4b
        );

    border: 1px solid #3730a3;
    margin-bottom: 25px;
}

.hero h1 {
    color: white;
    font-size: 43px;
    font-weight: 800;
    margin: 0;
}

.hero p {
    color: #cbd5e1;
    font-size: 16px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px;
}

.stButton button,
.stDownloadButton button {
    border-radius: 10px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="hero">
    <h1>OSS MARKET</h1>
    <p>Kendi uygulama mağazan.</p>
    <p>OSS uygulamalarını keşfet, tanıt ve indir.</p>
</div>
""", unsafe_allow_html=True)


# =========================================================
# AUTHENTICATION
# =========================================================

admin_login()

if (
    st.session_state.get("admin", False)
    and st.session_state.get("must_change_password", False)
):

    password_change_screen()
    st.stop()


apps = load_apps()


# =========================================================
# MAIN TABS
# =========================================================

market_tab, manage_tab = st.tabs([
    "🛒 Uygulama Mağazası",
    "⚙️ Yönetim Paneli"
])


# =========================================================
# MARKET
# =========================================================

with market_tab:

    search_col, category_col = st.columns([3, 1])

    with search_col:

        search = st.text_input(
            "🔎 Uygulama ara",
            placeholder="OSS Browser, OSS Studio..."
        )

    with category_col:

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

    st.caption(
        f"{len(filtered)} uygulama bulundu."
    )

    if not filtered:

        st.info(
            "Henüz uygulama eklenmemiş. Yönetim panelinden uygulama ekleyebilirsin."
        )

    for app in filtered:

        with st.container(border=True):

            image_path = IMAGES / app.get("image", "")

            left, right = st.columns(
                [1, 2.5],
                vertical_alignment="center"
            )

            with left:

                if (
                    app.get("image")
                    and image_path.is_file()
                ):

                    st.image(
                        str(image_path),
                        use_container_width=True
                    )

                else:

                    st.markdown(
                        "<div style='height:140px;display:grid;"
                        "place-items:center;background:#172033;"
                        "border-radius:12px;font-size:48px'>📦</div>",
                        unsafe_allow_html=True
                    )

            with right:

                st.subheader(
                    app.get("name", "İsimsiz uygulama")
                )

                st.caption(
                    f'{app.get("category", "Diğer")} · '
                    f'v{app.get("version", "1.0")}'
                )

                if app.get("short"):
                    st.write(app["short"])

                if app.get("description"):

                    with st.expander(
                        "Uygulama açıklaması"
                    ):
                        st.write(
                            app["description"]
                        )

                if app.get("website"):

                    st.link_button(
                        "Proje sayfası",
                        app["website"]
                    )

                folder_files = app.get(
                    "folder_files",
                    []
                )

                if folder_files:

                    zip_data = create_folder_zip(
                        app["id"],
                        folder_files
                    )

                    st.download_button(
                        "📁 Uygulama klasörünü indir",
                        data=zip_data,
                        file_name=(
                            safe_filename(app["name"])
                            + ".zip"
                        ),
                        mime="application/zip",
                        key="folder_download_" + app["id"]
                    )

                    st.caption(
                        f"{len(folder_files)} dosya · Klasör ZIP olarak hazırlanır."
                    )

                else:

                    file_path = UPLOADS / app.get(
                        "file",
                        ""
                    )

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


# =========================================================
# MANAGEMENT PANEL
# =========================================================

with manage_tab:

    if not st.session_state.get("admin", False):

        st.warning(
            "Yönetim panelini kullanmak için yönetici girişi yapmalısın."
        )

    else:

        st.title("Yönetim Merkezi")

        add_tab, edit_tab, security_tab = st.tabs([
            "＋ Uygulama ekle",
            "📦 Uygulamaları yönet",
            "🔐 Güvenlik"
        ])


        # =================================================
        # ADD APPLICATION
        # =================================================

        with add_tab:

            st.subheader(
                "Yeni OSS uygulaması ekle"
            )

            with st.form(
                "new_app",
                clear_on_submit=True
            ):

                name = st.text_input(
                    "Uygulama adı *",
                    placeholder="OSS Browser"
                )

                col1, col2 = st.columns(2)

                with col1:

                    category = st.selectbox(
                        "Kategori",
                        CATEGORIES
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

                st.divider()

                st.markdown(
                    "#### Kapak görseli"
                )

                image = st.file_uploader(
                    "Görsel yükle (isteğe bağlı)",
                    type=[
                        "png",
                        "jpg",
                        "jpeg",
                        "webp"
                    ]
                )

                st.divider()

                st.markdown(
                    "#### Uygulama dosyası"
                )

                upload_mode = st.radio(
                    "Yükleme türü",
                    [
                        "Tek dosya",
                        "Klasörün tamamı"
                    ],
                    horizontal=True
                )

                upload = None
                folder_upload = None

                if upload_mode == "Tek dosya":

                    upload = st.file_uploader(
                        "EXE, ZIP, APK veya başka bir dosya",
                        key="single_upload"
                    )

                else:

                    folder_upload = st.file_uploader(
                        "Uygulama klasörünü seç",
                        accept_multiple_files="directory",
                        key="folder_upload"
                    )

                    st.caption(
                        "Klasörün içindeki alt klasörler ve dosyalar korunur."
                    )

                submit = st.form_submit_button(
                    "🚀 Mağazaya ekle",
                    use_container_width=True
                )

                if submit:

                    if not name.strip():

                        st.error(
                            "Uygulama adı zorunludur."
                        )

                    elif (
                        upload_mode == "Tek dosya"
                        and upload is None
                    ):

                        st.error(
                            "Bir uygulama dosyası seçmelisin."
                        )

                    elif (
                        upload_mode == "Klasörün tamamı"
                        and not folder_upload
                    ):

                        st.error(
                            "Bir uygulama klasörü seçmelisin."
                        )

                    else:

                        app_id = uuid.uuid4().hex

                        if upload_mode == "Tek dosya":

                            filename = save_single_file(
                                upload,
                                app_id
                            )

                            saved_folder_files = []

                            original_filename = safe_filename(
                                upload.name
                            )

                        else:

                            saved_folder_files = save_folder_upload(
                                folder_upload,
                                app_id
                            )

                            filename = ""

                            original_filename = (
                                safe_filename(name)
                                + ".zip"
                            )

                            if not saved_folder_files:

                                st.error(
                                    "Klasörde kaydedilebilir dosya bulunamadı."
                                )

                                st.stop()

                        image_name = ""

                        if image:

                            image_name = save_single_file(
                                image,
                                app_id + "_cover"
                            )

                            # Görsel dosyası uploads yerine images klasöründe olmalı.
                            old_image = UPLOADS / image_name

                            image_name = "cover_" + app_id + Path(image.name).suffix.lower()

                            new_image = IMAGES / image_name

                            old_image.replace(new_image)

                        new_app = {
                            "id": app_id,
                            "name": name.strip(),
                            "short": short.strip(),
                            "category": category,
                            "version": version.strip() or "1.0",
                            "website": website.strip(),
                            "description": description.strip(),
                            "file": filename,
                            "original_filename": original_filename,
                            "folder_files": saved_folder_files,
                            "image": image_name,
                            "date": datetime.now().strftime(
                                "%d.%m.%Y %H:%M"
                            )
                        }

                        current = load_apps()
                        current.append(new_app)

                        save_apps(current)

                        st.success(
                            "Uygulama OSS Market'e eklendi."
                        )

                        st.rerun()


        # =================================================
        # EDIT AND DELETE
        # =================================================

        with edit_tab:

            current = load_apps()

            if not current:

                st.info(
                    "Henüz uygulama bulunmuyor."
                )

            for app in current:

                with st.expander(
                    f'{app["name"]} · v{app.get("version", "1.0")}'
                ):

                    with st.form(
                        "edit_" + app["id"]
                    ):

                        new_name = st.text_input(
                            "Uygulama adı",
                            value=app.get("name", "")
                        )

                        new_version = st.text_input(
                            "Sürüm",
                            value=app.get("version", "1.0")
                        )

                        new_category = st.selectbox(
                            "Kategori",
                            CATEGORIES,
                            index=(
                                CATEGORIES.index(app["category"])
                                if app.get("category") in CATEGORIES
                                else len(CATEGORIES) - 1
                            )
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
                            "Yeni kapak görseli",
                            type=[
                                "png",
                                "jpg",
                                "jpeg",
                                "webp"
                            ],
                            key="image_" + app["id"]
                        )

                        new_file = st.file_uploader(
                            "Yeni tek dosya",
                            key="file_" + app["id"]
                        )

                        save_edit = st.form_submit_button(
                            "Değişiklikleri kaydet"
                        )

                        if save_edit:

                            all_apps = load_apps()

                            target = next(
                                (
                                    x for x in all_apps
                                    if x["id"] == app["id"]
                                ),
                                None
                            )

                            if target:

                                target.update({
                                    "name": new_name.strip(),
                                    "version": new_version.strip(),
                                    "category": new_category,
                                    "short": new_short.strip(),
                                    "description": new_description.strip(),
                                    "website": new_website.strip()
                                })

                                if new_image:

                                    remove_file(
                                        IMAGES,
                                        target.get("image", "")
                                    )

                                    extension = Path(
                                        new_image.name
                                    ).suffix.lower()

                                    image_name = (
                                        "cover_"
                                        + app["id"]
                                        + extension
                                    )

                                    (IMAGES / image_name).write_bytes(
                                        new_image.getbuffer()
                                    )

                                    target["image"] = image_name

                                if new_file:

                                    remove_file(
                                        UPLOADS,
                                        target.get("file", "")
                                    )

                                    target["file"] = save_single_file(
                                        new_file,
                                        app["id"]
                                    )

                                    target["original_filename"] = safe_filename(
                                        new_file.name
                                    )

                                    target["folder_files"] = []

                                save_apps(all_apps)

                                st.success(
                                    "Uygulama güncellendi."
                                )

                                st.rerun()

                    st.caption(
                        "Dosya türünü değiştirmek için yeni dosya yükleyebilirsin."
                    )

                    confirm = st.checkbox(
                        "Bu uygulamayı silmek istiyorum.",
                        key="confirm_" + app["id"]
                    )

                    if st.button(
                        "🗑️ Uygulamayı sil",
                        key="delete_" + app["id"],
                        disabled=not confirm
                    ):

                        all_apps = load_apps()

                        target = next(
                            (
                                x for x in all_apps
                                if x["id"] == app["id"]
                            ),
                            None
                        )

                        if target:
                            remove_app_files(target)

                        all_apps = [
                            x for x in all_apps
                            if x["id"] != app["id"]
                        ]

                        save_apps(all_apps)

                        st.success(
                            "Uygulama silindi."
                        )

                        st.rerun()


        # =================================================
        # SECURITY
        # =================================================

        with security_tab:

            st.subheader(
                "Yönetici şifresini değiştir"
            )

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

                    if not verify_password(
                        old_password,
                        admin
                    ):

                        st.error(
                            "Mevcut şifre yanlış."
                        )

                    elif len(new_password) < 10:

                        st.error(
                            "Yeni şifre en az 10 karakter olmalı."
                        )

                    elif new_password != repeat_password:

                        st.error(
                            "Yeni şifreler eşleşmiyor."
                        )

                    else:

                        set_password(new_password)

                        st.success(
                            "Yönetici şifren değiştirildi."
                        )

            st.divider()

            st.subheader(
                "Mağaza bilgileri"
            )

            st.write(
                f"Toplam uygulama: {len(load_apps())}"
            )

            st.write(
                f"Veri klasörü: {DATA}"
            )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "OSS Market · Kişisel uygulama mağazası"
)
