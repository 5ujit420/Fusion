import logging
from django.db import IntegrityError, transaction
from .models import Has, Skill

logger = logging.getLogger(__name__)


def create_has_for_student(skill_data, validated_data):
    """Create or get Skill then create Has relation.
    Preserves previous behaviour: if Has already exists, raise ValueError for serializer to translate.
    """
    skill_obj, created = Skill.objects.get_or_create(**skill_data)
    try:
        with transaction.atomic():
            has_obj = Has.objects.create(skill_id=skill_obj, **validated_data)
            return has_obj
    except IntegrityError as e:
        logger.exception("Has creation IntegrityError")
        raise ValueError("This skill is already present")
    except Exception as e:
        logger.exception("Unexpected error creating Has")
        raise
