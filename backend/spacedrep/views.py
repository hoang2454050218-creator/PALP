"""HTTP endpoints for the spaced repetition system.

| Method | Path                       | Auth                |
| ------ | -------------------------- | ------------------- |
| GET    | ``due/``                    | IsStudent           |
| GET    | ``upcoming/``               | IsStudent           |
| POST   | ``review/``                 | IsStudent           |
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStudent

from spacedrep.models import ReviewItem
from spacedrep.services import (
    due_items,
    ensure_item,
    review,
    upcoming_items,
)


def _serialize_item(item: ReviewItem) -> dict:
    return {
        "id": item.id,
        "concept_id": item.concept_id,
        "concept_name": item.concept.name,
        "concept_code": item.concept.code,
        "state": item.state,
        "stability_days": round(float(item.stability), 2),
        "difficulty": round(float(item.difficulty), 2),
        "due_at": item.due_at.isoformat() if item.due_at else None,
        "last_review_at": item.last_review_at.isoformat() if item.last_review_at else None,
        "review_count": item.review_count,
        "lapse_count": item.lapse_count,
    }


class DueItemsView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        items = due_items(student=request.user)
        return Response({"items": [_serialize_item(i) for i in items]})


class UpcomingItemsView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        items = upcoming_items(student=request.user)
        return Response({"items": [_serialize_item(i) for i in items]})


class ReviewView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request):
        concept_id = request.data.get("concept_id")
        rating = request.data.get("rating")
        response_time = request.data.get("response_time_seconds")
        if not concept_id or not rating:
            return Response(
                {"detail": "concept_id and rating are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            concept_id_int = int(concept_id)
            rating_int = int(rating)
        except (TypeError, ValueError):
            return Response(
                {"detail": "concept_id + rating must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if rating_int < 1 or rating_int > 4:
            return Response(
                {"detail": "rating must be 1..4 (Again / Hard / Good / Easy)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from curriculum.models import Concept

        concept = Concept.objects.filter(pk=concept_id_int, is_active=True).first()
        if not concept:
            return Response(
                {"detail": "Không tìm thấy concept."},
                status=status.HTTP_404_NOT_FOUND,
            )
        item = ensure_item(student=request.user, concept=concept)
        log = review(
            item=item,
            rating=rating_int,
            response_time_seconds=
                float(response_time) if response_time is not None else None,
        )
        item.refresh_from_db()
        return Response(
            {
                "item": _serialize_item(item),
                "log": {
                    "id": log.id,
                    "interval_days": log.interval_days,
                    "post_stability": log.post_stability,
                    "post_difficulty": log.post_difficulty,
                    "retrievability_at_review": log.retrievability_at_review,
                    "rating": log.rating,
                },
            },
            status=status.HTTP_201_CREATED,
        )
