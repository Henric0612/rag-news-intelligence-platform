"""Evaluation-only SQLite and empty FAISS storage, scoped to a temporary directory."""

from contextlib import contextmanager
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from flask import Flask

from .dataset import load_dataset, validate_dataset


@contextmanager
def isolated_evaluation(dataset=None):
    """Yield (app, paths) with fixed KnowledgeItems in a private temporary DB.

    The empty FAISS IndexFlatIP and mapping reserve storage for later D2 model
    evaluation. D1 does not synthesize embeddings or claim retrieval quality.
    Only the KnowledgeItem table is created; no production app factory is called.
    """
    if dataset is None:
        dataset = load_dataset()
    else:
        validate_dataset(dataset)
    from Backend.models import db, KnowledgeItem
    import faiss

    with TemporaryDirectory(prefix="rag-evaluation-") as directory:
        root = Path(directory)
        paths = {
            "root": root,
            "database": root / "evaluation.sqlite",
            "index": root / "knowledge.index",
            "mapping": root / "id_mapping.json",
        }
        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{paths['database']}",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(app)
        with app.app_context():
            KnowledgeItem.__table__.create(db.engine)
            db.session.add_all(
                KnowledgeItem(id=item["id"], title=item["title"],
                              content=item["content"], category=item["category"],
                              source_type="manual", source_name="Phase D v1 synthetic corpus",
                              status="published", language="zh")
                for item in dataset["records"]
            )
            db.session.commit()
            faiss.write_index(faiss.IndexFlatIP(384), str(paths["index"]))
            paths["mapping"].write_text(json.dumps({}), encoding="utf-8")
            try:
                yield app, paths
            finally:
                db.session.remove()
                db.engine.dispose()
