import logging
from datetime import timedelta

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from .constants import DATA_TIERS, EXPORT_GLOSSARY
from .models import AuditLog, ConsentRecord, DataDeletionRequest

logger = logging.getLogger("palp.privacy")


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_consent_status(user):
    statuses = []
    from .constants import CONSENT_PURPOSES

    for purpose_key, meta in CONSENT_PURPOSES.items():
        latest = (
            ConsentRecord.objects
            .filter(user=user, purpose=purpose_key)
            .order_by("-created_at")
            .first()
        )
        statuses.append({
            "purpose": purpose_key,
            "label": meta["label"],
            "description": meta["description"],
            "granted": latest.granted if latest else False,
            "last_changed_at": latest.created_at if latest else None,
            "version": latest.version if latest else None,
        })
    return statuses


def has_consent(user, purpose):
    latest = (
        ConsentRecord.objects
        .filter(user=user, purpose=purpose)
        .order_by("-created_at")
        .values_list("granted", flat=True)
        .first()
    )
    return latest is True


def sync_user_consent_flag(user):
    from .constants import CONSENT_PURPOSES
    all_granted = all(
        has_consent(user, p) for p in CONSENT_PURPOSES
    )
    user.consent_given = all_granted
    user.consent_given_at = timezone.now() if all_granted else None
    user.save(update_fields=["consent_given", "consent_given_at"])


def log_audit(*, actor, action, resource, target_user=None, detail=None,
              ip_address=None, request_id=None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_user=target_user,
        resource=resource,
        detail=detail or {},
        ip_address=ip_address,
        request_id=request_id,
    )


def _serialize_qs(queryset, fields=None):
    rows = []
    for obj in queryset.iterator():
        data = {}
        target_fields = fields if fields else [
            f.name for f in obj._meta.get_fields()
            if hasattr(f, "column")
        ]
        for field_name in target_fields:
            val = getattr(obj, field_name, None)
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            elif hasattr(val, "pk"):
                val = val.pk
            data[field_name] = val
        rows.append(data)
    return rows


def export_user_data(user):
    # Build the tier scaffolding dynamically so adding a new tier in
    # ``constants.DATA_TIERS`` (e.g. v3 roadmap behavioral_signals) doesn't
    # require remembering to update the hard-coded keys here.
    result: dict = {tier_key: {} for tier_key in DATA_TIERS}

    result["pii"]["user"] = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "student_id": user.student_id,
        "phone": user.phone,
        "role": user.role,
        "consent_given": user.consent_given,
        "consent_given_at": (
            user.consent_given_at.isoformat() if user.consent_given_at else None
        ),
        "created_at": user.created_at.isoformat(),
    }

    result["pii"]["consent_history"] = list(
        ConsentRecord.objects
        .filter(user=user)
        .values("purpose", "granted", "version", "created_at")
    )

    for tier_key, tier_config in DATA_TIERS.items():
        if tier_key == "pii":
            continue

        for model_label, fields_spec in tier_config["models"].items():
            app_label, model_name = model_label.split(".")
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError:
                continue

            user_fk = _find_user_fk(Model)
            if not user_fk:
                continue

            qs = Model.objects.filter(**{user_fk: user})
            data_key = f"{app_label}.{model_name}"
            result[tier_key][data_key] = _serialize_qs(qs)

    return result


def _find_user_fk(model_class):
    from django.conf import settings
    user_model_label = settings.AUTH_USER_MODEL.lower()

    for field in model_class._meta.get_fields():
        if hasattr(field, "related_model") and field.related_model:
            related_label = (
                f"{field.related_model._meta.app_label}."
                f"{field.related_model._meta.model_name}"
            )
            if related_label == user_model_label:
                return field.name
    return None


@transaction.atomic
def delete_user_data(user, tiers, actor=None, ip_address=None):
    summary = {}

    for tier_key in tiers:
        tier_config = DATA_TIERS.get(tier_key)
        if not tier_config:
            continue

        tier_summary = {}
        policy = tier_config["delete_policy"]

        if tier_key == "pii":
            _anonymize_pii(user)
            tier_summary["user"] = "anonymized"
        else:
            for model_label in tier_config["models"]:
                app_label, model_name = model_label.split(".")
                try:
                    Model = apps.get_model(app_label, model_name)
                except LookupError:
                    continue

                user_fk = _find_user_fk(Model)
                if not user_fk:
                    continue

                qs = Model.objects.filter(**{user_fk: user})
                count = qs.count()

                if policy == "hard_delete":
                    qs.delete()
                    tier_summary[model_label] = {
                        "action": "deleted", "count": count,
                    }
                elif policy == "anonymize":
                    _anonymize_queryset(qs, user_fk)
                    tier_summary[model_label] = {
                        "action": "anonymized", "count": count,
                    }

        summary[tier_key] = tier_summary

    log_audit(
        actor=actor or user,
        action=AuditLog.Action.DELETE,
        resource="privacy.delete_user_data",
        target_user=user,
        detail={"tiers": tiers, "summary": summary},
        ip_address=ip_address,
    )

    return summary


def _anonymize_pii(user):
    user.first_name = "Deleted"
    user.last_name = "User"
    user.email = f"deleted_{user.id}@anon.palp"
    user.student_id = ""
    user.phone = ""
    user.avatar_url = ""
    user.save(update_fields=[
        "first_name", "last_name", "email",
        "student_id", "phone", "avatar_url",
    ])


def _anonymize_queryset(queryset, user_fk_name):
    queryset.update(**{user_fk_name: None})


def enforce_retention():
    now = timezone.now()
    total_deleted = 0

    for tier_key, tier_config in DATA_TIERS.items():
        if tier_key == "pii":
            continue

        retention_months = tier_config.get("retention_months")
        if not retention_months:
            continue

        cutoff = now - timedelta(days=retention_months * 30)

        for model_label in tier_config["models"]:
            app_label, model_name = model_label.split(".")
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError:
                continue

            date_field = _find_date_field(Model)
            if not date_field:
                continue

            qs = Model.objects.filter(**{f"{date_field}__lt": cutoff})
            count = qs.count()

            if count == 0:
                continue

            policy = tier_config["delete_policy"]
            if policy == "hard_delete":
                qs.delete()
            elif policy == "anonymize":
                user_fk = _find_user_fk(Model)
                if user_fk:
                    _anonymize_queryset(qs, user_fk)

            total_deleted += count
            logger.info(
                "Retention enforcement: %s %d records from %s (cutoff=%s)",
                policy, count, model_label, cutoff.isoformat(),
            )

    log_audit(
        actor=None,
        action=AuditLog.Action.DELETE,
        resource="privacy.enforce_retention",
        detail={"total_affected": total_deleted},
    )

    return total_deleted


def _find_date_field(model_class):
    for name in ("created_at", "timestamp_utc", "started_at", "last_updated"):
        try:
            model_class._meta.get_field(name)
            return name
        except Exception:
            continue
    return None
