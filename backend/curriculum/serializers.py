from rest_framework import serializers
from .models import (
    Course, Enrollment, Concept, ConceptPrerequisite,
    Milestone, MicroTask, SupplementaryContent,
)


class ConceptSerializer(serializers.ModelSerializer):
    prerequisite_ids = serializers.SerializerMethodField()

    class Meta:
        model = Concept
        fields = ("id", "code", "name", "description", "order", "prerequisite_ids")

    def get_prerequisite_ids(self, obj):
        return list(obj.prerequisites.values_list("prerequisite_id", flat=True))


class SupplementaryContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplementaryContent
        fields = ("id", "concept", "title", "content_type", "body", "media_url", "difficulty_target", "order")


class MicroTaskSerializer(serializers.ModelSerializer):
    concept_name = serializers.CharField(source="concept.name", read_only=True)

    class Meta:
        model = MicroTask
        fields = (
            "id", "milestone", "concept", "concept_name", "title", "description",
            "task_type", "difficulty", "estimated_minutes", "content",
            "max_score", "order",
        )


class MilestoneSerializer(serializers.ModelSerializer):
    tasks = MicroTaskSerializer(many=True, read_only=True)
    concept_ids = serializers.PrimaryKeyRelatedField(
        source="concepts", queryset=Concept.objects.all(), many=True, required=False,
    )
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = (
            "id", "course", "title", "description", "order",
            "target_week", "concept_ids", "tasks", "task_count",
        )

    def get_task_count(self, obj):
        return obj.tasks.count()


class MilestoneListSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = ("id", "title", "description", "order", "target_week", "task_count")

    def get_task_count(self, obj):
        return obj.tasks.count()


class CourseSerializer(serializers.ModelSerializer):
    concept_count = serializers.SerializerMethodField()
    milestone_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ("id", "code", "name", "description", "credits", "concept_count", "milestone_count")

    def get_concept_count(self, obj):
        return obj.concepts.count()

    def get_milestone_count(self, obj):
        return obj.milestones.count()


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ("id", "student", "course", "student_class", "semester", "enrolled_at", "is_active")
        read_only_fields = ("student",)
