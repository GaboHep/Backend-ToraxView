# seed_admin.py
import os
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from auth.models import User
from auth.auth_utils import pwd_context

def main():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "adminToraxRX12!")
        if not db.query(User).filter_by(username=username).first():
            u = User(username=username, hashed_password=pwd_context.hash(password), role="administrador")
            db.add(u)
            db.commit()
            print(f"Admin '{username}' creado")
        else:
            print("Admin ya existe")
    finally:
        db.close()

if __name__ == "__main__":
    main()
