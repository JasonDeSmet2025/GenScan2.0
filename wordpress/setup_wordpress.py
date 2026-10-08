#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GenScan2.0 — Automatische WordPress-setup (frontend)

Eén commando zet een werkende, gestructureerde WordPress-site op op deze pc:

    py setup_wordpress.py

Hoe het werkt:
  1. Leest .env  (database-/admin-waarden)   -- wordt automatisch aangemaakt
     vanuit .env.example als die ontbreekt.
  2. Start de Docker-stack (MySQL + WordPress + phpMyAdmin).
  3. Wacht tot WordPress + database bereikbaar zijn.
  4. Installeert WordPress (alleen nog niet geïnstalleerd).
  5. Past alles toe uit het ontwerpbestand site.json
     (naam, taal, thema, plugins, gebruikers, pagina's, menu's, ...).

Het script gebruikt uitsluitend de standaardbibliotheek (geen extra packages)
en is idempotent: veilig herhaald uitvoeren. Alleen Docker moet draaien.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_EXAMPLE = os.path.join(HERE, ".env.example")
ENV_FILE = os.path.join(HERE, ".env")
SITE_FILE = os.path.join(HERE, "site.json")

# Vaste namen (zie docker-compose.yml: networks/volumes met expliciete "name:")
NET = "genstack_net"
WP_VOL = "genstack_wp_data"
WP_IMAGE = "wordpress:cli"          # officiële wp-cli-image van WordPress
WP_CONTAINER = "genstack_wp"        # Apache-container (voor docker cp / exec)
WPCLI_DEFAULT_TIMEOUT = 180         # max. wachttijd tot WP + DB bereikbaar zijn

ENV = {}  # gevulde .env-waarden (globaal, gebruikt door wp())


# --------------------------------------------------------------------- #
#  Console-output
# --------------------------------------------------------------------- #
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"


def _supports_color():
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


_COLOR = _supports_color()


def _paint(color, text):
    return f"{color}{text}{C.RESET}" if _COLOR else text


def info(msg):
    print(_paint(C.CYAN, "[..] ") + msg)


def ok(msg):
    print(_paint(C.GREEN, "[OK] ") + msg)


def warn(msg):
    print(_paint(C.YELLOW, "[!!] ") + msg)


def err(msg):
    print(_paint(C.RED, "[XX] ") + msg)


def step(msg):
    print("\n" + _paint(C.BOLD, "==> " + msg))


def die(msg):
    err(msg)
    sys.exit(1)


# --------------------------------------------------------------------- #
#  .env lezen / aanmaken
# --------------------------------------------------------------------- #
def parse_env(path):
    """Leest een KEY=VALUE .env bestand (negeert lege regels en #)."""
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip('"').strip("'")
    return data


def ensure_env():
    global ENV
    if not os.path.exists(ENV_FILE):
        if os.path.exists(ENV_EXAMPLE):
            shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
            warn(f".env niet gevonden -> aangemaakt vanuit .env.example: {ENV_FILE}")
            warn("Pas de wachtwoorden in .env aan vóór productief gebruik.")
        else:
            die(f"Geen .env of .env.example gevonden in {HERE}")
    ENV = parse_env(ENV_FILE)
    required = [
        "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_ROOT_PASSWORD",
        "WP_ADMIN_USER", "WP_ADMIN_EMAIL", "WP_ADMIN_PASSWORD",
    ]
    missing = [k for k in required if not ENV.get(k)]
    if missing:
        die(f".env is incompleet. Ontbrekende velden: {', '.join(missing)}")
    return ENV


def load_site():
    if not os.path.exists(SITE_FILE):
        die(f"Ontwerpbestand niet gevonden: {SITE_FILE}")
    try:
        with open(SITE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as e:
        die(f"site.json is geen geldig JSON: {e}")


# --------------------------------------------------------------------- #
#  Commando's uitvoeren
# --------------------------------------------------------------------- #
def run_cmd(cmd, check=True, quiet=False):
    if not quiet:
        print("    $ " + " ".join(_quote(a) for a in cmd))
    try:
        p = subprocess.run(
            cmd, cwd=HERE, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        die("Docker niet gevonden op PATH. Installeer/start Docker Desktop eerst.")
    out = (p.stdout or "") + (p.stderr or "")
    if check and p.returncode != 0:
        if out.strip():
            for line in out.strip().splitlines():
                print("      " + line)
        die(f"Commando faalde met code {p.returncode}: {' '.join(cmd)}")
    return p


def _quote(arg):
    """Alleen voor het nette weergeven van het commando."""
    if arg and any(ch in arg for ch in " \t'\"&|<>"):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def docker_available():
    p = subprocess.run(["docker", "info"], capture_output=True, text=True)
    return p.returncode == 0


def compose(*args, check=True, quiet=False):
    return run_cmd(["docker", "compose", *args], check=check, quiet=quiet)


def wp(*args, check=True, quiet=False):
    """Voert een wp-cli-opdracht uit via een tijdelijke wordpress:cli-container.

    `args` zijn de WP-CLI-subcommando's (zonder het woord 'wp').
    """
    cmd = [
        "docker", "run", "--rm", "-i",
        "--network", NET,
        "-v", f"{WP_VOL}:/var/www/html",
        "-e", "HOME=/tmp",
        "-e", "WORDPRESS_DB_HOST=db",
        "-e", f"WORDPRESS_DB_NAME={ENV['DB_NAME']}",
        "-e", f"WORDPRESS_DB_USER={ENV['DB_USER']}",
        "-e", f"WORDPRESS_DB_PASSWORD={ENV['DB_PASSWORD']}",
        "-e", f"WORDPRESS_TABLE_PREFIX={ENV.get('WP_TABLE_PREFIX', 'wp_')}",
        WP_IMAGE, "wp", "--allow-root", *args,
    ]
    return run_cmd(cmd, check=check, quiet=quiet)


def wp_scalar(*args):
    """Voert wp-cli uit en geeft de (gestripte) stdout terug, ongeacht succes."""
    p = wp(*args, check=False, quiet=True)
    return (p.stdout or "").strip()


def wp_rc(*args):
    """Geeft alleen de returncode terug (0 = ok)."""
    return wp(*args, check=False, quiet=True).returncode


def slugify(text):
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# --------------------------------------------------------------------- #
#  Wachten / status
# --------------------------------------------------------------------- #
def wait_ready(timeout=WPCLI_DEFAULT_TIMEOUT, poll=5):
    step("Wacht tot WordPress & de database bereikbaar zijn ...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        p = wp("db", "status", check=False, quiet=True)
        if p.returncode == 0:
            ok("WordPress-omgeving bereikbaar.")
            return True
        sys.stdout.write("\r    nog bezig ...")
        sys.stdout.flush()
        time.sleep(poll)
    sys.stdout.write("\n")
    die("WordPress/database was niet tijdig bereikbaar.\n"
        "Kijk voor oorzaken:  docker compose logs")


# --------------------------------------------------------------------- #
#  site.json toepassen
# --------------------------------------------------------------------- #
def apply_site(site):
    site_cfg = site.get("site", {})

    # --- Algemene instellingen ---
    step("Stel algemene site-instellingen in ...")
    mapping = [
        ("title", "blogname"),
        ("tagline", "blogdescription"),
        ("timezone", "timezone_string"),
        ("date_format", "date_format"),
        ("time_format", "time_format"),
        ("start_of_week", "start_of_week"),
        ("posts_per_page", "posts_per_page"),
    ]
    for src, opt in mapping:
        if site_cfg.get(src) is not None:
            wp("option", "update", opt, str(site_cfg[src]))
    if site_cfg.get("language"):
        lang = site_cfg["language"]
        wp("language", "core", "install", lang, check=False)
        wp("option", "update", "WPLANG", lang)
    ok("Algemene instellingen toegepast.")

    # --- Permanente links ---
    perm = site.get("permalinks", {}).get("structure")
    if perm:
        step("Stel de permalinkstructuur in ...")
        wp("rewrite", "structure", perm)
        wp("rewrite", "flush")
        ok(f"Permalinks ingesteld op '{perm}'.")

    # --- Thema ---
    theme = site.get("theme")
    if theme:
        step("Zet het thema in ...")
        if wp_rc("theme", "is-installed", theme) != 0:
            wp("theme", "install", theme)
        wp("theme", "activate", theme)
        ok(f"Thema '{theme}' geactiveerd.")
    for t in site.get("themes_to_remove", []):
        if wp_rc("theme", "is-installed", t) == 0:
            step(f"Verwijder thema '{t}' ...")
            wp("theme", "deactivate", t, check=False, quiet=True)
            wp("theme", "delete", t)
            ok(f"Thema '{t}' verwijderd.")

    # --- Plugins ---
    step("Installeer plugins ...")
    for plug in site.get("plugins", []):
        slug = plug["slug"]
        activate = plug.get("activate", True)
        if wp_rc("plugin", "is-installed", slug) != 0:
            wp("plugin", "install", slug)
        if activate:
            wp("plugin", "activate", slug)
        ok(f"Plugin '{slug}' klaar.")
    for slug in site.get("plugins_to_remove", []):
        if wp_rc("plugin", "is-installed", slug) == 0:
            step(f"Verwijder plugin '{slug}' ...")
            wp("plugin", "delete", slug)
            ok(f"Plugin '{slug}' verwijderd.")

    # --- Gebruikers ---
    for user in site.get("users", []):
        username = user["username"]
        if wp_rc("user", "exists", username) == 0:
            ok(f"Gebruiker '{username}' bestaat al (overslaan).")
            continue
        step(f"Maak gebruiker '{username}' ...")
        password = wp_scalar("user", "generate-password") or "WijzigNaLogin"
        args = ["user", "create", username, user["email"],
                f"--role={user.get('role', 'subscriber')}",
                "--user_pass=" + password, "--porcelain"]
        if user.get("first_name"):
            args.append(f"--first_name={user['first_name']}")
        if user.get("last_name"):
            args.append(f"--last_name={user['last_name']}")
        wp(*args)
        print(f"      Gebruiker '{username}' aangemaakt. "
              f"Wachtwoord (kopieer dit nu): {password}")

    # --- Pagina's ---
    step("Maak pagina's ...")
    page_ids = {}
    for page in site.get("pages", []):
        slug = page.get("slug") or slugify(page.get("title", ""))
        existing = wp_scalar("page", "list", f"--name={slug}", "--field=ID")
        if existing:
            pid = existing.splitlines()[0].strip()
            page_ids[slug] = pid
            ok(f"Pagina '{slug}' bestaat al (ID {pid}).")
            continue
        args = ["page", "create", page.get("title", slug),
                f"--post_name={slug}", "--porcelain"]
        if page.get("content"):
            args.append("--post_content=" + page["content"])
        if page.get("status"):
            args.append(f"--post_status={page['status']}")
        parent = page.get("parent")
        if parent:
            parent_id = page_ids.get(parent) or resolve_post_id(parent)
            if parent_id:
                args.append(f"--post_parent={parent_id}")
        pid = wp_scalar(*args)
        page_ids[slug] = pid
        ok(f"Pagina '{slug}' aangemaakt (ID {pid}).")

    # --- Berichten (posts) ---
    for post in site.get("posts", []):
        slug = post.get("slug") or slugify(post.get("title", ""))
        if wp_scalar("post", "list", f"--name={slug}", "--field=ID"):
            ok(f"Bericht '{slug}' bestaat al (overslaan).")
            continue
        args = ["post", "create", post.get("title", slug), f"--post_name={slug}"]
        if post.get("content"):
            args.append("--post_content=" + post["content"])
        if post.get("status"):
            args.append(f"--post_status={post['status']}")
        wp(*args)
        ok(f"Bericht '{slug}' aangemaakt.")

    # --- Menu's ---
    step("Maak menu's ...")
    for menu in site.get("menus", []):
        name = menu["name"]
        location = menu.get("location")
        all_menus = wp_scalar("menu", "list", "--field=name", "--exact")
        menu_names = [m for m in all_menus.splitlines() if m.strip()]
        if name in menu_names:
            menu_id = wp_scalar("menu", "list", "--exact", f"--name={name}", "--field=ID")
            ok(f"Menu '{name}' bestaat al (ID {menu_id}).")
        else:
            menu_id = wp_scalar("menu", "create", name, "--porcelain")
            ok(f"Menu '{name}' aangemaakt (ID {menu_id}).")
        if location:
            wp("menu", "location", name, location, check=False, quiet=True)
        for item in menu.get("items", []):
            item_id = page_ids.get(item) or resolve_post_id(item)
            if not item_id:
                warn(f"Menu-item '{item}' niet gevonden (pagina/bericht?) - overgeslagen.")
                continue
            wp("menu", "add-item", menu_id, str(item_id), check=False, quiet=True)
        ok(f"Menu '{name}' ingevuld.")

    # --- Thema-instellingen (uitstraling) ---
    mods = site.get("theme_mods", {})
    if mods:
        step("Stel thema-instellingen in ...")
        for key, value in mods.items():
            if isinstance(value, (dict, list)):
                wp("theme_mod", "set", key, json.dumps(value, ensure_ascii=False),
                   "--format=json")
            else:
                wp("theme_mod", "set", key, str(value))
        ok("Thema-instellingen toegepast.")

    # --- Import (optioneel) ---
    for xml_file in site.get("import", {}).get("xml_files", []):
        import_xml(xml_file)


def resolve_post_id(slug):
    """Zoekt een ID via slug, eerst als pagina, daarna als bericht."""
    pid = wp_scalar("page", "list", f"--name={slug}", "--field=ID")
    if pid:
        return pid
    pid = wp_scalar("post", "list", f"--name={slug}", "--field=ID")
    return pid or None


def import_xml(xml_relpath):
    src = os.path.join(HERE, xml_relpath)
    if not os.path.exists(src):
        warn(f"Importbestand niet gevonden: {src}")
        return
    step(f"Importeer '{xml_relpath}' ...")
    dest = f"{WP_CONTAINER}:/var/www/html/wp-content/uploads/genstack_import.xml"
    run_cmd(["docker", "cp", src, dest])
    wp("import", "/var/www/html/wp-content/uploads/genstack_import.xml",
       "--authors=create")
    run_cmd(["docker", "exec", WP_CONTAINER, "rm",
            "-f", "/var/www/html/wp-content/uploads/genstack_import.xml"],
            check=False, quiet=True)
    ok("Import voltooid.")


# --------------------------------------------------------------------- #
#  Hoofdstroom
# --------------------------------------------------------------------- #
def ensure_url(url):
    """Houdt siteurl/home gelijk aan WP_SITE_URL (handig bij FQDN-wissel)."""
    current = wp_scalar("option", "get", "siteurl")
    if current and current.rstrip("/") != url.rstrip("/"):
        wp("option", "update", "siteurl", url)
        wp("option", "update", "home", url)
        ok(f"Site-URL bijgewerkt naar {url}")


def main():
    step("GenScan2.0 — WordPress-setup")
    print(_paint(C.BOLD, "Voortgang:"))

    if not docker_available():
        die("Docker is niet draaiend. Start Docker Desktop en probeer opnieuw.")

    ensure_env()
    site = load_site()
    url = ENV.get("WP_SITE_URL",
                  "http://localhost:" + ENV.get("WP_HTTP_PORT", "8080"))
    title = site.get("site", {}).get("title", "GenScan")

    # 1) Stack starten
    step("Start de Docker-stack (MySQL + WordPress + phpMyAdmin) ...")
    compose("up", "-d")
    ok("Docker-stack gestart.")

    # 2) Wachten tot bereikbaar
    wait_ready()

    # 3) Installeren indien nodig
    if wp_rc("core", "is-installed") != 0:
        step("Installeer WordPress ...")
        wp("core", "install",
           f"--url={url}",
           f"--title={title}",
           f"--admin_user={ENV['WP_ADMIN_USER']}",
           f"--admin_password={ENV['WP_ADMIN_PASSWORD']}",
           f"--admin_email={ENV['WP_ADMIN_EMAIL']}")
        ok("WordPress geïnstalleerd.")
    else:
        ok("WordPress is al geïnstalleerd (overslaan).")

    ensure_url(url)

    # 4) Ontwerp (site.json) toepassen
    step("Pas het ontwerp uit site.json toe ...")
    apply_site(site)

    # 5) Samenvatting
    print("\n" + _paint(C.BOLD, "===================================================="))
    print(_paint(C.GREEN, " Klaar! WordPress draait op deze pc:"))
    print(_paint(C.BOLD, "===================================================="))
    print(f"   Site      : {url}")
    print(f"   Admin     : {url.rstrip('/')}/wp-admin")
    print(f"   Login     : {ENV['WP_ADMIN_USER']}  (wachtwoord: zie .env)")
    print(f"   phpMyAdmin: http://localhost:{ENV.get('PMA_PORT', '8081')}")
    print()
    print(_paint(C.CYAN, " Handige commando's:"))
    print("     docker compose logs -f wordpress   # logs volgen")
    print("     docker compose down                # stoppen (data blijft bewaard)")
    print("     docker compose down -v             # stoppen EN alle data wissen")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGeannuleerd door gebruiker.")
        sys.exit(1)
