from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app.main import app, db_session, get_engine
from app.database import recreate_schema

engine = create_engine("sqlite:///:memory:", echo=False)
recreate_schema(engine, drop_existing=False)

def override_db_session():
    with engine.begin() as conn:
        pass
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[db_session] = override_db_session

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
