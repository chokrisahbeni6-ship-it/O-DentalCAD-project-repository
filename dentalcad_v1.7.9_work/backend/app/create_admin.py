"""Crée ou réinitialise un compte administrateur.
Usage : docker compose exec backend python -m app.create_admin email@exemple.fr "Nom Prénom"
Le mot de passe est demandé au clavier (il n'apparaît pas à l'écran)."""
import getpass
import sys

from sqlalchemy import text

from app.auth import hash_password
from app.db import SessionLocal, init_db


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    email, name = sys.argv[1].strip().lower(), sys.argv[2].strip()
    pw = getpass.getpass("Mot de passe (12 caractères minimum) : ")
    if pw != getpass.getpass("Confirmez : "):
        sys.exit("Les deux saisies sont différentes.")
    try:
        hashed = hash_password(pw)
    except ValueError as e:
        sys.exit(str(e))
    init_db()
    db = SessionLocal()
    try:
        db.execute(text("""
            INSERT INTO users (email, hashed_password, full_name, role, is_active)
            VALUES (:e, :p, :n, 'admin', TRUE)
            ON CONFLICT (email) DO UPDATE
              SET hashed_password = :p, role = 'admin', is_active = TRUE
        """), {"e": email, "p": hashed, "n": name})
        db.commit()
    finally:
        db.close()
    print("Compte administrateur enregistré :", email)


if __name__ == "__main__":
    main()
