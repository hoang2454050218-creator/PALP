"""Phase 7 demo seeding — 1 active research protocol + 1 published model card.

Run with:
    python manage.py shell -c "exec(open('seed_phase7_demo.py').read())"
"""
from __future__ import annotations

from publication.models import ModelCard
from publication.services import draft_model_card, promote_model_card
from research.models import ResearchProtocol


def _seed_protocol() -> ResearchProtocol:
    proto, created = ResearchProtocol.objects.update_or_create(
        code="aied-2026-dkt-replication",
        defaults={
            "title": "Replication of Piech et al. 2015 DKT on PALP attempt logs",
            "description": (
                "Mục tiêu: tái lặp kết quả Deep Knowledge Tracing trên dữ liệu "
                "PALP để chuẩn bị submission cho hội nghị AIED 2026. Dữ liệu "
                "xuất ra sẽ được ẩn danh hoá theo k=5 anonymity và thời gian "
                "lưu trữ tối đa 12 tháng."
            ),
            "pi_name": "Dr. Lê Văn PI",
            "pi_email": "pi.aied@example.edu.vn",
            "irb_number": "IRB-2026-001",
            "data_purposes": ["aied_2026_dkt_replication"],
            "data_categories": ["academic", "behavioral"],
            "retention_months": 12,
            "status": ResearchProtocol.Status.ACTIVE,
        },
    )
    print(f"  protocol {'created' if created else 'updated'}: {proto.code}")
    return proto


def _seed_model_card() -> ModelCard:
    draft = draft_model_card(model_label="dkt-numpy@0.1.0")
    promoted = promote_model_card(draft, target="published")
    print(f"  model card published: {promoted.model_label}")
    return promoted


def main() -> None:
    print("Seeding Phase 7 demo data...")
    _seed_protocol()
    _seed_model_card()
    print("Phase 7 demo seed: done.")


main()
