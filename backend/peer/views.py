"""HTTP endpoints for the Peer Engine.

Endpoint summary (all under ``/api/peer/``):

| Method | Path                                | Auth                        |
| ------ | ----------------------------------- | --------------------------- |
| GET    | ``consent/``                        | IsStudent                   |
| PATCH  | ``consent/``                        | IsStudent                   |
| GET    | ``frontier/``                       | IsStudent                   |
| GET    | ``benchmark/``                      | IsStudent + peer_comparison |
| POST   | ``buddy/find/``                     | IsStudent + peer_teaching   |
| GET    | ``buddy/me/``                       | IsStudent + peer_teaching   |
| POST   | ``buddy/<id>/respond/``             | IsStudent + peer_teaching   |
| POST   | ``teaching-session/<match_id>/start/``  | IsStudent + peer_teaching |
| GET    | ``herd-clusters/``                  | IsLecturer                  |
| POST   | ``herd-clusters/<id>/review/``      | IsLecturer                  |

The frontier endpoint is intentionally NOT consent-gated — past-self
data has no peer-comparison side effect and the page is the safe
default landing for any student.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsLecturer, IsLecturerOrAdmin, IsStudent

from peer.models import (
    HerdCluster,
    PeerConsent,
    ReciprocalPeerMatch,
    TeachingSession,
)
from peer.permissions import (
    HasPeerComparisonConsent,
    HasPeerTeachingConsent,
)
from peer.serializers import (
    HerdClusterSerializer,
    PeerConsentSerializer,
    ReciprocalPeerMatchSerializer,
    TeachingSessionSerializer,
)
from peer.services.benchmark import compute_benchmark
from peer.services.frontier import compute_frontier
from peer.services.reciprocal_matcher import find_reciprocal_match


def _ensure_consent_row(student) -> PeerConsent:
    consent, _ = PeerConsent.objects.get_or_create(student=student)
    return consent


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

class PeerConsentView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        consent = _ensure_consent_row(request.user)
        return Response(PeerConsentSerializer(consent).data)

    def patch(self, request):
        consent = _ensure_consent_row(request.user)
        serializer = PeerConsentSerializer(consent, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Track revocations so we can audit later — explicit field
        # change wins over silent toggling. We also mirror peer
        # consents into the central ``ConsentRecord`` so the privacy
        # middleware sees the same source of truth.
        from privacy.models import ConsentRecord
        from privacy.constants import CONSENT_VERSION

        previous = {
            "peer_comparison": consent.peer_comparison,
            "peer_teaching": consent.peer_teaching,
        }
        consent = serializer.save()

        for purpose in ("peer_comparison", "peer_teaching"):
            new_val = getattr(consent, purpose)
            if new_val != previous[purpose]:
                ConsentRecord.objects.create(
                    user=request.user,
                    purpose=purpose,
                    granted=new_val,
                    version=CONSENT_VERSION,
                )
                if not new_val:
                    consent.last_revoked_purpose = purpose
                    from django.utils import timezone
                    consent.last_revoked_at = timezone.now()
                    consent.save(
                        update_fields=["last_revoked_purpose", "last_revoked_at"]
                    )

        return Response(PeerConsentSerializer(consent).data)


# ---------------------------------------------------------------------------
# Frontier — past-self vs current-self (default, no consent required)
# ---------------------------------------------------------------------------

class FrontierView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        snapshot = compute_frontier(request.user)
        return Response(snapshot.to_dict())


# ---------------------------------------------------------------------------
# Benchmark — anonymous percentile band
# ---------------------------------------------------------------------------

class BenchmarkView(APIView):
    permission_classes = [
        IsAuthenticated, IsStudent, HasPeerComparisonConsent,
    ]

    def get(self, request):
        result = compute_benchmark(request.user)
        return Response(result.to_dict())


# ---------------------------------------------------------------------------
# Buddy — reciprocal teaching matches
# ---------------------------------------------------------------------------

class BuddyFindView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasPeerTeachingConsent]

    def post(self, request):
        match = find_reciprocal_match(request.user)
        if not match:
            return Response(
                {
                    "match": None,
                    "message": (
                        "Chưa tìm được bạn ghép phù hợp trong cohort. "
                        "Hệ thống sẽ thử lại trong tuần tới — không có kết "
                        "quả không phải lỗi của bạn."
                    ),
                },
                status=status.HTTP_200_OK,
            )
        serializer = ReciprocalPeerMatchSerializer(
            match, context={"request": request}
        )
        return Response({"match": serializer.data})


class BuddyMineView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasPeerTeachingConsent]

    def get(self, request):
        from django.db.models import Q
        matches = (
            ReciprocalPeerMatch.objects
            .filter(Q(student_a=request.user) | Q(student_b=request.user))
            .exclude(status=ReciprocalPeerMatch.Status.ARCHIVED)
            .select_related("student_a", "student_b", "concept_a_to_b", "concept_b_to_a")
            .order_by("-created_at")[:10]
        )
        return Response(
            {
                "matches": ReciprocalPeerMatchSerializer(
                    matches, many=True, context={"request": request}
                ).data
            }
        )


class BuddyRespondView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasPeerTeachingConsent]

    def post(self, request, match_id):
        try:
            match = ReciprocalPeerMatch.objects.get(pk=match_id)
        except ReciprocalPeerMatch.DoesNotExist:
            return Response(
                {"detail": "Không tìm thấy match."},
                status=status.HTTP_404_NOT_FOUND,
            )

        viewer = request.user
        if viewer.id not in (match.student_a_id, match.student_b_id):
            return Response(
                {"detail": "Bạn không thuộc match này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        action = request.data.get("action")
        if action == "accept":
            match.status = ReciprocalPeerMatch.Status.ACTIVE
        elif action == "decline":
            match.status = ReciprocalPeerMatch.Status.DECLINED
        elif action == "archive":
            match.status = ReciprocalPeerMatch.Status.ARCHIVED
        else:
            return Response(
                {"detail": "action phải là accept | decline | archive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match.save(update_fields=["status", "updated_at"])
        return Response(
            ReciprocalPeerMatchSerializer(match, context={"request": request}).data
        )


# ---------------------------------------------------------------------------
# Teaching session — minimal start endpoint (full real-time UI is later)
# ---------------------------------------------------------------------------

class TeachingSessionStartView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasPeerTeachingConsent]

    def post(self, request, match_id):
        try:
            match = ReciprocalPeerMatch.objects.get(pk=match_id)
        except ReciprocalPeerMatch.DoesNotExist:
            return Response(
                {"detail": "Không tìm thấy match."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.id not in (match.student_a_id, match.student_b_id):
            return Response(
                {"detail": "Bạn không thuộc match này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if match.status != ReciprocalPeerMatch.Status.ACTIVE:
            return Response(
                {
                    "detail": (
                        "Match chưa được cả hai bên đồng ý — bấm Đồng ý "
                        "trước khi bắt đầu phiên."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = TeachingSession.objects.create(match=match)
        return Response(
            TeachingSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Herd clusters — lecturer side
# ---------------------------------------------------------------------------

class HerdClusterListView(APIView):
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin]

    def get(self, request):
        from accounts.models import LecturerClassAssignment

        if request.user.is_admin_user:
            qs = HerdCluster.objects.all()
        else:
            class_ids = LecturerClassAssignment.objects.filter(
                lecturer=request.user,
            ).values_list("student_class_id", flat=True)
            qs = HerdCluster.objects.filter(student_class_id__in=class_ids)

        qs = qs.select_related("student_class", "fairness_audit").prefetch_related(
            "members"
        ).order_by("-detected_at")[:50]

        return Response(
            {"clusters": HerdClusterSerializer(qs, many=True).data}
        )


class HerdClusterReviewView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def post(self, request, cluster_id):
        from django.utils import timezone

        try:
            cluster = HerdCluster.objects.get(pk=cluster_id)
        except HerdCluster.DoesNotExist:
            return Response(
                {"detail": "Không tìm thấy cluster."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from accounts.models import LecturerClassAssignment
        if not LecturerClassAssignment.objects.filter(
            lecturer=request.user, student_class=cluster.student_class,
        ).exists():
            return Response(
                {"detail": "Bạn không phụ trách lớp này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        notes = request.data.get("notes", "").strip()
        resolved = bool(request.data.get("resolved", False))

        cluster.reviewed_by = request.user
        cluster.reviewed_at = timezone.now()
        cluster.reviewer_notes = notes
        if resolved:
            cluster.is_resolved = True
            cluster.resolved_at = timezone.now()
        cluster.flagged_for_review = False
        cluster.save(
            update_fields=[
                "reviewed_by", "reviewed_at", "reviewer_notes",
                "is_resolved", "resolved_at", "flagged_for_review",
            ]
        )
        return Response(HerdClusterSerializer(cluster).data)
