import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, UserDB, UserRole, AuditJobDB, AuditStatus

DATABASE_URL = "sqlite:///./app/data/platform.db"

def prime_system():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. Create default admin user
        admin = db.query(UserDB).filter(UserDB.username == "admin").first()
        if not admin:
            admin = UserDB(
                username="admin",
                email="admin@aoikei.local",
                hashed_password="fake_hashed_password",
                role=UserRole.ADMIN
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("Created Admin User.")

        # 2. Create sample audit job
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        sample_job = AuditJobDB(
            job_id=job_id,
            repo_url="https://github.com/aoi-kei/sample-project",
            status=AuditStatus.COMPLETED,
            health_score=85,
            owner_id=admin.id,
            report_data={"high_risks": 2, "medium_risks": 5, "low_risks": 10},
            report_json='{"status": "A-OK", "findings": ["Hardcoded AWS Key", "Missing CSRF Protection"]}'
        )
        db.add(sample_job)
        db.commit()
        print(f"Created Sample Audit Job: {job_id}")

    finally:
        db.close()

if __name__ == "__main__":
    prime_system()
